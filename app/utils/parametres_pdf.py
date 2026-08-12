"""Contexte commun pour les templates PDF (logo en data-URI, en-têtes société)."""

from __future__ import annotations

import base64
import os

from flask import current_app, url_for

from ..models.parametres_documents import ParametresDocuments


def get_parametres_documents() -> ParametresDocuments:
    return ParametresDocuments.get_singleton()


def logo_data_uri() -> str | None:
    """Image du logo en data URI pour xhtml2pdf / WeasyPrint."""
    p = get_parametres_documents()
    fn = (p.logo_filename or "").strip()
    if not fn:
        return None
    upload = current_app.config.get("UPLOAD_FOLDER") or ""
    path = os.path.join(upload, "parametres", fn)
    if not os.path.isfile(path):
        return None
    ext = fn.rsplit(".", 1)[-1].lower()
    mime = "image/png"
    if ext in ("jpg", "jpeg"):
        mime = "image/jpeg"
    elif ext == "gif":
        mime = "image/gif"
    try:
        with open(path, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime};base64,{b64}"


def get_logo_filepath() -> str | None:
    """Chemin fichier logo pour ReportLab (hors data-URI)."""
    p = get_parametres_documents()
    fn = (p.logo_filename or "").strip()
    if not fn:
        return None
    upload = current_app.config.get("UPLOAD_FOLDER") or ""
    path = os.path.join(upload, "parametres", fn)
    return path if os.path.isfile(path) else None


def get_cachet_filepath() -> str | None:
    """Chemin fichier cachet pour ReportLab."""
    p = get_parametres_documents()
    fn = (getattr(p, "cachet_filename", None) or "").strip()
    if not fn:
        return None
    upload = current_app.config.get("UPLOAD_FOLDER") or ""
    path = os.path.join(upload, "parametres", fn)
    return path if os.path.isfile(path) else None


def has_cachet() -> bool:
    return get_cachet_filepath() is not None


def cachet_url() -> str | None:
    p = get_parametres_documents()
    fn = (getattr(p, "cachet_filename", None) or "").strip()
    if not fn or not get_cachet_filepath():
        return None
    return url_for("parametres.logo_file", filename=fn)


DEFAULT_COMPANY_SLOGAN = "Serving those who care for others"
DEFAULT_SITE_WEB = "https://avalonpharmasenegal.com"
DEFAULT_COMPANY_EMAIL = "avalonpharmasenegal@gmail.com"
DEFAULT_COMPANY_TELEPHONE = "77 444 14 01 - 77 764 87 28"
DEFAULT_COMPANY_RC = "SN STL 2008B1250"
DEFAULT_COMPANY_NINEA = "30835902K2"
DEFAULT_COMPANY_COMPTE = "CBAO : SN012 08274 036182246001 48"

DEFAULT_COMPANY_COORDS = {
    "telephone": DEFAULT_COMPANY_TELEPHONE,
    "email": DEFAULT_COMPANY_EMAIL,
    "rc": DEFAULT_COMPANY_RC,
    "ninea": DEFAULT_COMPANY_NINEA,
    "compte_bancaire": DEFAULT_COMPANY_COMPTE,
}


def resolve_company_email(row: ParametresDocuments | None) -> str:
    email = (getattr(row, "email", None) or "").strip() if row else ""
    return email or DEFAULT_COMPANY_EMAIL


def ensure_doc_params_email(row: ParametresDocuments | None) -> ParametresDocuments | None:
    """Garantit les coordonnées société sur facture / BL / PDF."""
    if row is None:
        return None
    changed = False
    for key, value in DEFAULT_COMPANY_COORDS.items():
        if not (getattr(row, key, None) or "").strip():
            setattr(row, key, value)
            changed = True
    if changed:
        try:
            from ..extensions import db

            db.session.commit()
        except Exception:
            pass
    return row


def resolve_company_slogan(row: ParametresDocuments | None) -> str:
    slogan = (getattr(row, "slogan", None) or "").strip() if row else ""
    return slogan or DEFAULT_COMPANY_SLOGAN


def normalize_site_web_url(url: str | None) -> str:
    """URL absolue pour le QR code (défaut : avalonpharmasenegal.com)."""
    u = (url or "").strip() or DEFAULT_SITE_WEB
    if not u.startswith(("http://", "https://")):
        u = f"https://{u.lstrip('/')}"
    return u


def site_web_display(url: str) -> str:
    """Libellé court sous le QR (sans protocole)."""
    u = normalize_site_web_url(url)
    return u.replace("https://", "").replace("http://", "").rstrip("/")


def pdf_company_context():
    """Dict à passer en plus aux render_template des PDF."""
    row = ensure_doc_params_email(get_parametres_documents())
    site_web_url = normalize_site_web_url(getattr(row, "site_web", None))
    return {
        "doc_params": row,
        "logo_data_uri": logo_data_uri(),
        "company_name": row.raison_sociale or "Société",
        "company_email": resolve_company_email(row),
        "site_web_url": site_web_url,
        "site_web_label": site_web_display(site_web_url),
        "company_slogan": resolve_company_slogan(row),
        "has_cachet": has_cachet(),
        "cachet_url": cachet_url(),
    }


def merge_browser_print_logo(ctx: dict) -> dict:
    """
    Ajoute logo_url (fichier servi par parametres.logo_file) au contexte
    déjà enrichi par pdf_company_context(),     pour les gabarits impression navigateur
    (partials _erp_print_header / _erp_print_footer, layouts/print_document.html).
    """
    row = ctx.get("doc_params")
    if row is None:
        ctx["logo_url"] = None
        ctx["cachet_url"] = None
        ctx["has_cachet"] = False
        return ctx
    logo_url = None
    fn = (getattr(row, "logo_filename", None) or "").strip()
    if fn and get_logo_filepath():
        logo_url = url_for("parametres.logo_file", filename=fn)
    ctx["logo_url"] = logo_url
    ctx["site_web_url"] = normalize_site_web_url(getattr(row, "site_web", None) if row else None)
    ctx["site_web_label"] = site_web_display(ctx["site_web_url"])
    ctx["company_slogan"] = resolve_company_slogan(row) if row else DEFAULT_COMPANY_SLOGAN
    ctx["has_cachet"] = has_cachet()
    ctx["cachet_url"] = cachet_url()
    return ctx
