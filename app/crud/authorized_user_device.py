from sqlalchemy.orm import Session

from app.models.authorized_user_device import AuthorizedUserDevice
from app.models.device import Device


def get_device_ids_for_authorized_user(
    db: Session,
    authorized_user_id: int,
) -> list[int]:
    rows = (
        db.query(AuthorizedUserDevice.device_id)
        .filter(AuthorizedUserDevice.authorized_user_id == authorized_user_id)
        .all()
    )
    return [row[0] for row in rows]


def get_devices_for_authorized_user(
    db: Session,
    authorized_user_id: int,
) -> list[Device]:
    return (
        db.query(Device)
        .join(AuthorizedUserDevice, AuthorizedUserDevice.device_id == Device.id)
        .filter(AuthorizedUserDevice.authorized_user_id == authorized_user_id)
        .order_by(Device.device_name.asc(), Device.id.asc())
        .all()
    )


def user_has_access_to_device(
    db: Session,
    *,
    authorized_user_id: int,
    device_id: int,
) -> bool:
    
    print("authorized_user_id : ",authorized_user_id, "device_id : ",device_id)
    
    query = (
        db.query(AuthorizedUserDevice)
        .filter(
            AuthorizedUserDevice.authorized_user_id == authorized_user_id,
            AuthorizedUserDevice.device_id == device_id,
        )
    )
    return db.query(query.exists()).scalar()


def replace_authorized_user_devices(
    db: Session,
    *,
    authorized_user_id: int,
    device_ids: list[int],
) -> None:
    db.query(AuthorizedUserDevice).filter(
        AuthorizedUserDevice.authorized_user_id == authorized_user_id
    ).delete(synchronize_session=False)

    unique_device_ids = sorted(set(device_ids))

    for device_id in unique_device_ids:
        db.add(
            AuthorizedUserDevice(
                authorized_user_id=authorized_user_id,
                device_id=device_id,
            )
        )

    db.commit()