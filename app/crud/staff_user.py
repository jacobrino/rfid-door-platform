from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.staff_user import StaffUser


AGENT_ROLE_NAME = "agent"


def get_agent_role(db: Session) -> Role | None:
    return db.query(Role).filter(Role.name == AGENT_ROLE_NAME).first()


def get_staff_users_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    is_active: str | None = None,
) -> tuple[list[StaffUser], int]:
    query = db.query(StaffUser).join(Role).filter(Role.name == AGENT_ROLE_NAME)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                StaffUser.first_name.ilike(search_term),
                StaffUser.last_name.ilike(search_term),
                StaffUser.email.ilike(search_term),
            )
        )

    if is_active == "active":
        query = query.filter(StaffUser.is_active.is_(True))
    elif is_active == "inactive":
        query = query.filter(StaffUser.is_active.is_(False))

    total = query.count()
    offset = (page - 1) * per_page

    staff_users = (
        query.order_by(StaffUser.id.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return staff_users, total


def get_staff_user_by_id(db: Session, staff_user_id: int) -> StaffUser | None:
    return (
        db.query(StaffUser)
        .join(Role)
        .filter(StaffUser.id == staff_user_id, Role.name == AGENT_ROLE_NAME)
        .first()
    )


def get_staff_user_by_email(
    db: Session,
    email: str,
    exclude_staff_user_id: int | None = None,
) -> StaffUser | None:
    query = db.query(StaffUser).filter(StaffUser.email == email)

    if exclude_staff_user_id is not None:
        query = query.filter(StaffUser.id != exclude_staff_user_id)

    return query.first()


def create_staff_user(
    db: Session,
    *,
    role_id: int,
    first_name: str,
    last_name: str,
    email: str,
    password_hash: str,
    is_active: bool = True,
) -> StaffUser:
    staff_user = StaffUser(
        role_id=role_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        is_active=is_active,
    )
    db.add(staff_user)
    db.commit()
    db.refresh(staff_user)
    return staff_user


def update_staff_user(
    db: Session,
    staff_user: StaffUser,
    *,
    first_name: str,
    last_name: str,
    email: str,
    is_active: bool,
    password_hash: str | None = None,
) -> StaffUser:
    staff_user.first_name = first_name
    staff_user.last_name = last_name
    staff_user.email = email
    staff_user.is_active = is_active

    if password_hash:
        staff_user.password_hash = password_hash

    staff_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(staff_user)
    return staff_user


def deactivate_staff_user(db: Session, staff_user: StaffUser) -> StaffUser:
    staff_user.is_active = False
    staff_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(staff_user)
    return staff_user

def toggle_staff_user_status(db: Session, staff_user: StaffUser) -> StaffUser:
    staff_user.is_active = not staff_user.is_active
    staff_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(staff_user)
    return staff_user