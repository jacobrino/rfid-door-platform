from datetime import datetime
from sqlalchemy.orm import Session

from app.crud.authorized_user import get_authorized_user_by_id
from app.crud.rfid_assignment import (
    create_rfid_assignment,
    get_active_assignment_by_card_id,
    get_rfid_assignment_by_id,
    update_rfid_assignment,
)
from app.crud.rfid_card import get_rfid_card_by_id
from app.models.rfid_assignment import RfidAssignment
from app.schemas.rfid_assignment import RfidAssignmentCreate, RfidAssignmentUpdate


class RfidAssignmentServiceError(Exception):
    pass


ALLOWED_ASSIGNABLE_CARD_STATUSES = {"available", "assigned"}
ALLOWED_REUSABLE_PREVIOUS_ASSIGNMENT_STATUSES = {"expired", "unassigned", "revoked"}


def create_rfid_assignment_service(
    db: Session,
    payload: RfidAssignmentCreate,
    assigned_by_staff_id: int,
) -> RfidAssignment:
    card = get_rfid_card_by_id(db, payload.rfid_card_id)
    if not card:
        raise RfidAssignmentServiceError("Carte RFID introuvable.")

    user = get_authorized_user_by_id(db, payload.authorized_user_id, include_deleted=True)
    if not user:
        raise RfidAssignmentServiceError("Utilisateur autorisé introuvable.")

    if user.deleted_at is not None:
        raise RfidAssignmentServiceError("Impossible d'attribuer une carte à un utilisateur supprimé.")

    if not user.is_active:
        raise RfidAssignmentServiceError("Impossible d'attribuer une carte à un utilisateur inactif.")

    if card.status not in ALLOWED_ASSIGNABLE_CARD_STATUSES:
        raise RfidAssignmentServiceError(
            "Cette carte ne peut pas être attribuée dans son état actuel."
        )

    active_assignment = get_active_assignment_by_card_id(db, payload.rfid_card_id)

    if active_assignment:
        previous_user_deleted = (
            active_assignment.authorized_user is not None
            and active_assignment.authorized_user.deleted_at is not None
        )

        previous_assignment_expired = (
            active_assignment.expired_at is not None
            and active_assignment.expired_at <= datetime.utcnow()
        )

        previous_assignment_reusable = (
            active_assignment.status in ALLOWED_REUSABLE_PREVIOUS_ASSIGNMENT_STATUSES
            or active_assignment.unassigned_at is not None
            or previous_assignment_expired
            or previous_user_deleted
        )

        if not previous_assignment_reusable:
            raise RfidAssignmentServiceError(
                "Cette carte possède déjà une affectation active non réattribuable."
            )

    assignment = create_rfid_assignment(db, payload, assigned_by_staff_id=assigned_by_staff_id)

    card.status = "assigned"
    db.commit()
    db.refresh(card)

    return assignment


def unassign_rfid_assignment_service(
    db: Session,
    assignment_id: int,
    notes: str | None = None,
) -> RfidAssignment:
    assignment = get_rfid_assignment_by_id(db, assignment_id)

    if not assignment:
        raise RfidAssignmentServiceError("Affectation introuvable.")

    if assignment.status != "active":
        raise RfidAssignmentServiceError("Seule une affectation active peut être retirée.")

    payload = RfidAssignmentUpdate(
        expired_at=assignment.expired_at,
        unassigned_at=datetime.utcnow(),
        status="unassigned",
        notes=notes if notes is not None else assignment.notes,
    )

    updated_assignment = update_rfid_assignment(db, assignment, payload)

    if updated_assignment.rfid_card:
        updated_assignment.rfid_card.status = "available"
        db.commit()
        db.refresh(updated_assignment.rfid_card)

    return updated_assignment


def revoke_rfid_assignment_service(
    db: Session,
    assignment_id: int,
    notes: str | None = None,
) -> RfidAssignment:
    assignment = get_rfid_assignment_by_id(db, assignment_id)

    if not assignment:
        raise RfidAssignmentServiceError("Affectation introuvable.")

    if assignment.status != "active":
        raise RfidAssignmentServiceError("Seule une affectation active peut être révoquée.")

    payload = RfidAssignmentUpdate(
        expired_at=assignment.expired_at,
        unassigned_at=datetime.utcnow(),
        status="revoked",
        notes=notes if notes is not None else assignment.notes,
    )

    updated_assignment = update_rfid_assignment(db, assignment, payload)

    if updated_assignment.rfid_card:
        updated_assignment.rfid_card.status = "available"
        db.commit()
        db.refresh(updated_assignment.rfid_card)

    return updated_assignment


def expire_rfid_assignment_service(
    db: Session,
    assignment_id: int,
    notes: str | None = None,
) -> RfidAssignment:
    assignment = get_rfid_assignment_by_id(db, assignment_id)

    if not assignment:
        raise RfidAssignmentServiceError("Affectation introuvable.")

    if assignment.status != "active":
        raise RfidAssignmentServiceError("Seule une affectation active peut expirer.")

    now = datetime.utcnow()

    payload = RfidAssignmentUpdate(
        expired_at=now,
        unassigned_at=assignment.unassigned_at,
        status="expired",
        notes=notes if notes is not None else assignment.notes,
    )

    updated_assignment = update_rfid_assignment(db, assignment, payload)

    if updated_assignment.rfid_card:
        updated_assignment.rfid_card.status = "available"
        db.commit()
        db.refresh(updated_assignment.rfid_card)

    return updated_assignment