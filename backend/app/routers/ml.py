from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime
import pandas as pd

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
)

from ..deps import get_db, get_current_user
from ..models import Event, Tour, User

router = APIRouter(prefix="/api/ml", tags=["ml"])

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
REPORT_PATH = os.path.join(MODEL_DIR, "train_report.json")


def _build_row(t: Tour, max_price: float = 0.0, dur_filter: float = 0.0) -> dict:
    # Единый формат строки для train и predict
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


@router.post("/train")
def train_model(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Глобальная модель по событиям:
    BOOK -> 1
    VIEW -> 0
    Используем признаки тура + простые признаки запроса (пока max_price/duration_filter=0),
    но pipeline уже готов — позже можно добавить Search-лог и прокинуть реальные значения.
    """

    events = db.query(Event).all()
    if len(events) < 10:
        return {"status": "not_enough_data", "events": len(events), "need": 10}

    rows = []
    y = []

    for ev in events:
        tour = db.query(Tour).filter(Tour.id == ev.tour_id).first()
        if not tour:
            continue

        rows.append(_build_row(tour, max_price=0.0, dur_filter=0.0))
        y.append(1 if ev.event_type == "BOOK" else 0)

    if len(rows) < 10:
        return {"status": "not_enough_data_after_filter", "rows": len(rows)}

    # проверка, что есть оба класса
    y_arr = np.array(y, dtype=np.int32)
    if len(set(y_arr.tolist())) < 2:
        return {
            "status": "need_both_classes",
            "labels": {"count_0": int((y_arr == 0).sum()), "count_1": int((y_arr == 1).sum())},
        }

    # train/test split
    df = pd.DataFrame(rows)

    X_train, X_test, y_train, y_test = train_test_split(
        df, y_arr, test_size=0.25, random_state=42, stratify=y_arr
    )

    pipe = _make_pipeline()
    pipe.fit(X_train, y_train)

    # predict
    proba_test = pipe.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= 0.5).astype(int)

    # metrics
    roc_auc = float(roc_auc_score(y_test, proba_test))
    pr_auc = float(average_precision_score(y_test, proba_test))
    ll = float(log_loss(y_test, proba_test))

    acc = float(accuracy_score(y_test, pred_test))
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred_test, average="binary", zero_division=0)

    cm = confusion_matrix(y_test, pred_test).tolist()  # [[tn, fp],[fn,tp]]

    report = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "samples_total": int(len(rows)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "labels": {"count_0": int((y_arr == 0).sum()), "count_1": int((y_arr == 1).sum())},
        "metrics": {
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "logloss": ll,
            "accuracy": acc,
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "confusion_matrix": cm,
            "threshold": 0.5,
        },
        "notes": "BOOK=1, VIEW=0. Features: tour fields + (max_price,duration_filter placeholders=0).",
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
