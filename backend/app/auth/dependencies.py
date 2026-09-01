from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import User, UserRole
from app.auth.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_email = payload.get("sub")
    if not user_email:
        return None
    
    user = db.query(User).filter(User.email == user_email).first()
    return user

def require_auth(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

def require_admin(
    current_user: User = Depends(require_auth)
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authority/Admin privileges required"
        )
    return current_user

def require_inspector_or_admin(
    current_user: User = Depends(require_auth)
) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.INSPECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field Inspector or Admin privileges required"
        )
    return current_user
