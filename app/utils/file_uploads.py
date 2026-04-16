from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

AUTHORIZED_USERS_UPLOAD_DIR = Path("app/static/uploads/authorized_users")
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_authorized_user_photo(upload_file: UploadFile | None) -> str | None:
    if not upload_file or not upload_file.filename:
        return None

    content_type = upload_file.content_type
    extension = ALLOWED_IMAGE_CONTENT_TYPES.get(content_type)

    if not extension:
        raise ValueError("Format de photo non autorisé. Utilise JPG, PNG ou WEBP.")

    AUTHORIZED_USERS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    absolute_path = AUTHORIZED_USERS_UPLOAD_DIR / filename

    with absolute_path.open("wb") as buffer:
        buffer.write(upload_file.file.read())

    return f"uploads/authorized_users/{filename}"


def delete_uploaded_file(relative_path: str | None) -> None:
    if not relative_path:
        return

    absolute_path = Path("app/static") / Path(relative_path).relative_to("uploads")
    if absolute_path.exists() and absolute_path.is_file():
        absolute_path.unlink()