from datetime import datetime, time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.access_log import AccessLog
from app.models.authorized_user import AuthorizedUser
from app.models.device import Device
from app.models.rfid_assignment import RfidAssignment
from app.models.rfid_card import RfidCard
from app.models.staff_user import StaffUser

router = APIRouter(tags=["Web Dashboard"])
templates = Jinja2Templates(directory=settings.template_path)


@router.get("/dashboard", name="dashboard.index",response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)

    granted_today = (
        db.query(func.count(AccessLog.id))
        .filter(
            AccessLog.access_status == "granted",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
        .scalar()
        or 0
    )

    denied_today = (
        db.query(func.count(AccessLog.id))
        .filter(
            AccessLog.access_status == "denied",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
        .scalar()
        or 0
    )

    ignored_today = (
        db.query(func.count(AccessLog.id))
        .filter(
            AccessLog.access_status == "ignored",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
        .scalar()
        or 0
    )

    entries_today = (
        db.query(func.count(AccessLog.id))
        .filter(
            AccessLog.access_status == "granted",
            AccessLog.access_direction == "entry",
            AccessLog.scanned_at >= today_start,
            AccessLog.scanned_at <= today_end,
        )
        .scalar()
        or 0
    )

    active_authorized_users = (
        db.query(func.count(AuthorizedUser.id))
        .filter(
            AuthorizedUser.deleted_at.is_(None),
            AuthorizedUser.is_active.is_(True),
        )
        .scalar()
        or 0
    )

    active_assignments = (
        db.query(func.count(RfidAssignment.id))
        .filter(RfidAssignment.status == "active")
        .scalar()
        or 0
    )

    available_cards = (
        db.query(func.count(RfidCard.id))
        .filter(RfidCard.status == "available")
        .scalar()
        or 0
    )

    active_devices = (
        db.query(func.count(Device.id))
        .filter(Device.is_active.is_(True))
        .scalar()
        or 0
    )

    expired_users = (
        db.query(func.count(AuthorizedUser.id))
        .filter(
            AuthorizedUser.deleted_at.is_(None),
            AuthorizedUser.valid_until.is_not(None),
            AuthorizedUser.valid_until < now,
        )
        .scalar()
        or 0
    )

    expired_assignments = (
        db.query(func.count(RfidAssignment.id))
        .filter(
            RfidAssignment.expired_at.is_not(None),
            RfidAssignment.expired_at < now,
        )
        .scalar()
        or 0
    )

    abnormal_cards = (
        db.query(func.count(RfidCard.id))
        .filter(RfidCard.status.in_(["blocked", "lost", "damaged", "inactive"]))
        .scalar()
        or 0
    )

    inactive_devices = (
        db.query(func.count(Device.id))
        .filter(Device.is_active.is_(False))
        .scalar()
        or 0
    )

    recent_events = (
        db.query(AccessLog)
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .limit(5)
        .all()
    )

    recent_denied_events = (
        db.query(AccessLog)
        .filter(AccessLog.access_status == "denied")
        .order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "kpis": {
                "granted_today": granted_today,
                "denied_today": denied_today,
                "ignored_today": ignored_today,
                "entries_today": entries_today,
                "active_authorized_users": active_authorized_users,
                "active_assignments": active_assignments,
                "available_cards": available_cards,
                "active_devices": active_devices,
                "expired_users": expired_users,
                "expired_assignments": expired_assignments,
                "abnormal_cards": abnormal_cards,
                "inactive_devices": inactive_devices,
            },
            "recent_events": recent_events,
            "recent_denied_events": recent_denied_events,
        },
    )