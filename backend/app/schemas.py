from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=4, max_length=120)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# Tours
class TourResponse(BaseModel):
    id: int
    city: str
    price: int
    duration_days: int
    rating: float
    season: str
    tour_type: str
    description: str

    ml_score: Optional[float] = None

    class Config:
        from_attributes = True


class TourSearchRequest(BaseModel):
    city: str
    max_price: Optional[int] = None
    duration_days: Optional[int] = None
    tour_type: Optional[str] = None
    season: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


# Events
class TourSearchResponse(BaseModel):
    search_id: int
    items: List["TourResponse"]  # forward ref

class ViewEventRequest(BaseModel):
    tour_id: int
    search_id: Optional[int] = None 


# Bookings
class CreateBookingRequest(BaseModel):
    tour_id: int
    search_id: Optional[int] = None


class BookingResponse(BaseModel):
    id: int
    status: str
    created_at: datetime
    tour: TourResponse

    class Config:
        from_attributes = True

TourSearchResponse.model_rebuild()
TourResponse.model_rebuild()
