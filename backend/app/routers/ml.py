from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime
import pandas as pd

from sklearn.metrics import roc_curve, precision_recall_curve

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    log_loss,
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    f1_score,
    brier_score_loss,
)

from ..deps import get_db, get_current_user
from ..models import Event, Tour, User

router = APIRouter(prefix="/api/ml", tags=["ml"])

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
REPORT_PATH = os.path.join(MODEL_DIR, "train_report.json")

# Формирование признаков 
def _build_row(t: Tour, max_price: float = 0.0, dur_filter: float = 0.0) -> dict:
    return {
        "city": t.city,
        "season": t.season,
        "tour_type": t.tour_type,
        "price": float(t.price),
        "duration_days": float(t.duration_days),
        "rating": float(t.rating),
        "max_price": float(max_price),
        "duration_filter": float(dur_filter),
    }

# разбиение признаков категориальные/числовые
def _make_pipeline() -> Pipeline:
    cat_features = ["city", "season", "tour_type"]
    num_features = ["price", "duration_days", "rating", "max_price", "duration_filter"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
            ("num", StandardScaler(), num_features),
        ],
        remainder="drop",
    )

    clf = LogisticRegression(max_iter=1000, class_weight="balanced")

    return Pipeline(steps=[("prep", preprocessor), ("clf", clf)])

# проверка деления на 0
def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def _derived_from_cm(cm_2x2: list) -> dict:
    # cm = [[tn, fp],[fn,tp]]
    tn, fp = cm_2x2[0][0], cm_2x2[0][1]
    fn, tp = cm_2x2[1][0], cm_2x2[1][1]

    tpr = _safe_div(tp, tp + fn)  # recall
    tnr = _safe_div(tn, tn + fp)  # specificity
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    bal_acc = (tpr + tnr) / 2.0

    mcc_den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = float(((tp * tn) - (fp * fn)) / mcc_den) if mcc_den else 0.0

    return {
        "tnr_specificity": float(tnr),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "balanced_accuracy": float(bal_acc),
        "mcc": float(mcc),
    }

# предсказываем порог
def _metrics_at_threshold(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> dict:
    pred = (proba >= threshold).astype(int)

    acc = float(accuracy_score(y_true, pred))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, pred, average="binary", zero_division=0
    )
    cm = confusion_matrix(y_true, pred).tolist()

    return {
        "threshold": float(threshold),
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "confusion_matrix": cm,
        "derived": _derived_from_cm(cm),
    }


@router.post("/train")
def train_model(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    events = db.query(Event).all()
    if len(events) < 10:
        return {"status": "not_enough_data", "events": len(events), "need": 10}

    rows = [] # список признаков
    y = [] # список целевых меток 

    for ev in events:
        tour = db.query(Tour).filter(Tour.id == ev.tour_id).first()
        if not tour:
            continue

        rows.append(_build_row(tour, max_price=0.0, dur_filter=0.0))
        y.append(1 if ev.event_type == "BOOK" else 0)

    if len(rows) < 10:
        return {"status": "not_enough_data_after_filter", "rows": len(rows)}

    # превращаем y в numpy-массив и проверяем, что классы оба присутствуют
    y_arr = np.array(y, dtype=np.int32)
    if len(set(y_arr.tolist())) < 2:
        return {
            "status": "need_both_classes",
            "labels": {"count_0": int((y_arr == 0).sum()), "count_1": int((y_arr == 1).sum())},
        }

    # обучение
    df = pd.DataFrame(rows)

    X_train, X_test, y_train, y_test = train_test_split(
        df, y_arr, test_size=0.25, random_state=42, stratify=y_arr
    )

    pipe = _make_pipeline()
    pipe.fit(X_train, y_train)

    # предсказания вероятностей
    proba_test = pipe.predict_proba(X_test)[:, 1]

    # ROC curve (TPR vs FPR)
    fpr, tpr, _ = roc_curve(y_test, proba_test)
    roc_curve_points = [{"fpr": float(a), "tpr": float(b)} for a, b in zip(fpr, tpr)]

    # PR curve (Precision vs Recall)
    prec, rec, _ = precision_recall_curve(y_test, proba_test)
    pr_curve_points = [{"recall": float(r), "precision": float(p)} for r, p in zip(rec, prec)]

    # базовые метрики по вероятностям
    roc_auc = float(roc_auc_score(y_test, proba_test))
    pr_auc = float(average_precision_score(y_test, proba_test))
    ll = float(log_loss(y_test, proba_test))
    brier = float(brier_score_loss(y_test, proba_test))

    # метрики при threshold=0.5
    base_thr = 0.5
    base_metrics = _metrics_at_threshold(y_test, proba_test, base_thr)

    # подбор лучшего threshold по f1
    thresholds = np.linspace(0.05, 0.95, 19)
    best = None
    threshold_curve = []

    for th in thresholds:
        mm = _metrics_at_threshold(y_test, proba_test, float(th))

        # кривая для графика
        threshold_curve.append({
            "threshold": mm["threshold"],
            "precision": mm["precision"],
            "recall": mm["recall"],
            "f1": mm["f1"],
            "accuracy": mm["accuracy"],
            "specificity": mm["derived"]["tnr_specificity"],
            "balanced_accuracy": mm["derived"]["balanced_accuracy"],
            "mcc": mm["derived"]["mcc"],
        })

        # лучший порог по F1
        if best is None or mm["f1"] > best["f1"]:
            best = mm

    # macro/weighted f1 (по предсказаниям при base_thr)
    base_pred = (proba_test >= base_thr).astype(int)
    f1_macro = float(f1_score(y_test, base_pred, average="macro", zero_division=0))
    f1_weighted = float(f1_score(y_test, base_pred, average="weighted", zero_division=0))

    report = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "samples_total": int(len(rows)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "labels": {"count_0": int((y_arr == 0).sum()), "count_1": int((y_arr == 1).sum())},
        "metrics": {
            # метрики “по вероятностям” (threshold-independent)
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "logloss": ll,
            "brier": brier,

            # назад-совместимые поля (как раньше)
            "accuracy": base_metrics["accuracy"],
            "precision": base_metrics["precision"],
            "recall": base_metrics["recall"],
            "f1": base_metrics["f1"],
            "confusion_matrix": base_metrics["confusion_matrix"],
            "threshold": base_thr,

            "f1_macro": f1_macro,
            "f1_weighted": f1_weighted,
            "derived": base_metrics["derived"],

            # метрики на best threshold
            "best_threshold": {
                "threshold": best["threshold"],
                "accuracy": best["accuracy"],
                "precision": best["precision"],
                "recall": best["recall"],
                "f1": best["f1"],
                "confusion_matrix": best["confusion_matrix"],
                "derived": best["derived"],
                "grid": [float(x) for x in thresholds.tolist()],
                "curve": threshold_curve,
            },

            "roc_curve": roc_curve_points,
            "pr_curve": pr_curve_points,
        },
        "notes": "BOOK=1, VIEW=0. Features: tour fields + (max_price,duration_filter placeholders=0). "
                 "Added: best_threshold tuning, derived CM metrics, f1_macro/weighted, brier.",
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "saved_model": "model.joblib",
        "saved_report": "train_report.json",
        "samples": int(len(rows)),
        "metrics": report["metrics"],
    }


@router.get("/report")
def get_train_report(user=Depends(get_current_user)):
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(status_code=404, detail="train_report.json not found. Run Train ML first.")
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
