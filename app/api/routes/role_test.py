from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.dependencies import require_admin, require_agent_or_admin
from app.models.staff_user import StaffUser

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin-only", response_class=HTMLResponse)
def admin_only_page(
    request: Request,
    current_user: StaffUser = Depends(require_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard/admin_only.html",
        context={
            "request": request,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "user_role": current_user.role.name if current_user.role else "unknown",
        },
    )


@router.get("/staff-area", response_class=HTMLResponse)
def staff_area_page(
    request: Request,
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard/staff_area.html",
        context={
            "request": request,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "user_role": current_user.role.name if current_user.role else "unknown",
        },
    )