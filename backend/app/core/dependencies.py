from typing import Optional, Union, List
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.token import TokenData

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Extract raw token from credentials or direct Authorization header
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            token = auth_header

    if not token or not token.strip():
        raise credentials_exception

    # 2. Sanitize token string
    token = token.strip()
    # Strip any leading 'Bearer' prefix (handles Swagger UI duplicate 'Bearer Bearer' paste)
    while token.lower().startswith("bearer"):
        parts = token.split(None, 1)
        if len(parts) > 1:
            token = parts[1].strip()
        else:
            token = ""
            break

    # Strip surrounding quotes and whitespace
    token = token.strip("\"' \t\r\n")

    if not token:
        raise credentials_exception

    # 3. Decode JWT payload
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exception

    # 4. Extract subject claim
    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    role: Optional[str] = payload.get("role")
    user_id_claim = payload.get("user_id")
    email_claim = payload.get("email")

    user: Optional[User] = None

    # 5. Look up user by ID (numeric sub or user_id claim)
    if isinstance(sub, int) or (isinstance(sub, str) and sub.isdigit()):
        user = db.query(User).filter(User.id == int(sub)).first()
    elif isinstance(sub, str) and "@" in sub:
        # Subject is an email address
        user = db.query(User).filter(User.email == sub).first()

    # Fallback to user_id claim if not found
    if not user and user_id_claim is not None:
        try:
            user = db.query(User).filter(User.id == int(user_id_claim)).first()
        except (ValueError, TypeError):
            pass

    # Fallback to email claim if not found
    if not user and email_claim:
        user = db.query(User).filter(User.email == str(email_claim)).first()

    # Fallback matching sub to user email or name
    if not user and isinstance(sub, str):
        user = db.query(User).filter((User.email == sub) | (User.name == sub)).first()

    if user is None:
        raise credentials_exception

    return user


def require_role(allowed_roles: List[Union[UserRole, str]]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        allowed_vals = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if user_role_val not in allowed_vals:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_vals}",
            )
        return current_user
    return role_checker
