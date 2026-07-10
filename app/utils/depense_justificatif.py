"""Upload et nommage des justificatifs de dépenses (PDF, PNG, JPEG)."""

from __future__ import annotations

import os
import re
import uuid

from flask import current_app
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

ALLOWED_JUSTIFICATIF_EXTENSIONS = frozenset({"pdf", "png", "jpg", "jpeg"})


def _slug_part(value: str, fallback: str = "depense") -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:60] or fallback


def allowed_justificatif(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_JUSTIFICATIF_EXTENSIONS


def depenses_upload_dir() -> str:
    root = current_app.config.get("UPLOAD_FOLDER") or ""
    path = os.path.join(root, "depenses")
    os.makedirs(path, exist_ok=True)
    return path


def upload_depense_justificatif(file, categorie_nom: str, reference: str) -> str | None:
    """
    Enregistre le justificatif sous uploads/depenses/.
    Nom : {categorie}_{reference}.{ext} (ex. transport_dep-vte-2025-0001.pdf).
    Retourne le chemin relatif stocké en base (depenses/…) ou None si aucun fichier.
    """
    if not file or not file.filename:
        return None

    original = secure_filename(file.filename)
    if not allowed_justificatif(original):
        raise BadRequest("Format non autorisé. Utilisez PDF, PNG ou JPEG.")

    ext = original.rsplit(".", 1)[1].lower()
    cat_slug = _slug_part(categorie_nom, "depense")
    ref_slug = _slug_part(reference, uuid.uuid4().hex[:8])
    base_name = f"{cat_slug}_{ref_slug}.{ext}"

    upload_dir = depenses_upload_dir()
    filename = base_name
    counter = 2
    while os.path.exists(os.path.join(upload_dir, filename)):
        filename = f"{cat_slug}_{ref_slug}-{counter}.{ext}"
        counter += 1

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    return f"depenses/{filename}"


def justificatif_abs_path(stored: str | None) -> str | None:
    if not stored:
        return None
    root = current_app.config.get("UPLOAD_FOLDER") or ""
    safe = stored.replace("\\", "/").lstrip("/")
    if safe.startswith("depenses/"):
        return os.path.join(root, safe)
    return os.path.join(root, safe)


def remove_justificatif_file(stored: str | None) -> None:
    path = justificatif_abs_path(stored)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass

