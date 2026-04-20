from datetime import datetime
from fastapi import Request

from app.models.authorized_user import AuthorizedUser
from app.models.rfid_card import RfidCard
from app.models.rfid_assignment import RfidAssignment
from app.models.device import Device
from app.models.access_log import AccessLog
from app.models.staff_user import StaffUser


def authorized_user_out(u: AuthorizedUser, request: Request | None = None) -> dict:
    photo_url = None
    if request and u.path:
        photo_url = str(request.url_for("static", path=u.path))

    return {
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "full_name": f"{u.first_name} {u.last_name}",
        "gender": u.gender,
        "phone": u.phone,
        "email": u.email,
        "reference_code": u.reference_code,
        "valid_from": u.valid_from.isoformat() if u.valid_from else None,
        "valid_until": u.valid_until.isoformat() if u.valid_until else None,
        "is_active": u.is_active,
        "notes": u.notes,
        "path": u.path,
        "photo_url": photo_url,
        "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


def staff_user_out(u: StaffUser) -> dict:
    return {
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "full_name": f"{u.first_name} {u.last_name}",
        "email": u.email,
        "is_active": u.is_active,
        "role_name": u.role.name if u.role else None,
        "failed_login_attempts": u.failed_login_attempts,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "locked_until": u.locked_until.isoformat() if u.locked_until else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


def rfid_card_out(c: RfidCard) -> dict:
    return {
        "id": c.id,
        "uid": c.uid,
        "card_label": c.card_label,
        "status": c.status,
        "issued_at": c.issued_at.isoformat() if c.issued_at else None,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def device_out(d: Device) -> dict:
    return {
        "id": d.id,
        "device_name": d.device_name,
        "device_code": d.device_code,
        "location": d.location,
        "is_active": d.is_active,
        "is_for_enrollment": d.is_for_enrollment,
        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


def assignment_out(a: RfidAssignment, request: Request | None = None) -> dict:
    return {
        "id": a.id,
        "rfid_card_id": a.rfid_card_id,
        "authorized_user_id": a.authorized_user_id,
        "assigned_by_staff_id": a.assigned_by_staff_id,
        "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        "expired_at": a.expired_at.isoformat() if a.expired_at else None,
        "unassigned_at": a.unassigned_at.isoformat() if a.unassigned_at else None,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        "rfid_card": rfid_card_out(a.rfid_card) if a.rfid_card else None,
        "authorized_user": authorized_user_out(a.authorized_user, request) if a.authorized_user else None,
    }


def access_log_out(log: AccessLog, request: Request | None = None) -> dict:
    return {
        "id": log.id,
        "device_id": log.device_id,
        "rfid_card_id": log.rfid_card_id,
        "authorized_user_id": log.authorized_user_id,
        "assignment_id": log.assignment_id,
        "uid_scanned": log.uid_scanned,
        "access_status": log.access_status,
        "access_direction": log.access_direction,
        "reason": log.reason,
        "scanned_at": log.scanned_at.isoformat() if log.scanned_at else None,
        "door_opened": log.door_opened,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "device": device_out(log.device) if log.device else None,
        "rfid_card": rfid_card_out(log.rfid_card) if log.rfid_card else None,
        "authorized_user": authorized_user_out(log.authorized_user, request) if log.authorized_user else None,
        "assignment": assignment_out(log.assignment, request) if log.assignment else None,
    }


def paginate(items, total: int, page: int, per_page: int, serializer) -> dict:
    total_pages = max(1, (total + per_page - 1) // per_page)

    return {
        "items": [serializer(item) for item in items],
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
        },
    }


def parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None