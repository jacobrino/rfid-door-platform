from sqlalchemy.orm import Session

from app.crud.rfid_card import (
    create_rfid_card,
    get_rfid_card_by_id,
    uid_exists,
    update_rfid_card,
)
from app.models.rfid_card import RfidCard
from app.schemas.rfid_card import RfidCardCreate, RfidCardUpdate


class RfidCardServiceError(Exception):
    pass


def create_rfid_card_service(
    db: Session,
    payload: RfidCardCreate,
) -> RfidCard:
    if uid_exists(db, payload.uid):
        raise RfidCardServiceError("Cet UID existe déjà.")

    return create_rfid_card(db, payload)


def update_rfid_card_service(
    db: Session,
    rfid_card_id: int,
    payload: RfidCardUpdate,
) -> RfidCard:
    rfid_card = get_rfid_card_by_id(db, rfid_card_id)

    if not rfid_card:
        raise RfidCardServiceError("Carte RFID introuvable.")

    if uid_exists(db, payload.uid, exclude_card_id=rfid_card.id):
        raise RfidCardServiceError("Cet UID existe déjà.")

    return update_rfid_card(db, rfid_card, payload)