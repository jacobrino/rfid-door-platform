from datetime import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.crud.rfid_assignment import (
    get_authorized_users_for_assignment_filter,
    get_rfid_assignment_by_id,
    get_rfid_assignments_paginated,
    get_rfid_cards_for_assignment_filter,
    get_staff_users_for_assignment_filter,
)
from app.crud.authorized_user import get_authorized_users
from app.crud.rfid_card import get_assignable_rfid_cards
from app.models.staff_user import StaffUser
from app.schemas.rfid_assignment import RfidAssignmentCreate
from app.services.rfid_assignment_service import (
    RfidAssignmentServiceError,
    create_rfid_assignment_service,
    expire_rfid_assignment_service,
    revoke_rfid_assignment_service,
    unassign_rfid_assignment_service,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_PER_PAGE = 10
ASSIGNMENT_STATUSES = ["active", "expired", "unassigned", "revoked"]


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value)


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_optional_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value.strip())


@router.get("/assignments", response_class=HTMLResponse)
def assignments_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    rfid_card_id: str | None = Query(default=None),
    authorized_user_id: str | None = Query(default=None),
    assigned_by_staff_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    parsed_rfid_card_id = parse_optional_int(rfid_card_id)
    parsed_authorized_user_id = parse_optional_int(authorized_user_id)
    parsed_assigned_by_staff_id = parse_optional_int(assigned_by_staff_id)

    assignments, total = get_rfid_assignments_paginated(
        db,
        page=page,
        per_page=DEFAULT_PER_PAGE,
        rfid_card_id=parsed_rfid_card_id,
        authorized_user_id=parsed_authorized_user_id,
        assigned_by_staff_id=parsed_assigned_by_staff_id,
        status=status,
    )

    cards = get_rfid_cards_for_assignment_filter(db)
    users = get_authorized_users_for_assignment_filter(db)
    staff_users = get_staff_users_for_assignment_filter(db)

    total_pages = max(1, (total + DEFAULT_PER_PAGE - 1) // DEFAULT_PER_PAGE)
    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))

    filters = {
        "rfid_card_id": parsed_rfid_card_id,
        "authorized_user_id": parsed_authorized_user_id,
        "assigned_by_staff_id": parsed_assigned_by_staff_id,
        "status": status or "",
    }

    return templates.TemplateResponse(
        request=request,
        name="assignments/index.html",
        context={
            "request": request,
            "assignments": assignments,
            "cards": cards,
            "users": users,
            "staff_users": staff_users,
            "filters": filters,
            "statuses": ASSIGNMENT_STATUSES,
            "current_page": page,
            "total": total,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next,
            "previous_page": page - 1,
            "next_page": page + 1,
            "page_numbers": page_numbers,
            "current_user": current_user,
        },
    )


@router.get("/assignments/create", response_class=HTMLResponse)
def assignments_create_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    cards = get_assignable_rfid_cards(db)
    users = get_authorized_users(db)

    now = datetime.now()
    request.state.now = now

    return templates.TemplateResponse(
        request=request,
        name="assignments/create.html",
        context={
            "request": request,
            "error": None,
            "form_data": {},
            "cards": cards,
            "users": users,
            "current_user": current_user,
            "statuses": ASSIGNMENT_STATUSES,
        },
    )


@router.post("/assignments/create", response_class=HTMLResponse)
def assignments_store(
    request: Request,
    rfid_card_id: int = Form(...),
    authorized_user_id: int = Form(...),
    assigned_at: str | None = Form(None),
    expired_at: str | None = Form(None),
    unassigned_at: str | None = Form(None),
    status: str = Form(...),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    cards = get_assignable_rfid_cards(db)
    users = get_authorized_users(db)

    form_data = {
        "rfid_card_id": rfid_card_id,
        "authorized_user_id": authorized_user_id,
        "assigned_at": assigned_at or "",
        "expired_at": expired_at or "",
        "unassigned_at": unassigned_at or "",
        "status": status,
        "notes": clean_optional_string(notes),
    }

    try:
        payload = RfidAssignmentCreate(
            rfid_card_id=rfid_card_id,
            authorized_user_id=authorized_user_id,
            assigned_at=parse_optional_datetime(assigned_at),
            expired_at=parse_optional_datetime(expired_at),
            unassigned_at=parse_optional_datetime(unassigned_at),
            status=status,
            notes=clean_optional_string(notes),
        )

        create_rfid_assignment_service(
            db,
            payload,
            assigned_by_staff_id=current_user.id,
        )

        return RedirectResponse(url="/assignments", status_code=303)

    except ValidationError as e:
        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request,
            name="assignments/create.html",
            context={
                "request": request,
                "error": error_message,
                "form_data": form_data,
                "cards": cards,
                "users": users,
                "current_user": current_user,
                "statuses": ASSIGNMENT_STATUSES,
            },
            status_code=400,
        )
    except RfidAssignmentServiceError as e:
        return templates.TemplateResponse(
            request=request,
            name="assignments/create.html",
            context={
                "request": request,
                "error": str(e),
                "form_data": form_data,
                "cards": cards,
                "users": users,
                "current_user": current_user,
                "statuses": ASSIGNMENT_STATUSES,
            },
            status_code=400,
        )


@router.get("/assignments/{assignment_id}", response_class=HTMLResponse)
def assignments_show(
    assignment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    assignment = get_rfid_assignment_by_id(db, assignment_id)

    if not assignment:
        return RedirectResponse(url="/assignments", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="assignments/show.html",
        context={
            "request": request,
            "assignment": assignment,
            "current_user": current_user,
        },
    )


@router.post("/assignments/{assignment_id}/unassign")
def assignments_unassign(
    assignment_id: int,
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        unassign_rfid_assignment_service(db, assignment_id, notes=clean_optional_string(notes))
    except RfidAssignmentServiceError:
        pass

    return RedirectResponse(url=f"/assignments/{assignment_id}", status_code=303)


@router.post("/assignments/{assignment_id}/revoke")
def assignments_revoke(
    assignment_id: int,
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        revoke_rfid_assignment_service(db, assignment_id, notes=clean_optional_string(notes))
    except RfidAssignmentServiceError:
        pass

    return RedirectResponse(url=f"/assignments/{assignment_id}", status_code=303)


@router.post("/assignments/{assignment_id}/expire")
def assignments_expire(
    assignment_id: int,
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        expire_rfid_assignment_service(db, assignment_id, notes=clean_optional_string(notes))
    except RfidAssignmentServiceError:
        pass

    return RedirectResponse(url=f"/assignments/{assignment_id}", status_code=303)