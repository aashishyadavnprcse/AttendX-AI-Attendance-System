from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.token import Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user (student, teacher, admin) with optional facial embedding vector.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    if user_in.roll_number:
        existing_roll = db.query(User).filter(User.roll_number == user_in.roll_number).first()
        if existing_roll:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Roll number '{user_in.roll_number}' is already assigned to another student.",
            )

    new_user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        roll_number=user_in.roll_number,
        embedding_vector=user_in.embedding_vector,
        avatar_url=user_in.avatar_url,
        parent_name=user_in.parent_name,
        parent_phone=user_in.parent_phone,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    response = UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role,
        roll_number=new_user.roll_number,
        avatar_url=new_user.avatar_url,
        parent_name=new_user.parent_name,
        parent_phone=new_user.parent_phone,
        created_at=new_user.created_at,
        has_biometric_enrolled=bool(new_user.embedding_vector),
    )
    return response


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user with email/roll number and password, returning JWT Bearer token.
    """
    identifier = (credentials.email or credentials.username or "").strip()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email address or student roll number is required.",
        )

    # Allow login by email (case-insensitive) or roll number
    user = db.query(User).filter(
        (User.email.ilike(identifier)) | (User.roll_number == identifier)
    ).first()

    if not user or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password combination.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(subject=user.id, role=role_val, email=user.email)
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=role_val,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get profile information of the currently authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        roll_number=current_user.roll_number,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        has_biometric_enrolled=bool(current_user.embedding_vector),
    )
