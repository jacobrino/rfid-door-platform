from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.dependencies import get_current_user
from app.models.staff_user import StaffUser

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: StaffUser = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "user_role": current_user.role.name if current_user.role else "unknown",
        },
    )