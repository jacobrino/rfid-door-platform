from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.staff_user import StaffUser
from app.schemas.staff_user import StaffUserCreate, StaffUserUpdate
from app.services import staff_user_service
from app.api.json_routes.common import paginate, staff_user_out

router = APIRouter(prefix="/api/staff-users", tags=["API Staff Users"])


@router.get("")
def api_staff_users_index(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    data = staff_user_service.list_staff_users(
        db,
        page=page,
        per_page=per_page,
        search=search,
        is_active=is_active,
    )

    result = paginate(
        data["items"],
        data["total"],
        data["page"],
        data["per_page"],
        staff_user_out,
    )

    result["filters"] = {
        "search": data["search"],
        "is_active": data["is_active"],
    }

    return result


@router.get("/{staff_user_id}")
def api_staff_users_show(
    staff_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    staff_user = staff_user_service.get_staff_user_or_404(db, staff_user_id)
    return staff_user_out(staff_user)


@router.post("", status_code=status.HTTP_201_CREATED)
def api_staff_users_store(
    payload: StaffUserCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        staff_user = staff_user_service.create_staff_user(db, payload)
        return staff_user_out(staff_user)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=getattr(exc, "detail", str(exc)),
        )


@router.put("/{staff_user_id}")
def api_staff_users_update(
    staff_user_id: int,
    payload: StaffUserUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    try:
        staff_user = staff_user_service.update_staff_user(db, staff_user_id, payload)
        return staff_user_out(staff_user)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=getattr(exc, "detail", str(exc)),
        )


@router.post("/{staff_user_id}/toggle-status")
def api_staff_users_toggle_status(
    staff_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    staff_user = staff_user_service.toggle_staff_user_status(db, staff_user_id)
    return {
        "success": True,
        "message": "Statut mis à jour.",
        "staff_user": staff_user_out(staff_user),
    }