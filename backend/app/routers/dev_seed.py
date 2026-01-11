from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import random

from ..deps import get_db, get_current_user
from ..models import User, Tour, Event
from ..security import hash_password

router = APIRouter(prefix="/api/dev", tags=["dev"])

# наполнение БД данными
@router.post("/seed")
def seed_demo_data(
    users_count: int = 5,
    tours_count: int = 120,
    views_per_user: int = 80,
    books_per_user: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # списки для туров
    cities = ["Rome", "Paris", "Barcelona", "Prague", "Vienna", "Berlin"]
    seasons = ["summer", "winter", "all"]
    types = ["relax", "excursion", "beach"]

    existing_tours = db.query(Tour).count()
    to_create = max(0, tours_count - existing_tours)

    # создание туров
    for _ in range(to_create):
        city = random.choice(cities)
        tour_type = random.choice(types)
        season = random.choice(seasons)

        price = random.randint(60000, 220000)
        duration = random.randint(3, 14)
        rating = round(random.uniform(3.7, 4.95), 2)

        desc = f"{city} • {tour_type} • {duration} дней • {season}"

        # добавление тура в БД
        db.add(Tour(
            city=city,
            price=price,
            duration_days=duration,
            rating=rating,
            season=season,
            tour_type=tour_type,
            description=desc
        ))
    db.commit()

    tours = db.query(Tour).all()
    if not tours:
        raise HTTPException(status_code=400, detail="No tours available for seeding")

    # создание пользователей
    created_users = []
    for i in range(users_count):
        email = f"demo{i+1}@mail.com"
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(email=email, name=f"Demo User {i+1}", password_hash=hash_password("1234"))
            db.add(u)
            db.commit()
            db.refresh(u)
        created_users.append(u)

    # создание для каждого пользователя историю просмотров и бронирований
    for u in created_users:
        fav_city = random.choice(cities) # любимый город
        fav_type = random.choice(types) # любимый тип

        # VIEW — чаще смотрит то, что похоже на предпочтения
        for _ in range(views_per_user):
            pool = [t for t in tours if (t.city == fav_city or t.tour_type == fav_type)]
            t = random.choice(pool if pool else tours)
            db.add(Event(user_id=u.id, tour_id=t.id, event_type="VIEW", created_at=datetime.utcnow()))

        # BOOK — чаще бронирует то, что совпадает по fav_city+fav_type и рейтинг выше
        for _ in range(books_per_user):
            pool = [t for t in tours if (t.city == fav_city and t.tour_type == fav_type and t.rating >= 4.4)]
            t = random.choice(pool if pool else tours)
            db.add(Event(user_id=u.id, tour_id=t.id, event_type="BOOK", created_at=datetime.utcnow()))

    db.commit()

    return {
        "status": "ok",
        "created_tours": to_create,
        "users": [{"email": u.email, "password": "1234"} for u in created_users],
        "events_estimate": len(created_users) * (views_per_user + books_per_user),
    }
