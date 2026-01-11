from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User
from .security import JWT_SECRET, JWT_ALG

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# сессия на один запрос
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# авторизация + получение пользователя
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG]) # декодировка токена
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # поиск пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
