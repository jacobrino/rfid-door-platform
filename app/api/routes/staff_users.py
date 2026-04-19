from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.staff_user import StaffUser
from app.schemas.staff_user import StaffUserCreate, StaffUserUpdate
from app.services import staff_user_service

from fastapi.templating import Jinja2Templates

from app.core.config import settings

templates = Jinja2Templates(directory=settings.template_path)

router = APIRouter(prefix="/staff-users", tags=["Staff Users"])


@router.get("/", name="staff_users.index")
def index(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    search: str | None = None,
    is_active: str | None = None,
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

    print('data : ',data["total"])
    print('data1 : ',data["items"][0].id)

    return templates.TemplateResponse(
        request=request,
        name="staff_users/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "staff_users": data["items"],
            "pagination": {
                "total": data["total"],
                "page": data["page"],
                "per_page": data["per_page"],
                "total_pages": data["total_pages"],
            },
            "filters": {
                "search": data["search"],
                "is_active": data["is_active"],
            },
        },
    )


@router.get("/create", name="staff_users.create")
def create_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="staff_users/create.html",
        context={
            "request": request,
            "current_user": current_user,
            "old": {},
            "errors": {},
        },
    )


@router.post("/create", name="staff_users.store")
def store(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirmation: str = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    form_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "password_confirmation": password_confirmation,
        "is_active": is_active,
    }

    try:
        payload = StaffUserCreate(**form_data)
        staff_user_service.create_staff_user(db, payload)

        return RedirectResponse(
            url=request.url_for("staff_users.index"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValidationError as exc:
        errors = {}

        for error in exc.errors():
            field = error["loc"][-1]
            errors[field] = error["msg"]

        return templates.TemplateResponse(
            request=request,
            name="staff_users/create.html",
            context={
                "request": request,
                "current_user": current_user,
                "old": form_data,
                "errors": errors,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="staff_users/create.html",
            context={
                "request": request,
                "current_user": current_user,
                "old": form_data,
                "errors": {
                    "general": getattr(
                        exc,
                        "detail",
                        "Une erreur est survenue lors de la création de l'agent.",
                    )
                },
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/{staff_user_id}", name="staff_users.show")
def show(
    request: Request,
    staff_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    staff_user = staff_user_service.get_staff_user_or_404(db, staff_user_id)

    return templates.TemplateResponse(
        request=request,
        name="staff_users/show.html",
        context={
            "request": request,
            "current_user": current_user,
            "staff_user": staff_user,
        },
    )


@router.get("/{staff_user_id}/edit", name="staff_users.edit")
def edit_page(
    request: Request,
    staff_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    staff_user = staff_user_service.get_staff_user_or_404(db, staff_user_id)

    return templates.TemplateResponse(
        request=request,
        name="staff_users/edit.html",
        context={
            "request": request,
            "current_user": current_user,
            "staff_user": staff_user,
            "old": {
                "first_name": staff_user.first_name,
                "last_name": staff_user.last_name,
                "email": staff_user.email,
                "is_active": staff_user.is_active,
            },
            "errors": {},
        },
    )


@router.post("/{staff_user_id}/edit", name="staff_users.update")
def update(
    request: Request,
    staff_user_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    password_confirmation: str = Form(""),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    staff_user = staff_user_service.get_staff_user_or_404(db, staff_user_id)

    form_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password or None,
        "password_confirmation": password_confirmation or None,
        "is_active": is_active,
    }

    try:
        payload = StaffUserUpdate(**form_data)
        staff_user_service.update_staff_user(db, staff_user_id, payload)

        return RedirectResponse(
            url=request.url_for("staff_users.show", staff_user_id=staff_user_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValidationError as exc:
        errors = {}

        for error in exc.errors():
            field = error["loc"][-1]
            errors[field] = error["msg"]

        return templates.TemplateResponse(
            request=request,
            name="staff_users/edit.html",
            context={
                "request": request,
                "current_user": current_user,
                "staff_user": staff_user,
                "old": form_data,
                "errors": errors,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="staff_users/edit.html",
            context={
                "request": request,
                "current_user": current_user,
                "staff_user": staff_user,
                "old": form_data,
                "errors": {
                    "general": getattr(
                        exc,
                        "detail",
                        "Une erreur est survenue lors de la modification de l'agent.",
                    )
                },
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

@router.post("/{staff_user_id}/toggle-status", name="staff_users.toggle_status")
def toggle_status(
    request: Request,
    staff_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    staff_user_service.toggle_staff_user_status(db, staff_user_id)

    return RedirectResponse(
        url=request.url_for("staff_users.edit", staff_user_id=staff_user_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )