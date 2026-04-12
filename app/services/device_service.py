from sqlalchemy.orm import Session

from app.core.security import generate_device_token, hash_device_token
from app.crud.device import (
    create_device,
    device_code_exists,
    get_device_by_id,
    update_device,
    update_device_token_hash,
)
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate


class DeviceServiceError(Exception):
    pass


def create_device_service(
    db: Session,
    payload: DeviceCreate,
) -> tuple[Device, str]:
    if device_code_exists(db, payload.device_code):
        raise DeviceServiceError("Ce code appareil existe déjà.")

    plain_token = payload.api_token or generate_device_token()
    token_hash = hash_device_token(plain_token)

    device = create_device(
        db,
        device_name=payload.device_name,
        device_code=payload.device_code,
        api_token_hash=token_hash,
        location=payload.location,
        is_active=payload.is_active,
    )

    return device, plain_token


def update_device_service(
    db: Session,
    device_id: int,
    payload: DeviceUpdate,
) -> Device:
    device = get_device_by_id(db, device_id)

    if not device:
        raise DeviceServiceError("Appareil introuvable.")

    if device_code_exists(db, payload.device_code, exclude_device_id=device.id):
        raise DeviceServiceError("Ce code appareil existe déjà.")

    return update_device(
        db,
        device,
        device_name=payload.device_name,
        device_code=payload.device_code,
        location=payload.location,
        is_active=payload.is_active,
    )


def regenerate_device_token_service(
    db: Session,
    device_id: int,
) -> tuple[Device, str]:
    device = get_device_by_id(db, device_id)

    if not device:
        raise DeviceServiceError("Appareil introuvable.")

    old_hash = device.api_token_hash

    plain_token = generate_device_token()
    token_hash = hash_device_token(plain_token)

    updated_device = update_device_token_hash(db, device, token_hash)

    if not updated_device:
        raise DeviceServiceError("Impossible de recharger l'appareil après mise à jour.")

    if updated_device.api_token_hash == old_hash:
        raise DeviceServiceError("Le hash du token n'a pas changé en base.")

    return updated_device, plain_token