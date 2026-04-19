from datetime import datetime

from fastapi import APIRouter, File, Depends, Form, Query, Request, UploadFile
from app.utils.file_uploads import save_authorized_user_photo, delete_uploaded_file

from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session
import io
import json
import textwrap
from reportlab.lib import colors
from pathlib import Path

import qrcode
from fastapi import  HTTPException
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image
import os

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_admin, require_agent_or_admin
from app.crud.authorized_user import (
    get_authorized_user_by_id,
    get_authorized_users_paginated,
)
from app.models.staff_user import StaffUser
from app.schemas.authorized_user import AuthorizedUserCreate, AuthorizedUserUpdate
from app.services.authorized_user_service import (
    AuthorizedUserServiceError,
    create_authorized_user_service,
    soft_delete_authorized_user_service,
    update_authorized_user_service,
)

from app.crud.device import get_devices
from app.crud.authorized_user_device import (
    get_device_ids_for_authorized_user,
    get_devices_for_authorized_user,
    replace_authorized_user_devices,
)


router = APIRouter()
templates = Jinja2Templates(directory=settings.template_path)

DEFAULT_PER_PAGE = 10


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value)


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None

def resolve_photo_path(user_path: str | None) -> str | None:
    if not user_path:
        return None

    normalized = user_path.lstrip("/\\")
    candidates = [
        os.path.abspath(os.path.join("static", normalized)),
        os.path.abspath(normalized),
    ]

    static_dir = getattr(settings, "static_path", None)
    if static_dir:
        candidates.append(os.path.abspath(os.path.join(static_dir, normalized)))

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def draw_text_lines(pdf, lines, x, y, line_height, font_name="Helvetica", font_size=8, color=colors.black):
    pdf.setFont(font_name, font_size)
    pdf.setFillColor(color)
    current_y = y
    for line in lines:
        pdf.drawString(x, current_y, line)
        current_y -= line_height
    return current_y


def wrap_text(value: str, width: int):
    if not value:
        return ["—"]
    return textwrap.wrap(str(value), width=width) or ["—"]

def get_static_root() -> Path:
    """
    Retourne le dossier réel app/static en se basant sur settings.template_path.
    Si templates = app/templates, alors static = app/static.
    """
    template_dir = Path(settings.template_path).resolve()
    app_dir = template_dir.parent
    static_dir = app_dir / "static"
    return static_dir


def resolve_authorized_user_photo(user_path: str | None) -> Path | None:
    """
    Convertit un path relatif comme:
    uploads/authorized_users/abc.jpg
    en chemin absolu:
    app/static/uploads/authorized_users/abc.jpg
    """
    if not user_path:
        return None

    relative_path = str(user_path).lstrip("/\\")
    full_path = get_static_root() / relative_path

    if full_path.exists() and full_path.is_file():
        return full_path

    return None


def build_qr_payload(user) -> dict:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "gender": user.gender,
        "phone": user.phone,
        "email": user.email,
        "reference_code": user.reference_code,
        "valid_from": user.valid_from.isoformat() if user.valid_from else None,
        "valid_until": user.valid_until.isoformat() if user.valid_until else None,
        "is_active": user.is_active,
    }


def make_qr_image_buffer(payload: dict) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(json.dumps(payload, ensure_ascii=False))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer



@router.get("/authorized-users", name="authorized_users.index", response_class=HTMLResponse)
def authorized_users_index(
    request: Request,
    page: int = Query(default=1, ge=1),
    search: str | None = Query(default=None),
    is_active: str | None = Query(default=None),
    validity: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    users, total = get_authorized_users_paginated(
        db,
        page=page,
        per_page=DEFAULT_PER_PAGE,
        search=search,
        is_active=is_active,
        validity=validity,
    )

    total_pages = max(1, (total + DEFAULT_PER_PAGE - 1) // DEFAULT_PER_PAGE)
    has_previous = page > 1
    has_next = page < total_pages
    page_numbers = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))

    filters = {
        "search": search or "",
        "is_active": is_active or "",
        "validity": validity or "",
    }

    return templates.TemplateResponse(
        request=request,
        name="authorized_users/index.html",
        context={
            "request": request,
            "users": users,
            "filters": filters,
            "current_page": page,
            "total": total,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next,
            "previous_page": page - 1,
            "next_page": page + 1,
            "page_numbers": page_numbers,
            "current_user": current_user,
        },
    )


@router.get("/authorized-users/create", name="authorized_users.create.index", response_class=HTMLResponse)
def authorized_users_create_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    now = datetime.now()
    request.state.now = now
    devices = get_devices(db)

    return templates.TemplateResponse(
        request=request,
        name="authorized_users/create.html",
        context={
            "request": request,
            "error": None,
            "devices": devices,
            "form_data": {},
            "current_user": current_user,
        },
    )


@router.post("/authorized-users/create", response_class=HTMLResponse, name="authorized_users.store")
def authorized_users_store(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    reference_code: str | None = Form(None),
    valid_from: str | None = Form(None),
    valid_until: str | None = Form(None),
    is_active: str | None = Form(None),
    notes: str | None = Form(None),
    photo: UploadFile | None = File(None),
    device_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    saved_path = None
    devices = get_devices(db)

    form_data = {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "phone": phone or "",
        "email": email or "",
        "reference_code": reference_code or "",
        "valid_from": valid_from or "",
        "valid_until": valid_until or "",
        "is_active": is_active == "on",
        "notes": notes or "",
    }

    try:
        saved_path = save_authorized_user_photo(photo)

        payload = AuthorizedUserCreate(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            phone=phone,
            email=email,
            reference_code=reference_code,
            valid_from=parse_optional_datetime(valid_from),
            valid_until=parse_optional_datetime(valid_until),
            is_active=is_active == "on",
            notes=notes,
            path=saved_path,
        )

        created_user = create_authorized_user_service(db, payload)

        replace_authorized_user_devices(
            db,
            authorized_user_id=created_user.id,
            device_ids=device_ids,
        )

        return RedirectResponse(url=request.url_for("authorized_users.index"), status_code=303)

    except ValueError as e:
        if saved_path:
            delete_uploaded_file(saved_path)

        return templates.TemplateResponse(
            request=request,
            name="authorized_users/create.html",
            context={
                "request": request,
                "error": str(e),
                "form_data": form_data,
                "devices": devices,
                "selected_device_ids": device_ids,
                "current_user": current_user,
                "show_sidebar": True,
                "show_navbar": True,
                "show_footer": True,
            },
            status_code=400,
        )

    except ValidationError as e:
        if saved_path:
            delete_uploaded_file(saved_path)

        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request,
            name="authorized_users/create.html",
            context={
                "request": request,
                "error": error_message,
                "form_data": form_data,
                "devices": devices,
                "selected_device_ids": device_ids,
                "current_user": current_user,
                "show_sidebar": True,
                "show_navbar": True,
                "show_footer": True,
            },
            status_code=400,
        )

    except AuthorizedUserServiceError as e:
        if saved_path:
            delete_uploaded_file(saved_path)

        return templates.TemplateResponse(
            request=request,
            name="authorized_users/create.html",
            context={
                "request": request,
                "error": str(e),
                "form_data": form_data,
                "devices": devices,
                "selected_device_ids": device_ids,
                "current_user": current_user,
                "show_sidebar": True,
                "show_navbar": True,
                "show_footer": True,
            },
            status_code=400,
        )


@router.get("/authorized-users/{authorized_user_id}/edit", name="authorized_users.edit", response_class=HTMLResponse)
def authorized_users_edit_page(
    authorized_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        return RedirectResponse(
            url=request.url_for("authorized_users.index"),
            status_code=303,
        )

    devices = get_devices(db)
    selected_device_ids = get_device_ids_for_authorized_user(db, authorized_user_id)

    form_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "gender": user.gender or "",
        "phone": user.phone or "",
        "email": user.email or "",
        "reference_code": user.reference_code or "",
        "valid_from": user.valid_from.strftime("%Y-%m-%dT%H:%M") if user.valid_from else "",
        "valid_until": user.valid_until.strftime("%Y-%m-%dT%H:%M") if user.valid_until else "",
        "is_active": user.is_active,
        "notes": user.notes or "",
    }

    return templates.TemplateResponse(
        request=request,
        name="authorized_users/edit.html",
        context={
            "request": request,
            "user": user,
            "error": None,
            "form_data": form_data,
            "devices": devices,
            "selected_device_ids": selected_device_ids,
            "current_user": current_user,
        },
    )



@router.post("/authorized-users/{authorized_user_id}/edit", response_class=HTMLResponse, name="authorized_users.update")
def authorized_users_update(
    authorized_user_id: int,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    reference_code: str | None = Form(None),
    valid_from: str | None = Form(None),
    valid_until: str | None = Form(None),
    is_active: str | None = Form(None),
    notes: str | None = Form(None),
    photo: UploadFile | None = File(None),
    device_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        return RedirectResponse(url=request.url_for("authorized_users.index"), status_code=303)

    devices = get_devices(db)
    old_path = user.path
    new_saved_path = None

    form_data = {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "phone": phone or "",
        "email": email or "",
        "reference_code": reference_code or "",
        "valid_from": valid_from or "",
        "valid_until": valid_until or "",
        "is_active": is_active == "on",
        "notes": notes or "",
    }

    try:
        if photo and photo.filename:
            new_saved_path = save_authorized_user_photo(photo)

        payload = AuthorizedUserUpdate(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            phone=phone,
            email=email,
            reference_code=reference_code,
            valid_from=parse_optional_datetime(valid_from),
            valid_until=parse_optional_datetime(valid_until),
            is_active=is_active == "on",
            notes=notes,
            path=new_saved_path if new_saved_path else old_path,
        )

        updated_user = update_authorized_user_service(db, authorized_user_id, payload)

        replace_authorized_user_devices(
            db,
            authorized_user_id=updated_user.id,
            device_ids=device_ids,
        )

        if new_saved_path and old_path:
            delete_uploaded_file(old_path)

        return RedirectResponse(
            url=request.url_for("authorized_users.show", authorized_user_id=authorized_user_id),
            status_code=303,
        )

    except ValueError as e:
        if new_saved_path:
            delete_uploaded_file(new_saved_path)

        return templates.TemplateResponse(
            request=request,
            name="authorized_users/edit.html",
            context={
                "request": request,
                "error": str(e),
                "form_data": form_data,
                "user": user,
                "devices": devices,
                "selected_device_ids": device_ids,
                "current_user": current_user,
            },
            status_code=400,
        )

    except ValidationError as e:
        if new_saved_path:
            delete_uploaded_file(new_saved_path)

        error_message = e.errors()[0]["msg"] if e.errors() else "Données invalides."
        return templates.TemplateResponse(
            request=request,
            name="authorized_users/edit.html",
            context={
                "request": request,
                "error": error_message,
                "form_data": form_data,
                "user": user,
                "devices": devices,
                "selected_device_ids": device_ids,
                "current_user": current_user,
            },
            status_code=400,
        )

    except AuthorizedUserServiceError as e:
        if new_saved_path:
            delete_uploaded_file(new_saved_path)

        return templates.TemplateResponse(
            request=request,
            name="authorized_users/edit.html",
            context={
                "request": request,
                "error": str(e),
                "form_data": form_data,
                "user": user,
                "devices": devices,
                "selected_device_ids": device_ids,
                "current_user": current_user,
            },
            status_code=400,
        )

@router.post("/authorized-users/{authorized_user_id}/delete",name="authorized_users.delete")
def authorized_users_delete(
    request: Request,
    authorized_user_id: int,
    db: Session = Depends(get_db),
):
    try:
        soft_delete_authorized_user_service(db, authorized_user_id)
    except AuthorizedUserServiceError:
        pass

    return RedirectResponse(
        url=request.url_for("authorized_users.show", authorized_user_id=authorized_user_id),
        status_code=303,
    )


@router.get("/authorized-users/{authorized_user_id}", name="authorized_users.show", response_class=HTMLResponse)
def authorized_users_show(
    authorized_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)
    
    allowed_devices = get_devices_for_authorized_user(db, authorized_user_id)

    if not user:
        return RedirectResponse(
            url=request.url_for("authorized_users.index"),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="authorized_users/show.html",
        context={
            "request": request,
            "user": user,
            "allowed_devices": allowed_devices,
            "current_user": current_user,
        },
    )


@router.get("/authorized-users/{authorized_user_id}/qr", name="authorized_users.qr")
async def authorized_user_qr(
    authorized_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    payload = build_qr_payload(user)
    buffer = make_qr_image_buffer(payload)

    return StreamingResponse(buffer, media_type="image/png")


@router.get("/authorized-users/{authorized_user_id}/download-card", name="authorized_users.download_card")
async def download_card(
    authorized_user_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_agent_or_admin),
):
    user = get_authorized_user_by_id(db, authorized_user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    from pathlib import Path
    from reportlab.lib import colors

    def get_static_root() -> Path:
        template_dir = Path(settings.template_path).resolve()
        app_dir = template_dir.parent
        return app_dir / "static"

    def resolve_authorized_user_photo(user_path: str | None) -> Path | None:
        if not user_path:
            return None
        full_path = get_static_root() / str(user_path).lstrip("/\\")
        if full_path.exists() and full_path.is_file():
            return full_path
        return None

    def build_qr_payload() -> dict:
        return {
            "id": user.id,
            "reference_code": user.reference_code,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "email": user.email,
            "valid_from": user.valid_from.isoformat() if user.valid_from else None,
            "valid_until": user.valid_until.isoformat() if user.valid_until else None,
            "is_active": user.is_active,
        }

    def make_qr_buffer() -> io.BytesIO:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(json.dumps(build_qr_payload(), ensure_ascii=False))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        return qr_buffer

    # CR80 uniquement
    page_width = 85.60 * mm
    page_height = 53.98 * mm
    filename = f"card_{user.id}_cr80.pdf"

    card_w = page_width
    card_h = page_height
    card_x = 0
    card_y = 0

    radius = 4 * mm
    header_h = 10 * mm
    photo_w = 18 * mm
    photo_h = 18 * mm
    qr_size = 13 * mm
    pad = 3.5 * mm

    title_size = 8.8
    name_size = 10.5
    text_size = 6.4
    small_size = 5.8

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    # Fond général
    pdf.setFillColor(colors.HexColor("#f3f4f6"))
    pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # Carte
    pdf.setFillColor(colors.white)
    pdf.roundRect(card_x, card_y, card_w, card_h, radius, fill=1, stroke=0)

    # Header bleu
    pdf.setFillColor(colors.HexColor("#1664ea"))
    pdf.roundRect(card_x, card_y + card_h - header_h, card_w, header_h, radius, fill=1, stroke=0)
    pdf.rect(card_x, card_y + card_h - header_h, card_w, header_h / 2, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", title_size)
    # pdf.drawString(
    #     card_x + pad,
    #     card_y + card_h - header_h + (header_h * 0.38),
    #     "UTILISATEUR AUTORISÉ"
    # )

    pdf.drawCentredString(
        card_x + (card_w / 2),
        card_y + card_h - header_h + (header_h * 0.38),
        "BADGE D'ACCES AU SYSTEME"
    )

    # Photo
    photo_x = card_x + pad
    photo_y = card_y + card_h - header_h - pad - photo_h

    pdf.setFillColor(colors.HexColor("#eef2f7"))
    pdf.roundRect(photo_x, photo_y, photo_w, photo_h, 2 * mm, fill=1, stroke=0)

    photo_path = resolve_authorized_user_photo(user.path)
    if photo_path:
        try:
            with open(photo_path, "rb") as f:
                img_buffer = io.BytesIO(f.read())
                img_buffer.seek(0)

            pdf.drawImage(
                ImageReader(img_buffer),
                photo_x,
                photo_y,
                width=photo_w,
                height=photo_h,
                mask="auto",
                preserveAspectRatio=False,
            )
        except Exception:
            pdf.setStrokeColor(colors.HexColor("#d1d5db"))
            pdf.roundRect(photo_x, photo_y, photo_w, photo_h, 2 * mm, fill=0, stroke=1)
    else:
        pdf.setStrokeColor(colors.HexColor("#d1d5db"))
        pdf.roundRect(photo_x, photo_y, photo_w, photo_h, 2 * mm, fill=0, stroke=1)

    # Bloc infos
    info_x = photo_x + photo_w + 4 * mm
    info_top_y = card_y + card_h - header_h - pad

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica-Bold", name_size)
    pdf.drawString(info_x, info_top_y - 1.5 * mm, f"{user.first_name} {user.last_name}"[:28])

    pdf.setFont("Helvetica", text_size)
    pdf.setFillColor(colors.HexColor("#6b7280"))
    pdf.drawString(info_x, info_top_y - 7.5 * mm, user.gender or "Utilisateur")

    label_gap = 5.5 * mm
    start_y = info_top_y - 13 * mm

    def draw_label_value(y, label, value):
        pdf.setFont("Helvetica-Bold", text_size)
        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.drawString(info_x, y, f"{label} :")

        label_width = pdf.stringWidth(f"{label} :", "Helvetica-Bold", text_size)

        pdf.setFont("Helvetica", text_size)
        pdf.setFillColor(colors.HexColor("#1f2937"))
        pdf.drawString(info_x + label_width + 1.5 * mm, y, value)

    draw_label_value(start_y, "Tél", user.phone or "—")
    draw_label_value(start_y - label_gap, "Email", (user.email or "—")[:28])
    draw_label_value(start_y - (label_gap * 2), "Statut", "Actif" if user.is_active else "Inactif")

    # Ligne de séparation
    divider_y = card_y + 18 * mm
    # pdf.setStrokeColor(colors.HexColor("#d1d5db"))
    # pdf.setLineWidth(0.4)
    # pdf.line(card_x + pad, divider_y, card_x + card_w - pad, divider_y)

    # Bloc bas gauche
    bottom_left_x = card_x + pad
    bottom_top_y = divider_y - 4.5 * mm

    valid_from_str = user.valid_from.strftime("%d/%m/%Y %H:%M") if user.valid_from else "—"
    valid_until_str = user.valid_until.strftime("%d/%m/%Y %H:%M") if user.valid_until else "—"

    pdf.setFillColor(colors.HexColor("#2563eb"))
    pdf.setFont("Helvetica-Bold", text_size + 0.2)
    pdf.drawString(bottom_left_x, bottom_top_y, f"Matricule : {user.reference_code or '—'}")

    pdf.setFillColor(colors.HexColor("#111827"))

    pdf.setFont("Helvetica-Bold", small_size)
    pdf.drawString(bottom_left_x, bottom_top_y - 6 * mm, "Valide du :")
    pdf.setFont("Helvetica", small_size)
    pdf.drawString(bottom_left_x + 18 * mm, bottom_top_y - 6 * mm, valid_from_str)

    pdf.setFont("Helvetica-Bold", small_size)
    pdf.drawString(bottom_left_x, bottom_top_y - 11.5 * mm, "Au :")
    pdf.setFont("Helvetica", small_size)
    pdf.drawString(bottom_left_x + 18 * mm, bottom_top_y - 11.5 * mm, valid_until_str)

    # QR code en bas à droite
    qr_buffer = make_qr_buffer()
    qr_x = card_x + card_w - pad - qr_size
    qr_y = card_y + pad

    pdf.setFillColor(colors.HexColor("#f8fafc"))
    pdf.roundRect(qr_x - 1.5 * mm, qr_y - 1.5 * mm, qr_size + 3 * mm, qr_size + 3 * mm, 2 * mm, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#d1d5db"))
    pdf.roundRect(qr_x - 1.5 * mm, qr_y - 1.5 * mm, qr_size + 3 * mm, qr_size + 3 * mm, 2 * mm, fill=0, stroke=1)
    pdf.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size, mask="auto")

    # Bordure carte
    pdf.setStrokeColor(colors.HexColor("#e5e7eb"))
    pdf.roundRect(card_x, card_y, card_w, card_h, radius, fill=0, stroke=1)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )