from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.models.staff_user import StaffUser
from app.crud.device import get_device_by_id, get_devices_paginated
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.services.device_service import (
    DeviceServiceError,
    create_device_service,
    regenerate_device_token_service,
    update_device_service,
)
from app.api.json_routes.common import device_out, paginate

router = APIRouter(prefix="/api/devices", tags=["API Devices"])


@router.get("")
def api_devices_index(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    devices, total = get_devices_paginated(
        db,
        page=page,
        per_page=per_page,
        search=search,
        is_active=is_active,
    )

    result = paginate(devices, total, page, per_page, device_out)
    result["filters"] = {
        "search": search or "",
        "is_active": is_active or "",
    }

    return result


@router.get("/{device_id}")
def api_devices_show(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    device = get_device_by_id(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    return device_out(device)


@router.post("", status_code=status.HTTP_201_CREATED)
def api_devices_store(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        device, plain_token = create_device_service(db, payload)
        return {
            "device": device_out(device),
            "api_token": plain_token,
        }
    except (DeviceServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{device_id}")
def api_devices_update(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        device = update_device_service(db, device_id, payload)
        return device_out(device)
    except (DeviceServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{device_id}/regenerate-token")
def api_devices_regenerate_token(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        device, plain_token = regenerate_device_token_service(db, device_id)
        return {
            "device": device_out(device),
            "api_token": plain_token,
        }
    except DeviceServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))