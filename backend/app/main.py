from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal
from .seed import seed_tours_if_empty
from .routers import dev_seed

from .routers import auth, tours, bookings, events, ml

app = FastAPI(title="Tour ML Picker Backend", version="1.0")

# CORS для React (Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dev_seed.router)

# init DB
Base.metadata.create_all(bind=engine)

# seed tours
db: Session = SessionLocal()
try:
    seed_tours_if_empty(db)
finally:
    db.close()

# routers
app.include_router(auth.router)
app.include_router(tours.router)
app.include_router(bookings.router)
app.include_router(events.router)
app.include_router(ml.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
