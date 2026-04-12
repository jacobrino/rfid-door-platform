from sqlalchemy.orm import Session

from app.crud.authorized_user import (
    create_authorized_user,
    email_exists,
    get_authorized_user_by_id,
    phone_exists,
    reference_code_exists,
    soft_delete_authorized_user,
    update_authorized_user,
)
from app.models.authorized_user import AuthorizedUser
from app.schemas.authorized_user import AuthorizedUserCreate, AuthorizedUserUpdate


class AuthorizedUserServiceError(Exception):
    pass


def create_authorized_user_service(
    db: Session,
    payload: AuthorizedUserCreate,
) -> AuthorizedUser:
    if payload.reference_code and reference_code_exists(db, payload.reference_code):
        raise AuthorizedUserServiceError("Ce code de référence existe déjà.")

    if payload.email and email_exists(db, payload.email):
        raise AuthorizedUserServiceError("Cette adresse e-mail existe déjà.")

    if payload.phone and phone_exists(db, payload.phone):
        raise AuthorizedUserServiceError("Ce numéro de téléphone existe déjà.")

    return create_authorized_user(db, payload)


def update_authorized_user_service(
    db: Session,
    authorized_user_id: int,
    payload: AuthorizedUserUpdate,
) -> AuthorizedUser:
    authorized_user = get_authorized_user_by_id(db, authorized_user_id)

    if not authorized_user:
        raise AuthorizedUserServiceError("Utilisateur autorisé introuvable.")

    if payload.reference_code and reference_code_exists(
        db,
        payload.reference_code,
        exclude_user_id=authorized_user.id,
    ):
        raise AuthorizedUserServiceError("Ce code de référence existe déjà.")

    if payload.email and email_exists(
        db,
        payload.email,
        exclude_user_id=authorized_user.id,
    ):
        raise AuthorizedUserServiceError("Cette adresse e-mail existe déjà.")

    if payload.phone and phone_exists(
        db,
        payload.phone,
        exclude_user_id=authorized_user.id,
    ):
        raise AuthorizedUserServiceError("Ce numéro de téléphone existe déjà.")

    return update_authorized_user(db, authorized_user, payload)


def soft_delete_authorized_user_service(
    db: Session,
    authorized_user_id: int,
) -> AuthorizedUser:
    authorized_user = get_authorized_user_by_id(
        db,
        authorized_user_id,
        include_deleted=True,
    )

    if not authorized_user:
        raise AuthorizedUserServiceError("Utilisateur autorisé introuvable.")

    if authorized_user.deleted_at is not None:
        raise AuthorizedUserServiceError("Cet utilisateur est déjà supprimé.")

    return soft_delete_authorized_user(db, authorized_user)