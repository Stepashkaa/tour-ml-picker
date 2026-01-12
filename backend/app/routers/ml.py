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
from ..models import Event, Tour, User, UserSearch

router = APIRouter(prefix="/api/ml", tags=["ml"])

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
REPORT_PATH = os.path.join(MODEL_DIR, "train_report.json")

# Формирование признаков 
def _build_row(t: Tour, max_price: float = 0.0, dur_filter: float = 0.0) -> dict:
    # Формируем "одну строку датасета" = признаки для ML (X)
    # Важно: здесь есть признаки тура (price, duration_days, rating, city...) 
    # и признаки контекста запроса (max_price, duration_filter)
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
    # 1) Какие признаки считаем категориальными (строки)
    cat_features = ["city", "season", "tour_type"]

    # 2) Какие признаки считаем числовыми (скалярные значения)
    num_features = ["price", "duration_days", "rating", "max_price", "duration_filter"]

    # 3) ColumnTransformer применяет разные преобразования к разным колонкам
    preprocessor = ColumnTransformer(
        transformers=[
            # OneHotEncoder превращает категории (Rome, Paris...) в набор 0/1 колонок.
            # handle_unknown="ignore" важно: если в будущем появится новый город,
            # модель не упадёт, а просто поставит 0 во всех известных городах.
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),

            # StandardScaler нормализует числовые признаки (среднее=0, std=1),
            # чтобы LogisticRegression корректно сравнивала веса признаков.
            ("num", StandardScaler(), num_features),
        ],
        remainder="drop", # всё, что не перечислили, выбрасываем
    )

    # 4) Классификатор: логистическая регрессия (предсказывает вероятность BOOK)
    # class_weight="balanced" помогает при дисбалансе классов (BOOK реже, VIEW чаще)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")

    # 5) Pipeline склеивает: сначала предобработка, потом модель
    return Pipeline(steps=[("prep", preprocessor), ("clf", clf)])

def _safe_div(a: float, b: float) -> float:
    # Безопасное деление: если знаменатель 0, возвращаем 0, чтобы не падать с ошибкой
    return float(a / b) if b else 0.0


def _derived_from_cm(cm_2x2: list) -> dict:
    # cm = [[tn, fp],[fn,tp]]
    tn, fp = cm_2x2[0][0], cm_2x2[0][1]
    fn, tp = cm_2x2[1][0], cm_2x2[1][1]

    
    tpr = _safe_div(tp, tp + fn) # Recall / TPR: доля найденных BOOK среди всех реальных BOOK
    tnr = _safe_div(tn, tn + fp) # Specificity / TNR: доля правильно найденных VIEW среди всех реальных VIEW
    fpr = _safe_div(fp, fp + tn) # False Positive Rate: доля ложных BOOK среди всех реальных VIEW
    fnr = _safe_div(fn, fn + tp) # False Negative Rate: доля пропущенных BOOK среди всех реальных BOOK
    bal_acc = (tpr + tnr) / 2.0 # Balanced Accuracy: среднее качество по обоим классам (важно при дисбалансе)
    
    # MCC — корреляция предсказаний и правды (очень хорош при дисбалансе)
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
    # 1) Превращаем вероятности в классы по порогу:
    #    если proba >= threshold -> BOOK (1), иначе VIEW (0)
    pred = (proba >= threshold).astype(int)

    # 2) Accuracy: доля правильных ответов (TP+TN)/N
    acc = float(accuracy_score(y_true, pred))

    # 3) Precision/Recall/F1 для класса BOOK (1)
    # average="binary" -> считаем метрики именно для positive класса = 1 (BOOK)
    # zero_division=0 -> если деление на 0 (например, модель не предсказала ни одного BOOK),
    #                   вернём 0 вместо ошибки
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, pred, average="binary", zero_division=0
    )

    # 4) Confusion matrix в формате [[TN, FP], [FN, TP]]
    cm = confusion_matrix(y_true, pred).tolist()

    # 5) Дополнительные derived-метрики из CM: specificity, fpr, fnr, balanced_accuracy, mcc
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

    # Берём все события пользователей (VIEW/BOOK) — это наша обучающая выборка
    events = db.query(Event).all()

    # Защита от обучения "на пустоте"
    if len(events) < 10:
        return {"status": "not_enough_data", "events": len(events), "need": 10}

    rows = [] # будущие признаки X
    y = [] # будущие метки y (BOOK=1, VIEW=0) 

    # Проходим по каждому событию и превращаем его в одну обучающую строку
    for ev in events:

        # Достаём тур, по которому было событие
        tour = db.query(Tour).filter(Tour.id == ev.tour_id).first()
        if not tour:
            continue # если тур удалён/не найден — пропускаем
        
        # По умолчанию — фильтры поиска неизвестны (0)
        max_price = 0.0
        dur_filter = 0.0
        
        # Если событие привязано к конкретному поиску (search_id),
        # то берём реальные параметры запроса пользователя
        if ev.search_id:
            s = db.query(UserSearch).filter(UserSearch.id == ev.search_id).first()
            if s:
                max_price = float(s.max_price or 0)
                dur_filter = float(s.duration_days or 0)

        # Признаки: поля тура + параметры поиска пользователя
        rows.append(_build_row(tour, max_price=max_price, dur_filter=dur_filter))

        # Целевая метка: BOOK -> 1, VIEW -> 0
        y.append(1 if ev.event_type == "BOOK" else 0)

    # Проверяем, что после фильтрации/пропусков датасет ещё достаточно большой
    if len(rows) < 10:
        return {"status": "not_enough_data_after_filter", "rows": len(rows)}

    # Превращаем список меток в numpy-массив (так удобнее считать и передавать в sklearn)
    y_arr = np.array(y, dtype=np.int32)

    # Проверяем, что в данных есть оба класса (0 и 1).
    # Иначе модель не сможет обучиться (LogReg требует минимум 2 класса).
    if len(set(y_arr.tolist())) < 2:
        return {
            "status": "need_both_classes",
            "labels": {"count_0": int((y_arr == 0).sum()), "count_1": int((y_arr == 1).sum())},
        }

    # X = таблица признаков (каждая строка — событие, каждый столбец — признак)
    df = pd.DataFrame(rows)

    # Делим данные на train/test, stratify сохраняет долю BOOK/VIEW одинаковой в train и test
    X_train, X_test, y_train, y_test = train_test_split(
        df, y_arr, test_size=0.25, random_state=42, stratify=y_arr
    )

    # Создаём ML-пайплайн: OneHot + StandardScaler + LogisticRegression
    pipe = _make_pipeline()
    pipe.fit(X_train, y_train) # Обучаем модель на обучающей выборке

    # предсказания вероятностей
    proba_test = pipe.predict_proba(X_test)[:, 1] # На тесте получаем вероятности класса BOOK (1)

    # ROC curve: зависимость TPR(Recall) от FPR при разных порогах
    fpr, tpr, _ = roc_curve(y_test, proba_test)
    roc_curve_points = [{"fpr": float(a), "tpr": float(b)} for a, b in zip(fpr, tpr)]

    # PR curve: зависимость Precision от Recall (важно при дисбалансе классов)
    prec, rec, _ = precision_recall_curve(y_test, proba_test)
    pr_curve_points = [{"recall": float(r), "precision": float(p)} for r, p in zip(rec, prec)]

    # Метрики по вероятностям (не зависят от threshold=0.5)
    roc_auc = float(roc_auc_score(y_test, proba_test))
    pr_auc = float(average_precision_score(y_test, proba_test))
    ll = float(log_loss(y_test, proba_test))
    brier = float(brier_score_loss(y_test, proba_test))

    # Фиксируем порог классификации: если proba >= 0.5 → считаем BOOK (1), иначе VIEW (0)
    base_thr = 0.5
    base_metrics = _metrics_at_threshold(y_test, proba_test, base_thr)

    # Сетка порогов: проверяем разные значения threshold
    thresholds = np.linspace(0.05, 0.95, 19)
    best = None # сюда положим лучший порог (по F1)
    threshold_curve = [] # сюда соберём точки для графика (precision/recall/f1 vs threshold)

    for th in thresholds:
        # считаем метрики при текущем пороге
        mm = _metrics_at_threshold(y_test, proba_test, float(th))

        # сохраняем точку для графика
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

    # Предсказанный класс при базовом пороге 0.5
    base_pred = (proba_test >= base_thr).astype(int)

    # F1 macro: среднее F1 по классам (VIEW и BOOK) — не зависит от дисбаланса
    f1_macro = float(f1_score(y_test, base_pred, average="macro", zero_division=0))

    # F1 weighted: среднее F1 по классам, но с весами по числу объектов класса
    f1_weighted = float(f1_score(y_test, base_pred, average="weighted", zero_division=0))

    report = {
        # Когда обучали (для логов/сравнения запусков)
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",

        # Размеры данных (важно для понимания достоверности метрик)
        "samples_total": int(len(rows)),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),

        # Баланс классов (сколько VIEW и BOOK)
        "labels": {"count_0": int((y_arr == 0).sum()), "count_1": int((y_arr == 1).sum())},

        "metrics": {
            # Метрики по вероятностям (не зависят от threshold)
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "logloss": ll,
            "brier": brier,

            # Метрики при пороге 0.5 (классический режим классификации)
            "accuracy": base_metrics["accuracy"],
            "precision": base_metrics["precision"],
            "recall": base_metrics["recall"],
            "f1": base_metrics["f1"],
            "confusion_matrix": base_metrics["confusion_matrix"],
            "threshold": base_thr,

            # Сводные F1 для дисбаланса
            "f1_macro": f1_macro,
            "f1_weighted": f1_weighted,

            # Derived метрики из confusion matrix (specificity, MCC и т.д.)
            "derived": base_metrics["derived"],

            # Подбор оптимального порога под F1 + кривая (threshold -> метрики)
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
            
            # Точки для графиков ROC и PR
            "roc_curve": roc_curve_points,
            "pr_curve": pr_curve_points,
        },

        # Текстовое пояснение (для отчёта/защиты)
        "notes": "BOOK=1, VIEW=0. Features: tour fields + (max_price,duration_filter placeholders=0). "
                 "Added: best_threshold tuning, derived CM metrics, f1_macro/weighted, brier.",
    }

    # Создаём папку ml/, если её ещё нет
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Сохраняем обученный pipeline (препроцессинг + модель) в файл
    joblib.dump(pipe, MODEL_PATH)

    # Сохраняем train_report.json (метрики + точки для графиков)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Возвращаем краткий ответ (удобно показать на фронте после Train ML)
    return {
        "status": "ok",
        "saved_model": "model.joblib",
        "saved_report": "train_report.json",
        "samples": int(len(rows)),
        "metrics": report["metrics"],
    }


@router.get("/report")
def get_train_report(user=Depends(get_current_user)):

    # Если отчёта нет — значит модель ещё не обучали
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(status_code=404, detail="train_report.json not found. Run Train ML first.")
    
    # Читаем JSON и возвращаем на фронт
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
