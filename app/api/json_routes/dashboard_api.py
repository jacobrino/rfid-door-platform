from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_agent_or_admin
from app.models.access_log import AccessLog
from app.models.authorized_user import AuthorizedUser
from app.models.device import Device
from app.models.rfid_assignment import RfidAssignment
from app.models.rfid_card import RfidCard
from app.models.staff_user import StaffUser
from app.api.json_routes.common import access_log_out

router = APIRouter(prefix="/api/dashboard", tags=["API Dashboard"])


@router.get("/stats")
def api_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)

    def count(query):
        return query.scalar() or 0

    granted_today = count(
        db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "granted",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
    )

    denied_today = count(
        db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "denied",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
    )

    ignored_today = count(
        db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "ignored",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
    )

    entries_today = count(
        db.query(func.count(AccessLog.id)).filter(
            AccessLog.access_status == "granted",
            AccessLog.access_direction == "entry",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
    )

    active_users = count(
        db.query(func.count(AuthorizedUser.id)).filter(
            AuthorizedUser.deleted_at.is_(None),
            AuthorizedUser.is_active.is_(True),
        )
    )

    total_users = count(
        db.query(func.count(AuthorizedUser.id)).filter(
            AuthorizedUser.deleted_at.is_(None),
        )
    )

    active_assignments = count(
        db.query(func.count(RfidAssignment.id)).filter(
            RfidAssignment.status == "active",
        )
    )

    available_cards = count(
        db.query(func.count(RfidCard.id)).filter(
            RfidCard.status == "available",
        )
    )

    total_cards = count(db.query(func.count(RfidCard.id)))
    assigned_cards = count(
        db.query(func.count(RfidCard.id)).filter(
            RfidCard.status == "assigned",
        )
    )

    active_devices = count(
        db.query(func.count(Device.id)).filter(Device.is_active.is_(True))
    )

    total_devices = count(db.query(func.count(Device.id)))

    expired_users = count(
        db.query(func.count(AuthorizedUser.id)).filter(
            AuthorizedUser.deleted_at.is_(None),
            AuthorizedUser.valid_until.is_not(None),
            AuthorizedUser.valid_until < now,
        )
    )

    expired_assignments = count(
        db.query(func.count(RfidAssignment.id)).filter(
            RfidAssignment.expired_at.is_not(None),
            RfidAssignment.expired_at < now,
        )
    )

    abnormal_cards = count(
        db.query(func.count(RfidCard.id)).filter(
            RfidCard.status.in_(["blocked", "lost", "damaged", "inactive"])
        )
    )

    inactive_devices = count(
        db.query(func.count(Device.id)).filter(Device.is_active.is_(False))
    )

    recent_events = (
        db.query(AccessLog)
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .limit(8)
        .all()
    )

    recent_denied = (
        db.query(AccessLog)
        .filter(AccessLog.access_status == "denied")
        .order_by(AccessLog.scanned_at.desc())
        .limit(5)
        .all()
    )

    return {
        "today_access": granted_today + denied_today + ignored_today,
        "today_granted": granted_today,
        "today_denied": denied_today,
        "today_ignored": ignored_today,
        "entries_today": entries_today,
        "total_authorized_users": total_users,
        "active_users": active_users,
        "active_assignments": active_assignments,
        "available_cards": available_cards,
        "total_rfid_cards": total_cards,
        "assigned_cards": assigned_cards,
        "active_devices": active_devices,
        "total_devices": total_devices,
        "expired_users": expired_users,
        "expired_assignments": expired_assignments,
        "abnormal_cards": abnormal_cards,
        "inactive_devices": inactive_devices,
        "recent_events": [access_log_out(log) for log in recent_events],
        "recent_denied": [access_log_out(log) for log in recent_denied],
    }