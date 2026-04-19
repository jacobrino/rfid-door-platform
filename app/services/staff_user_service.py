from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crud import staff_user as staff_user_crud
from app.schemas.staff_user import StaffUserCreate, StaffUserUpdate


def get_agent_role_or_404(db: Session):
    role = staff_user_crud.get_agent_role(db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Le rôle agent est introuvable.",
        )
    return role


def get_staff_user_or_404(db: Session, staff_user_id: int):
    staff_user = staff_user_crud.get_staff_user_by_id(db, staff_user_id)
    if not staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent introuvable.",
        )
    return staff_user


def ensure_email_is_unique(
    db: Session,
    email: str,
    exclude_staff_user_id: int | None = None,
) -> None:
    existing_user = staff_user_crud.get_staff_user_by_email(
        db,
        email=email.strip().lower(),
        exclude_staff_user_id=exclude_staff_user_id,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse email est déjà utilisée.",
        )


def list_staff_users(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    is_active: str | None = None,
) -> dict:
    if page < 1:
        page = 1

    if per_page < 1:
        per_page = 10

    staff_users, total = staff_user_crud.get_staff_users_paginated(
        db,
        page=page,
        per_page=per_page,
        search=search,
        is_active=is_active,
    )

    total_pages = ceil(total / per_page) if total > 0 else 1

    return {
        "items": staff_users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "search": search or "",
        "is_active": is_active or "",
    }


def create_staff_user(db: Session, payload: StaffUserCreate):
    role = get_agent_role_or_404(db)

    normalized_email = payload.email.strip().lower()
    ensure_email_is_unique(db, normalized_email)

    return staff_user_crud.create_staff_user(
        db,
        role_id=role.id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )


def update_staff_user(db: Session, staff_user_id: int, payload: StaffUserUpdate):
    staff_user = get_staff_user_or_404(db, staff_user_id)

    normalized_email = payload.email.strip().lower()
    ensure_email_is_unique(
        db,
        normalized_email,
        exclude_staff_user_id=staff_user.id,
    )

    password_hash = None
    if payload.password:
        password_hash = hash_password(payload.password)

    return staff_user_crud.update_staff_user(
        db,
        staff_user,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=normalized_email,
        is_active=payload.is_active,
        password_hash=password_hash,
    )


def deactivate_staff_user(db: Session, staff_user_id: int):
    staff_user = get_staff_user_or_404(db, staff_user_id)
    return staff_user_crud.deactivate_staff_user(db, staff_user)


def toggle_staff_user_status(db: Session, staff_user_id: int):
    staff_user = get_staff_user_or_404(db, staff_user_id)
    return staff_user_crud.toggle_staff_user_status(db, staff_user)