from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..deps import get_db, get_current_user
from ..models import Booking, Tour, Event, User
from ..schemas import CreateBookingRequest, BookingResponse, TourResponse

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse)
def create_booking(req: CreateBookingRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tour = db.query(Tour).filter(Tour.id == req.tour_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")

    booking = Booking(user_id=user.id, tour_id=tour.id, status="CREATED")
    db.add(booking)

    # логируем BOOK событие для ML
    ev = Event(user_id=user.id, tour_id=tour.id, event_type="BOOK")
    db.add(ev)

    db.commit()
    db.refresh(booking)

    # response with nested tour
    resp = BookingResponse(
        id=booking.id,
        status=booking.status,
        created_at=booking.created_at,
        tour=TourResponse.model_validate(tour),
    )
    return resp


@router.get("/my", response_model=List[BookingResponse])
def my_bookings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bookings = db.query(Booking).filter(Booking.user_id == user.id).order_by(Booking.created_at.desc()).all()

    out = []
    for b in bookings:
        tour = db.query(Tour).filter(Tour.id == b.tour_id).first()
        out.append(
            BookingResponse(
                id=b.id,
                status=b.status,
                created_at=b.created_at,
                tour=TourResponse.model_validate(tour),
            )
        )
    return out
