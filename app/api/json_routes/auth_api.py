from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import verify_password
from app.models.staff_user import StaffUser
from app.schemas.auth import LoginForm
from app.api.json_routes.common import staff_user_out

router = APIRouter(prefix="/api/auth", tags=["API Auth"])


@router.post("/login")
def api_login(
    payload: LoginForm,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    password = payload.password.strip()

    user = db.query(StaffUser).filter(StaffUser.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse e-mail ou mot de passe incorrect.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est inactif.",
        )

    request.session["user_id"] = user.id
    request.session["full_name"] = f"{user.first_name} {user.last_name}"
    request.session["role_name"] = user.role.name if user.role else ""

    return {
        "success": True,
        "message": "Connexion réussie.",
        "user": staff_user_out(user),
    }


@router.post("/logout")
def api_logout(request: Request):
    request.session.clear()
    return {
        "success": True,
        "message": "Déconnexion réussie.",
    }


@router.get("/me")
def api_me(current_user: StaffUser = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user": staff_user_out(current_user),
    }