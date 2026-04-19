# app/api/routes/api_json.py
#
# Routes JSON pour l'application Flutter.
# Adaptées EXACTEMENT à votre backend existant.
#
# Dans app/main.py, ajoutez ces lignes :
#
#   from fastapi.middleware.cors import CORSMiddleware
#   from app.api.routes.api_json import router as flutter_router
#
#   app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
#                      allow_methods=["*"], allow_headers=["*"])
#   app.include_router(flutter_router)

from datetime import datetime, time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_agent_or_admin
from app.core.security import verify_password

from app.models.access_log import AccessLog
from app.models.authorized_user import AuthorizedUser
from app.models.device import Device
from app.models.rfid_assignment import RfidAssignment
from app.models.rfid_card import RfidCard
from app.models.staff_user import StaffUser

from app.crud.authorized_user import get_authorized_user_by_id, get_authorized_users_paginated
from app.crud.rfid_card import get_rfid_card_by_id, get_rfid_cards_paginated
from app.crud.rfid_assignment import get_rfid_assignment_by_id, get_rfid_assignments_paginated
from app.crud.device import get_device_by_id, get_devices_paginated
from app.crud.access_log import get_access_log_by_id, get_access_logs_paginated

from app.schemas.authorized_user import AuthorizedUserCreate, AuthorizedUserUpdate
from app.schemas.rfid_card import RfidCardCreate, RfidCardUpdate
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.schemas.rfid_assignment import RfidAssignmentCreate

from app.services.authorized_user_service import (
    AuthorizedUserServiceError,
    create_authorized_user_service,
    update_authorized_user_service,
    soft_delete_authorized_user_service,
)
from app.services.rfid_card_service import (
    RfidCardServiceError,
    create_rfid_card_service,
    update_rfid_card_service,
)
from app.services.rfid_assignment_service import (
    RfidAssignmentServiceError,
    create_rfid_assignment_service,
    unassign_rfid_assignment_service,
    revoke_rfid_assignment_service,
    expire_rfid_assignment_service,
)
from app.services.device_service import (
    DeviceServiceError,
    create_device_service,
    update_device_service,
    regenerate_device_token_service,
)

router = APIRouter(prefix="/api/flutter", tags=["Flutter API"])


# ─────────────────────────────────────────────────────────────
# SERIALISEURS
# ─────────────────────────────────────────────────────────────

def _user_out(u: AuthorizedUser) -> dict:
    return {
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "gender": u.gender,
        "phone": u.phone,
        "email": u.email,
        "reference_code": u.reference_code,
        "valid_from": u.valid_from.isoformat() if u.valid_from else None,
        "valid_until": u.valid_until.isoformat() if u.valid_until else None,
        "is_active": u.is_active,
        "notes": u.notes,
        "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
        "created_at": u.created_at.isoformat(),
        "updated_at": u.updated_at.isoformat(),
    }

def _card_out(c: RfidCard) -> dict:
    return {
        "id": c.id,
        "uid": c.uid,
        "card_label": c.card_label,
        "status": c.status,
        "issued_at": c.issued_at.isoformat() if c.issued_at else None,
        "notes": c.notes,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }

def _assignment_out(a: RfidAssignment) -> dict:
    return {
        "id": a.id,
        "rfid_card_id": a.rfid_card_id,
        "authorized_user_id": a.authorized_user_id,
        "assigned_by_staff_id": a.assigned_by_staff_id,
        "assigned_at": a.assigned_at.isoformat(),
        "expired_at": a.expired_at.isoformat() if a.expired_at else None,
        "unassigned_at": a.unassigned_at.isoformat() if a.unassigned_at else None,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
        "rfid_card": _card_out(a.rfid_card) if a.rfid_card else None,
        "authorized_user": _user_out(a.authorized_user) if a.authorized_user else None,
    }

def _device_out(d: Device) -> dict:
    return {
        "id": d.id,
        "device_name": d.device_name,
        "device_code": d.device_code,
        "location": d.location,
        "is_active": d.is_active,
        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }

def _log_out(log: AccessLog) -> dict:
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
        "scanned_at": log.scanned_at.isoformat(),
        "door_opened": log.door_opened,
        "created_at": log.created_at.isoformat(),
        "device": _device_out(log.device) if log.device else None,
        "authorized_user": _user_out(log.authorized_user) if log.authorized_user else None,
    }

def _paginate(items, total, page, per_page, serializer):
    total_pages = max(1, (total + per_page - 1) // per_page)
    return {
        "items": [serializer(i) for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────

@router.post("/auth/login")
def flutter_login(payload: dict, request: Request, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").strip()
    password = (payload.get("password") or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email et mot de passe obligatoires.")

    user = db.query(StaffUser).filter(StaffUser.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Adresse e-mail ou mot de passe incorrect.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Ce compte est inactif.")

    # Même session que le back-office web
    request.session["user_id"] = user.id
    request.session["full_name"] = f"{user.first_name} {user.last_name}"
    request.session["role_name"] = user.role.name if user.role else ""

    return {
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role_name": user.role.name if user.role else None,
            "is_active": user.is_active,
        }
    }


@router.post("/auth/logout")
def flutter_logout(request: Request):
    request.session.clear()
    return {"success": True}


@router.get("/auth/me")
def flutter_me(current_user: StaffUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "role_name": current_user.role.name if current_user.role else None,
        "is_active": current_user.is_active,
    }


# ─────────────────────────────────────────────────────────────
# DASHBOARD — identique à dashboard.py
# ─────────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
def flutter_dashboard(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)

    def count(q): return q.scalar() or 0

    granted_today  = count(db.query(func.count(AccessLog.id)).filter(AccessLog.access_status == "granted",  AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end))
    denied_today   = count(db.query(func.count(AccessLog.id)).filter(AccessLog.access_status == "denied",   AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end))
    ignored_today  = count(db.query(func.count(AccessLog.id)).filter(AccessLog.access_status == "ignored",  AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end))
    entries_today  = count(db.query(func.count(AccessLog.id)).filter(AccessLog.access_status == "granted",  AccessLog.access_direction == "entry", AccessLog.scanned_at >= today_start, AccessLog.scanned_at <= today_end))

    active_users        = count(db.query(func.count(AuthorizedUser.id)).filter(AuthorizedUser.deleted_at.is_(None), AuthorizedUser.is_active.is_(True)))
    total_users         = count(db.query(func.count(AuthorizedUser.id)).filter(AuthorizedUser.deleted_at.is_(None)))
    active_assignments  = count(db.query(func.count(RfidAssignment.id)).filter(RfidAssignment.status == "active"))
    available_cards     = count(db.query(func.count(RfidCard.id)).filter(RfidCard.status == "available"))
    total_cards         = count(db.query(func.count(RfidCard.id)))
    assigned_cards      = count(db.query(func.count(RfidCard.id)).filter(RfidCard.status == "assigned"))
    active_devices      = count(db.query(func.count(Device.id)).filter(Device.is_active.is_(True)))
    total_devices       = count(db.query(func.count(Device.id)))
    expired_users       = count(db.query(func.count(AuthorizedUser.id)).filter(AuthorizedUser.deleted_at.is_(None), AuthorizedUser.valid_until.is_not(None), AuthorizedUser.valid_until < now))
    expired_assignments = count(db.query(func.count(RfidAssignment.id)).filter(RfidAssignment.expired_at.is_not(None), RfidAssignment.expired_at < now))
    abnormal_cards      = count(db.query(func.count(RfidCard.id)).filter(RfidCard.status.in_(["blocked", "lost", "damaged", "inactive"])))
    inactive_devices    = count(db.query(func.count(Device.id)).filter(Device.is_active.is_(False)))

    recent_events = db.query(AccessLog).order_by(AccessLog.scanned_at.desc(), AccessLog.id.desc()).limit(8).all()
    recent_denied = db.query(AccessLog).filter(AccessLog.access_status == "denied").order_by(AccessLog.scanned_at.desc()).limit(5).all()

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
        "recent_events": [_log_out(l) for l in recent_events],
        "recent_denied": [_log_out(l) for l in recent_denied],
    }


# ─────────────────────────────────────────────────────────────
# AUTHORIZED USERS
# ─────────────────────────────────────────────────────────────

@router.get("/authorized-users")
def flutter_list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[str] = None,
    validity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    users, total = get_authorized_users_paginated(
        db, page=page, per_page=per_page,
        search=search, is_active=is_active, validity=validity,
    )
    return _paginate(users, total, page, per_page, _user_out)


@router.get("/authorized-users/{user_id}")
def flutter_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    u = get_authorized_user_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return _user_out(u)


@router.post("/authorized-users", status_code=201)
def flutter_create_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        u = create_authorized_user_service(db, AuthorizedUserCreate(**payload))
        return _user_out(u)
    except (AuthorizedUserServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/authorized-users/{user_id}")
def flutter_update_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        u = update_authorized_user_service(db, user_id, AuthorizedUserUpdate(**payload))
        return _user_out(u)
    except (AuthorizedUserServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/authorized-users/{user_id}")
def flutter_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        soft_delete_authorized_user_service(db, user_id)
        return {"success": True}
    except AuthorizedUserServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────
# RFID CARDS
# ─────────────────────────────────────────────────────────────

@router.get("/rfid-cards")
def flutter_list_cards(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    cards, total = get_rfid_cards_paginated(db, page=page, per_page=per_page, search=search, status=status)
    return _paginate(cards, total, page, per_page, _card_out)


@router.get("/rfid-cards/{card_id}")
def flutter_get_card(card_id: int, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_agent_or_admin)):
    c = get_rfid_card_by_id(db, card_id)
    if not c:
        raise HTTPException(status_code=404, detail="Carte introuvable.")
    return _card_out(c)


@router.post("/rfid-cards", status_code=201)
def flutter_create_card(payload: dict, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        return _card_out(create_rfid_card_service(db, RfidCardCreate(**payload)))
    except (RfidCardServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rfid-cards/{card_id}")
def flutter_update_card(card_id: int, payload: dict, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        return _card_out(update_rfid_card_service(db, card_id, RfidCardUpdate(**payload)))
    except (RfidCardServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────
# ASSIGNMENTS
# ─────────────────────────────────────────────────────────────

@router.get("/assignments")
def flutter_list_assignments(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = None,
    rfid_card_id: Optional[int] = None,
    authorized_user_id: Optional[int] = None,
    assigned_by_staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    assignments, total = get_rfid_assignments_paginated(
        db, page=page, per_page=per_page,
        status=status, rfid_card_id=rfid_card_id,
        authorized_user_id=authorized_user_id,
        assigned_by_staff_id=assigned_by_staff_id,
    )
    return _paginate(assignments, total, page, per_page, _assignment_out)


@router.get("/assignments/{assignment_id}")
def flutter_get_assignment(assignment_id: int, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_agent_or_admin)):
    a = get_rfid_assignment_by_id(db, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Affectation introuvable.")
    return _assignment_out(a)


@router.post("/assignments", status_code=201)
def flutter_create_assignment(payload: dict, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        a = create_rfid_assignment_service(db, RfidAssignmentCreate(**payload), assigned_by_staff_id=current_user.id)
        return _assignment_out(a)
    except (RfidAssignmentServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assignments/{assignment_id}/unassign")
def flutter_unassign(assignment_id: int, payload: dict = {}, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        return _assignment_out(unassign_rfid_assignment_service(db, assignment_id, notes=payload.get("notes")))
    except RfidAssignmentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assignments/{assignment_id}/revoke")
def flutter_revoke(assignment_id: int, payload: dict = {}, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        return _assignment_out(revoke_rfid_assignment_service(db, assignment_id, notes=payload.get("notes")))
    except RfidAssignmentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assignments/{assignment_id}/expire")
def flutter_expire(assignment_id: int, payload: dict = {}, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        return _assignment_out(expire_rfid_assignment_service(db, assignment_id, notes=payload.get("notes")))
    except RfidAssignmentServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────
# DEVICES
# ─────────────────────────────────────────────────────────────

@router.get("/devices")
def flutter_list_devices(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    devices, total = get_devices_paginated(db, page=page, per_page=per_page, search=search, is_active=is_active)
    return _paginate(devices, total, page, per_page, _device_out)


@router.get("/devices/{device_id}")
def flutter_get_device(device_id: int, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_agent_or_admin)):
    d = get_device_by_id(db, device_id)
    if not d:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")
    return _device_out(d)


@router.post("/devices", status_code=201)
def flutter_create_device(payload: dict, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        device, plain_token = create_device_service(db, DeviceCreate(**payload))
        return {"device": _device_out(device), "api_token": plain_token}
    except (DeviceServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/devices/{device_id}")
def flutter_update_device(device_id: int, payload: dict, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        return _device_out(update_device_service(db, device_id, DeviceUpdate(**payload)))
    except (DeviceServiceError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/devices/{device_id}/regenerate-token")
def flutter_regen_token(device_id: int, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_admin)):
    try:
        device, plain_token = regenerate_device_token_service(db, device_id)
        return {"device": _device_out(device), "api_token": plain_token}
    except DeviceServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────
# ACCESS LOGS
# ─────────────────────────────────────────────────────────────

@router.get("/access-logs")
def flutter_list_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    uid: Optional[str] = None,
    device_id: Optional[str] = None,
    authorized_user_id: Optional[str] = None,
    access_status: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    def _pi(v): return int(v.strip()) if v and v.strip() else None
    def _pd(v):
        if not v or not v.strip(): return None
        try: return datetime.fromisoformat(v.strip())
        except: return None

    logs, total = get_access_logs_paginated(
        db, page=page, per_page=per_page,
        uid=uid,
        device_id=_pi(device_id),
        authorized_user_id=_pi(authorized_user_id),
        direction=direction,
        access_status=access_status,
        date_from=_pd(date_from),
        date_to=_pd(date_to) or datetime.now(),
    )
    return _paginate(logs, total, page, per_page, _log_out)


@router.get("/access-logs/{log_id}")
def flutter_get_log(log_id: int, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_agent_or_admin)):
    log = get_access_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log introuvable.")
    return _log_out(log)
