from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import Event, User
from ..schemas import ViewEventRequest

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/view")
def log_view(req: ViewEventRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ev = Event(user_id=user.id, tour_id=req.tour_id, event_type="VIEW")
    db.add(ev)
    db.commit()
    return {"status": "ok"}
