"""
Génération PDF à partir de HTML (factures, BL, proformas).

Ordre d’essai :
1. **WeasyPrint** — si installé (optionnel, voir requirements-optional-weasyprint.txt).
2. **xhtml2pdf** — pur pip, dépendances listées dans requirements.txt.
3. **fpdf2** — texte brut extrait du HTML (PDF lisible, mise en page simple).
"""

from __future__ import annotations

import io
import logging
import re
from html import unescape

logger = logging.getLogger(__name__)

WEASYPRINT_AVAILABLE = False
XHTML2PDF_AVAILABLE = False
FPDF2_AVAILABLE = False
_IMPORT_ERRORS: list[str] = []

try:
    from weasyprint import CSS, HTML

    WEASYPRINT_AVAILABLE = True
except Exception as e:
    _IMPORT_ERRORS.append(f"WeasyPrint: {e}")

try:
    from xhtml2pdf import pisa

    XHTML2PDF_AVAILABLE = True
except Exception as e:
    _IMPORT_ERRORS.append(f"xhtml2pdf: {e}")

try:
    from fpdf import FPDF

    FPDF2_AVAILABLE = True
except Exception as e:
    _IMPORT_ERRORS.append(f"fpdf2: {e}")

if _IMPORT_ERRORS:
    logger.warning("Moteurs PDF — %s", " | ".join(_IMPORT_ERRORS))


def generate_pdf(html_string: str) -> io.BytesIO:
    """
    Produit un PDF à partir d'une chaîne HTML.
    Retourne un BytesIO prêt pour Flask send_file.
    """
    if WEASYPRINT_AVAILABLE:
        try:
            return _generate_with_weasyprint(html_string)
        except Exception as e:
            logger.warning("WeasyPrint a échoué, fallback : %s", e)
    if XHTML2PDF_AVAILABLE:
        try:
            return _generate_with_xhtml2pdf(html_string)
        except Exception as e:
            logger.warning("xhtml2pdf a échoué, fallback fpdf2 : %s", e)
    if FPDF2_AVAILABLE:
        return _generate_with_fpdf2_plain(html_string)

    hint = (
        "Installez les dépendances PDF : "
        "`pip install -r requirements.txt` depuis le dossier du projet "
        "(xhtml2pdf, reportlab, fpdf2, …). "
        "Détail : "
        + (" ; ".join(_IMPORT_ERRORS) if _IMPORT_ERRORS else "aucun import réussi")
    )
    raise RuntimeError(hint)


def _generate_with_weasyprint(html_string: str) -> io.BytesIO:
    base_css = CSS(
        string="""
        @page { size: A4; margin: 1cm; }
        body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 13px; color: #333; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .text-right { text-align: right; }
        .text-center { text-align: center; }
        .fw-bold { font-weight: bold; }
        .header { margin-bottom: 30px; border-bottom: 2px solid #0066CC; padding-bottom: 10px; }
        .footer { position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 10px; color: #777; border-top: 1px solid #ddd; padding-top: 10px; }
    """
    )
    pdf_bytes = HTML(string=html_string).write_pdf(stylesheets=[base_css])
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return buf


def _generate_with_xhtml2pdf(html_string: str) -> io.BytesIO:
    html_lower = html_string.lower().strip()
    if "<html" not in html_lower:
        html_string = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'/></head><body>"
            + html_string
            + "</body></html>"
        )

    out = io.BytesIO()
    status = pisa.CreatePDF(
        src=html_string,
        dest=out,
        encoding="utf-8",
    )
    if status.err:
        raise RuntimeError("xhtml2pdf : erreur interne (HTML trop complexe ?).")
    out.seek(0)
    return out


def _html_to_text_lines(html: str, max_lines: int = 500) -> list[str]:
    """Extrait du texte lisible pour le repli fpdf2."""
    s = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    s = re.sub(r"(?is)<style.*?>.*?</style>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(tr|div|p|h[1-6]|li|table|thead|tbody)>\s*", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    lines: list[str] = []
    for raw in s.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            lines.append(line[:500])
        if len(lines) >= max_lines:
            break
    if not lines:
        lines = ["(Document vide — erreur de conversion HTML)"]
    return lines


def _generate_with_fpdf2_plain(html_string: str) -> io.BytesIO:
    """PDF minimal : texte seul, toujours générable si fpdf2 est installé."""
    lines = _html_to_text_lines(html_string)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)
    for line in lines:
        safe = line.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 4.5, safe)
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        data = bytes(raw)
    else:
        data = str(raw).encode("latin-1", errors="replace")
    buf = io.BytesIO(data)
    buf.seek(0)
    return buf
