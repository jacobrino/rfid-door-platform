from fastapi import APIRouter, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.esp32_access import (
    Esp32AccessCheckRequest,
    Esp32AccessCheckResponse,
    DeviceEchoPayload
)
from app.services.esp32_access_service import (
    Esp32AccessServiceError,
    check_esp32_access_service,
)

from datetime import datetime
from sqlalchemy.orm import Session

from app.core.security import verify_device_token
from app.crud.device import get_device_by_code, update_device_last_seen

router = APIRouter(prefix="/api/esp32/access", tags=["ESP32 Access"])


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header manquant.",
        )

    parts = authorization.strip().split(" ", 1)

    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header invalide.",
        )

    return parts[1].strip()


@router.post("/check", response_model=Esp32AccessCheckResponse)
def check_access(
    payload: Esp32AccessCheckRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    bearer_token = extract_bearer_token(authorization)

    try:
        result = check_esp32_access_service(
            db,
            payload=payload,
            bearer_token=bearer_token,
        )
        return result

    except Esp32AccessServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    

@router.post("/echo")
def esp32_echo(
    payload: DeviceEchoPayload,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    bearer_token = extract_bearer_token(authorization)

    device = get_device_by_code(db, payload.device_code)
    
    print('authorization : ',authorization)

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable dans database.")

    if not device.is_active:
        raise HTTPException(status_code=403, detail="Appareil inactif dans database.")

    if not bearer_token or not verify_device_token(bearer_token, device.api_token_hash):
        raise HTTPException(status_code=401, detail="Token appareil invalide.")

    update_device_last_seen(db, device)

    return {
        "success": True,
        "message": "Echo OK",
        "device_code": device.device_code,
        "server_time": datetime.utcnow().isoformat(),
    }


"""
jacob@jacob-IdeaPad-3-15IAU7:/var/www/html/ENI/rfid-door-platform$ 

curl -X POST "http://127.0.0.1:8000/api/esp32/access/check" -H "Content-Type: application/json" -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY" -d '{"device_code": "ssqa","uid": "id_puce_rfid"}'

{"decision":"denied","door_opened":false,"direction":"unknown","reason":"card_not_found","user_id":null,"assignment_id":null,"card_id":null,"scanned_at":"2026-04-11T21:38:51.010528"}

jacob@jacob-IdeaPad-3-15IAU7:/var/www/html/ENI/rfid-door-platform$ curl -X POST "http://127.0.0.1:8000/api/esp32/access/check"   -H "Content-Type: application/json"   -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY"   -d '{
    "device_code": "ssqa",
    "uid": "qdsqdqsdqsdqsdsqdss"
  }'
{"decision":"granted","door_opened":true,"direction":"entry","reason":"access_granted","user_id":2,"assignment_id":1,"card_id":1,"scanned_at":"2026-04-11T21:40:31.642180"}jacob@jacob-IdeaPad-3-15IAU7:/var/www/html/ENI/rfid-door-platform$ curl -X POST "http://127.0.0.1:8000/api/esp32/access/check"   -H "Content-Type: application/json"   -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY"   -d '{
    "device_code": "ssqa",
    "uid": "qdsqdqsdqsdqsdsqdss"
  }'
{"decision":"granted","door_opened":true,"direction":"exit","reason":"access_granted","user_id":2,"assignment_id":1,"card_id":1,"scanned_at":"2026-04-11T21:41:14.965324"}
"""

"""
Echo commande
curl -X POST "http://127.0.0.1:8000/api/esp32/access/echo" -H "Content-Type: application/json" -H "Authorization: Bearer HsySaOIkqkXhYj4VBl6KLjtHcZM_SF0NWWf8kqRPcdY" -d '{"device_code": "ssqa"}'


{"success":true,"message":"Echo OK","device_code":"ESP32_DEVICE_020","server_time":"2026-04-19T12:30:43.121861"}
"""