import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


APP_TIMEZONE = os.getenv("TZ", "UTC")
LOCAL_TZ = ZoneInfo(APP_TIMEZONE)


def utc_now() -> datetime:
    """
    Date actuelle en UTC avec timezone.
    Recommandé pour enregistrer en base de données.
    """
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    """
    Date actuelle dans le fuseau horaire configuré dans TZ.
    Exemple : Indian/Antananarivo.
    """
    return datetime.now(LOCAL_TZ)


def to_local_time(dt: datetime | None) -> datetime | None:
    """
    Convertit une date UTC vers le fuseau horaire local.
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(LOCAL_TZ)


def to_local_isoformat(dt: datetime | None) -> str | None:
    """
    Convertit une date en ISO format avec timezone locale.
    """
    print('heure dt: ',dt)
    local_dt = to_local_time(dt)
    print('local_dt: ',local_dt)

    if local_dt is None:
        return None

    return local_dt.isoformat()


def to_local_display(dt: datetime | None) -> str:
    """
    Format lisible pour affichage HTML.
    """
    local_dt = to_local_time(dt)

    if local_dt is None:
        return ""

    return local_dt.strftime("%d/%m/%Y %H:%M:%S")