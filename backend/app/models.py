from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    bookings = relationship("Booking", back_populates="user")


class Tour(Base):
    __tablename__ = "tours"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True, nullable=False)
    price = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)

    season = Column(String, nullable=False)     # summer/winter/all
    tour_type = Column(String, nullable=False)  # relax/excursion/beach

    description = Column(String, nullable=False, default="")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    tour_id = Column(Integer, ForeignKey("tours.id"), index=True, nullable=False)

    status = Column(String, nullable=False, default="CREATED")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="bookings")
    tour = relationship("Tour")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    tour_id = Column(Integer, ForeignKey("tours.id"), index=True, nullable=False)

    event_type = Column(String, nullable=False)  # VIEW / BOOK
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
