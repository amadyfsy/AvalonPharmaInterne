"""Upload et nommage des justificatifs de paiements clients (PDF, PNG, JPEG)."""

from __future__ import annotations

import os
import re
import uuid

from flask import current_app
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

ALLOWED_PAIEMENT_JUSTIFICATIF_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg"})


def _slug_part(value: str, fallback: str = "paiement") -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:60] or fallback


def allowed_paiement_justificatif(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_PAIEMENT_JUSTIFICATIF_EXTENSIONS


def paiements_upload_dir() -> str:
    root = current_app.config.get("UPLOAD_FOLDER") or ""
    path = os.path.join(root, "paiements")
    os.makedirs(path, exist_ok=True)
    return path


def upload_paiement_justificatif(file, reference: str) -> str | None:
    """
    Enregistre le justificatif sous uploads/paiements/.
    Nom : paiement_{reference}_{suffix}.{ext} (ex. paiement_enc-2026-0001_a1b2c3.pdf).
    Retourne le chemin relatif stocké en base (paiements/…) ou None si aucun fichier.
    """
    if not file or not getattr(file, "filename", None):
        return None

    original = secure_filename(file.filename)
    if not allowed_paiement_justificatif(original):
        raise BadRequest("Format de justificatif non autorisé. Utilisez PDF, PNG ou JPEG.")

    ext = original.rsplit(".", 1)[1].lower()
    ref_slug = _slug_part(reference, uuid.uuid4().hex[:8])
    unique_suffix = uuid.uuid4().hex[:6]
    base_name = f"paiement_{ref_slug}_{unique_suffix}.{ext}"

    upload_dir = paiements_upload_dir()
    filepath = os.path.join(upload_dir, base_name)
    file.save(filepath)
    return f"paiements/{base_name}"


def paiement_justificatif_abs_path(stored: str | None) -> str | None:
    if not stored:
        return None
    root = current_app.config.get("UPLOAD_FOLDER") or ""
    safe = stored.replace("\\", "/").lstrip("/")
    return os.path.join(root, safe)


def remove_paiement_justificatif_file(stored: str | None) -> None:
    path = paiement_justificatif_abs_path(stored)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
