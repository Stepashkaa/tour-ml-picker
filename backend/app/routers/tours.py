from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import joblib
import numpy as np
import pandas as pd

from ..deps import get_db, get_current_user
from ..models import Tour, User
from ..schemas import TourResponse, TourSearchRequest

router = APIRouter(prefix="/api/tours", tags=["tours"])

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "model.joblib")

# Ручная формула подсчёта score
def _simple_fallback_score(t: Tour, req: TourSearchRequest) -> float:
    s = 0.0
    s += float(t.rating) * 2.0

    if req.max_price:
        s += (req.max_price - t.price) / max(req.max_price, 1)

    if req.duration_days:
        s -= abs(t.duration_days - req.duration_days) / 10.0

    if req.tour_type and t.tour_type == req.tour_type:
        s += 0.7

    if req.season and (t.season == req.season or t.season == "all"):
        s += 0.2

    return s

# загружаем модель
def _load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)  # Pipeline
    return None

# строка с признаками
def _build_row_for_predict(t: Tour, req: TourSearchRequest) -> dict:
    return {
        "city": t.city,
        "season": t.season,
        "tour_type": t.tour_type,
        "price": float(t.price),
        "duration_days": float(t.duration_days),
        "rating": float(t.rating),
        "max_price": float(req.max_price or 0),
        "duration_filter": float(req.duration_days or 0),
    }



@router.get("/{tour_id}", response_model=TourResponse)
def get_tour(tour_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Tour).filter(Tour.id == tour_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tour not found")
    return TourResponse.model_validate(t)


@router.post("/search", response_model=List[TourResponse])
def search_tours(req: TourSearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Tour).filter(Tour.city == req.city)

    if req.max_price is not None:
        q = q.filter(Tour.price <= req.max_price) # дорогие убираем

    if req.duration_days is not None:
        q = q.filter(Tour.duration_days.between(req.duration_days - 2, req.duration_days + 2)) # количество дней

    if req.season:
        q = q.filter((Tour.season == req.season) | (Tour.season == "all"))

    tours = q.all() # получаем список туров

    model = _load_model()

    # Выбор ранжирования: ML или fallback
    scored = []
    if model is None:
        for t in tours:
            scored.append((t, _simple_fallback_score(t, req)))
    else:
        rows = [_build_row_for_predict(t, req) for t in tours] # признаки объединяем в строку
        if len(rows) > 0:
            df = pd.DataFrame(rows) # передаём для получения ml_score
            proba = model.predict_proba(df)[:, 1].tolist()
            for t, s in zip(tours, proba):
                scored.append((t, float(s)))

    # сортируем по вероятности брони тура
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: req.limit]

    out = []
    for t, s in top:
        dto = TourResponse.model_validate(t)
        dto.ml_score = float(s)
        out.append(dto)

    return out
