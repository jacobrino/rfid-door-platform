import io
import json

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.models.staff_user import StaffUser
from app.crud.authorized_user import (
    get_authorized_user_by_id,
    get_authorized_users_paginated,
)
from app.schemas.authorized_user import AuthorizedUserCreate, AuthorizedUserUpdate
from app.services.authorized_user_service import (
    AuthorizedUserServiceError,
    create_authorized_user_service,
    soft_delete_authorized_user_service,
    update_authorized_user_service,
)
from app.api.json_routes.common import authorized_user_out, paginate

router = APIRouter(prefix="/api/authorized-users", tags=["API Authorized Users"])


def build_qr_payload(user) -> dict:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "gender": user.gender,
        "phone": user.phone,
        "email": user.email,
        "reference_code": user.reference_code,
        "valid_from": user.valid_from.isoformat() if user.valid_from else None,
        "valid_until": user.valid_until.isoformat() if user.valid_until else None,
        "is_active": user.is_active,
    }


@router.get("")
def api_authorized_users_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: str | None = Query(default=None),
    validity: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    users, total = get_authorized_users_paginated(
        db,
        page=page,
        per_page=per_page,
        search=search,
        is_active=is_active,
        validity=validity,
    )

    result = paginate(
        users,
        total,
        page,
        per_page,
        lambda user: authorized_user_out(user, request),
    )

    result["filters"] = {
        "search": search or "",
        "is_active": is_active or "",
        "validity": validity or "",
    }

    return result


@router.get("/{authorized_user_id}")
def api_authorized_users_show(
    authorized_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    data = authorized_user_out(user, request)
    data["qr_payload"] = build_qr_payload(user)

    return data


@router.post("", status_code=status.HTTP_201_CREATED)
def api_authorized_users_store(
    payload: AuthorizedUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        user = create_authorized_user_service(db, payload)
        return authorized_user_out(user, request)
    except (AuthorizedUserServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{authorized_user_id}")
def api_authorized_users_update(
    authorized_user_id: int,
    payload: AuthorizedUserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        user = update_authorized_user_service(db, authorized_user_id, payload)
        return authorized_user_out(user, request)
    except (AuthorizedUserServiceError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{authorized_user_id}")
def api_authorized_users_delete(
    authorized_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        soft_delete_authorized_user_service(db, authorized_user_id)
        return {
            "success": True,
            "message": "Utilisateur supprimé avec succès.",
        }
    except AuthorizedUserServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{authorized_user_id}/qr-payload")
def api_authorized_users_qr_payload(
    authorized_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    return build_qr_payload(user)


@router.get("/{authorized_user_id}/qr")
def api_authorized_users_qr(
    authorized_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    payload = build_qr_payload(user)

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(json.dumps(payload, ensure_ascii=False))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")