from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_agent_or_admin
from app.models.staff_user import StaffUser
from app.crud.access_log import get_access_log_by_id, get_access_logs_paginated
from app.api.json_routes.common import access_log_out, paginate, parse_optional_datetime, parse_optional_int

router = APIRouter(prefix="/api/access-logs", tags=["API Access Logs"])


@router.get("")
def api_access_logs_index(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    uid: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    authorized_user_id: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    access_status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    parsed_device_id = parse_optional_int(device_id)
    parsed_authorized_user_id = parse_optional_int(authorized_user_id)
    parsed_date_from = parse_optional_datetime(date_from)
    parsed_date_to = parse_optional_datetime(date_to) or datetime.now()

    logs, total = get_access_logs_paginated(
        db,
        page=page,
        per_page=per_page,
        uid=uid,
        device_id=parsed_device_id,
        authorized_user_id=parsed_authorized_user_id,
        direction=direction,
        access_status=access_status,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )

    result = paginate(logs, total, page, per_page, access_log_out)
    result["filters"] = {
        "uid": uid or "",
        "device_id": parsed_device_id,
        "authorized_user_id": parsed_authorized_user_id,
        "direction": direction or "",
        "access_status": access_status or "",
        "date_from": parsed_date_from.isoformat() if parsed_date_from else None,
        "date_to": parsed_date_to.isoformat() if parsed_date_to else None,
    }

    return result


@router.get("/{access_log_id}")
def api_access_logs_show(
    access_log_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    log = get_access_log_by_id(db, access_log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Log introuvable.")

    return access_log_out(log)