from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.models.staff_user import StaffUser
from app.crud.rfid_card import get_rfid_card_by_id, get_rfid_cards_paginated
from app.schemas.rfid_card import RfidCardCreate, RfidCardUpdate
from app.services.rfid_card_service import (
    RfidCardServiceError,
    create_rfid_card_service,
    update_rfid_card_service,
)

from app.services.rfid_uid_capture_service import (
    start_uid_capture,
    get_uid_capture_status,
    reset_uid_capture,
)

from app.api.json_routes.common import paginate, rfid_card_out

router = APIRouter(prefix="/api/rfid-cards", tags=["API RFID Cards"])


@router.get("")
def api_rfid_cards_index(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    cards, total = get_rfid_cards_paginated(
        db,
        page=page,
        per_page=per_page,
        search=search,
        status=status_filter,
    )

    result = paginate(cards, total, page, per_page, rfid_card_out)
    result["filters"] = {
        "search": search or "",
        "status": status_filter or "",
    }

    return result


@router.get("/{rfid_card_id}")
def api_rfid_cards_show(
    rfid_card_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    card = get_rfid_card_by_id(db, rfid_card_id)

    if not card:
        raise HTTPException(status_code=404, detail="Carte introuvable.")

    return rfid_card_out(card)


@router.post("", status_code=status.HTTP_201_CREATED)
def api_rfid_cards_store(
    payload: RfidCardCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        return rfid_card_out(create_rfid_card_service(db, payload))
    except (RfidCardServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{rfid_card_id}")
def api_rfid_cards_update(
    rfid_card_id: int,
    payload: RfidCardUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        return rfid_card_out(update_rfid_card_service(db, rfid_card_id, payload))
    except (RfidCardServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/uid-capture/start")
def api_rfid_cards_uid_capture_start(
    current_user: StaffUser = Depends(require_admin),
):
    capture = start_uid_capture(timeout_seconds=15)

    return {
        "success": True,
        "capture_id": capture["capture_id"],
        "status": capture["status"],
        "started_at": capture["started_at"].isoformat() if capture.get("started_at") else None,
        "expires_at": capture["expires_at"].isoformat() if capture.get("expires_at") else None,
    }


@router.get("/uid-capture/status/{capture_id}")
def api_rfid_cards_uid_capture_status(
    capture_id: str,
    current_user: StaffUser = Depends(require_admin),
):
    return get_uid_capture_status(capture_id)


@router.post("/uid-capture/reset")
def api_rfid_cards_uid_capture_reset(
    current_user: StaffUser = Depends(require_admin),
):
    reset_uid_capture()

    return {
        "success": True,
        "message": "Capture UID réinitialisée.",
    }