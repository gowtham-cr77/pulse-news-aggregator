"""User Service: registration, authentication, and category preference management."""

from typing import List

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import Category, User, UserPreference
from app.schemas.schemas import (
    AuthResponse,
    CategoryOut,
    PreferencesOut,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)


def register_user(db: Session, payload: UserRegisterRequest) -> AuthResponse:
    """Register a new reader account with securely hashed password."""
    email_norm = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email_norm))
    if existing:
        raise ValueError("An account with this email already exists")

    user = User(
        email=email_norm,
        display_name=payload.display_name.strip() or "Reader",
        password_hash=hash_password(payload.password),
        role="reader",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email, user.role)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


def authenticate_user(db: Session, payload: UserLoginRequest) -> AuthResponse:
    """Verify credentials and return a signed JWT token."""
    email_norm = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_norm))
    if not user or not verify_password(payload.password, user.password_hash):
        raise PermissionError("Invalid email or password")

    token = create_access_token(user.id, user.email, user.role)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


def get_user_preferences(db: Session, user: User) -> PreferencesOut:
    """Return the user's preferred category IDs and category objects."""
    cats = db.scalars(
        select(Category)
        .join(UserPreference, UserPreference.category_id == Category.id)
        .where(UserPreference.user_id == user.id)
        .order_by(Category.name.asc())
    ).all()
    return PreferencesOut(
        category_ids=[c.id for c in cats],
        categories=[
            CategoryOut(id=c.id, name=c.name, slug=c.slug, keywords=c.keywords or [])
            for c in cats
        ],
    )


def update_user_preferences(
    db: Session, user: User, category_ids: List[int]
) -> PreferencesOut:
    """Replace the user's preferred categories with the validated selection."""
    unique_ids = list(dict.fromkeys(category_ids))
    if unique_ids:
        valid_cats = db.scalars(select(Category).where(Category.id.in_(unique_ids))).all()
        if len(valid_cats) != len(unique_ids):
            raise ValueError("One or more category IDs are invalid")

    db.execute(delete(UserPreference).where(UserPreference.user_id == user.id))
    for cid in unique_ids:
        db.add(UserPreference(user_id=user.id, category_id=cid))
    db.commit()
    return get_user_preferences(db, user)
