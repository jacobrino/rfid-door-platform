from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.models.staff_user import StaffUser
from app.crud.rfid_assignment import (
    get_rfid_assignment_by_id,
    get_rfid_assignments_paginated,
)
from app.schemas.rfid_assignment import RfidAssignmentCreate
from app.services.rfid_assignment_service import (
    RfidAssignmentServiceError,
    create_rfid_assignment_service,
    expire_rfid_assignment_service,
    revoke_rfid_assignment_service,
    unassign_rfid_assignment_service,
)
from app.api.json_routes.common import assignment_out, paginate

router = APIRouter(prefix="/api/assignments", tags=["API Assignments"])


@router.get("")
def api_assignments_index(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    rfid_card_id: int | None = Query(default=None),
    authorized_user_id: int | None = Query(default=None),
    assigned_by_staff_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    assignments, total = get_rfid_assignments_paginated(
        db,
        page=page,
        per_page=per_page,
        status=status_filter,
        rfid_card_id=rfid_card_id,
        authorized_user_id=authorized_user_id,
        assigned_by_staff_id=assigned_by_staff_id,
    )

    result = paginate(assignments, total, page, per_page, assignment_out)
    result["filters"] = {
        "status": status_filter or "",
        "rfid_card_id": rfid_card_id,
        "authorized_user_id": authorized_user_id,
        "assigned_by_staff_id": assigned_by_staff_id,
    }

    return result


@router.get("/{assignment_id}")
def api_assignments_show(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    assignment = get_rfid_assignment_by_id(db, assignment_id)

    if not assignment:
        raise HTTPException(status_code=404, detail="Affectation introuvable.")

    return assignment_out(assignment)


@router.post("", status_code=status.HTTP_201_CREATED)
def api_assignments_store(
    payload: RfidAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        assignment = create_rfid_assignment_service(
            db,
            payload,
            assigned_by_staff_id=current_user.id,
        )
        return assignment_out(assignment)
    except (RfidAssignmentServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{assignment_id}/unassign")
def api_assignments_unassign(
    assignment_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    payload = payload or {}

    try:
        assignment = unassign_rfid_assignment_service(
            db,
            assignment_id,
            notes=payload.get("notes"),
        )
        return assignment_out(assignment)
    except RfidAssignmentServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{assignment_id}/revoke")
def api_assignments_revoke(
    assignment_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    payload = payload or {}

    try:
        assignment = revoke_rfid_assignment_service(
            db,
            assignment_id,
            notes=payload.get("notes"),
        )
        return assignment_out(assignment)
    except RfidAssignmentServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{assignment_id}/expire")
def api_assignments_expire(
    assignment_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    payload = payload or {}

    try:
        assignment = expire_rfid_assignment_service(
            db,
            assignment_id,
            notes=payload.get("notes"),
        )
        return assignment_out(assignment)
    except RfidAssignmentServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))