from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import settings
from fastapi.responses import JSONResponse
from app.core.database import get_db
from app.models.staff_user import StaffUser
from app.core.security import verify_password

router = APIRouter(tags=["Web Auth"])
templates = Jinja2Templates(directory=settings.template_path)


@router.get("/login", name="auth.login.index",response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request},
    )


@router.post("/login", name="auth.login.store",response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip()
    password = password.strip()

    if not email or not password:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "L’adresse e-mail et le mot de passe sont obligatoires.",
            },
            status_code=400,
        )

    user = db.query(StaffUser).filter(StaffUser.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Adresse e-mail ou mot de passe incorrect.",
            },
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Ce compte est inactif.",
            },
            status_code=400,
        )

    request.session["user_id"] = user.id
    request.session["full_name"] = f"{user.first_name} {user.last_name}"
    request.session["role_name"] = user.role.name if user.role else ""

    return RedirectResponse(url=request.url_for('dashboard.index'), status_code=303)


@router.get("/me", name="auth.me")
def me(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")

    if not user_id:
        return JSONResponse(
            status_code=401,
            content={
                "authenticated": False,
                "message": "Utilisateur non authentifié."
            },
        )

    user = (
        db.query(StaffUser)
        .filter(StaffUser.id == user_id)
        .first()
    )

    if not user:
        request.session.clear()
        return JSONResponse(
            status_code=401,
            content={
                "authenticated": False,
                "message": "Session invalide."
            },
        )

    if not user.is_active:
        request.session.clear()
        return JSONResponse(
            status_code=403,
            content={
                "authenticated": False,
                "message": "Compte inactif."
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "authenticated": True,
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "is_active": user.is_active,
                "role": user.role.name if user.role else None,
            },
        },
    )

@router.get("/logout",name="auth.logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=request.url_for('auth.login.index'), status_code=303)