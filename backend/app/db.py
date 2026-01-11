from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# подключение БД
DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# создание базового класса
class Base(DeclarativeBase):
    pass
