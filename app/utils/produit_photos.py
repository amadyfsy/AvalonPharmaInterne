"""Upload et gestion des photos produit (principale + galerie)."""
from __future__ import annotations

import os
import re
import uuid

from flask import current_app
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

ALLOWED_PHOTO_EXTENSIONS = frozenset({'jpg', 'jpeg', 'png', 'webp'})
MAX_GALERIE_PHOTOS = 12


def _slug_part(value: str, fallback: str = 'produit') -> str:
    s = (value or '').strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:48] or fallback


def allowed_produit_photo(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_PHOTO_EXTENSIONS


def produits_upload_dir() -> str:
    root = current_app.config.get('UPLOAD_FOLDER') or ''
    path = os.path.join(root, 'produits')
    os.makedirs(path, exist_ok=True)
    return path


def upload_produit_photo(file, reference_produit: str, suffix: str = 'main') -> str:
    """Enregistre une image sous uploads/produits/. Retourne le chemin relatif produits/…"""
    if not file or not getattr(file, 'filename', None):
        raise BadRequest('Fichier image requis (JPEG, PNG ou WebP).')

    original = secure_filename(file.filename)
    if not allowed_produit_photo(original):
        raise BadRequest('Format non autorisé. Utilisez JPEG, PNG ou WebP.')

    ext = original.rsplit('.', 1)[1].lower()
    if ext == 'jpeg':
        ext = 'jpg'
    ref_slug = _slug_part(reference_produit, 'produit')
    suf_slug = _slug_part(suffix, 'img')
    base_name = f'{ref_slug}_{suf_slug}_{uuid.uuid4().hex[:8]}.{ext}'

    upload_dir = produits_upload_dir()
    filename = base_name
    counter = 2
    while os.path.exists(os.path.join(upload_dir, filename)):
        filename = f'{ref_slug}_{suf_slug}_{uuid.uuid4().hex[:8]}-{counter}.{ext}'
        counter += 1

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    return f'produits/{filename}'


def photo_abs_path(stored: str | None) -> str | None:
    if not stored:
        return None
    root = current_app.config.get('UPLOAD_FOLDER') or ''
    safe = stored.replace('\\', '/').lstrip('/')
    if safe.startswith('produits/'):
        return os.path.join(root, safe)
    return os.path.join(root, 'produits', os.path.basename(safe))


def remove_produit_photo_file(stored: str | None) -> None:
    path = photo_abs_path(stored)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
