"""
PDF factures / proformas / BL au format « document papier » (ReportLab).
Facture : en-tête répété sur chaque page (logo gauche + infos société à droite), sans pied.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import date
from typing import Any, Callable
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .bl_helpers import bl_quantite_document
from .ventes_totaux import document_affiche_tva

logger = logging.getLogger(__name__)

_FONTS_OK = False


def _ensure_fonts() -> None:
    global _FONTS_OK
    if _FONTS_OK:
        return
    fonts_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    pdfmetrics.registerFont(TTFont("Vera", os.path.join(fonts_dir, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(fonts_dir, "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Italic", os.path.join(fonts_dir, "VeraIt.ttf")))
    _FONTS_OK = True


def _num_gt_zero(x: Any) -> bool:
    if x is None:
        return False
    try:
        return float(x) > 1e-9
    except (TypeError, ValueError):
        return False


def _pdf_amount_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    """Montant PDF sur une seule ligne (évite 21 041 / 700,57)."""
    safe = escape(str(text)).replace(" ", "&nbsp;")
    return Paragraph(f"<nobr>{safe}</nobr>", style)


def _story_coords(doc_params: Any, date_doc: date | None) -> list:
    """Conserve uniquement la génération de la ligne Date et Lieu."""
    _ensure_fonts()
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        name="DocCoords",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=10.5,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=3,
    )
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    story: list = []
    lieu = (getattr(doc_params, "lieu_signature", None) or "St Louis").strip()
    if date_doc:
        m = mois[date_doc.month - 1]
        story.append(
            Paragraph(escape(f"{lieu}, le {date_doc.day} {m.capitalize()} {date_doc.year}"), normal)
        )
    return story


def _header_flowable(logo_path: str | None, doc_params: Any, usable_width: float) -> list:
    """Logo élargi à gauche, et coordonnées de la structure à droite."""
    _ensure_fonts()
    col1_w = usable_width * 0.4
    col2_w = usable_width * 0.6
    
    left_items = []
    if logo_path and os.path.isfile(logo_path):
        try:
            img = Image(logo_path, kind="proportional")
            img.drawHeight = min(img.drawHeight, 28 * mm)  # diminue un peu
            img.drawWidth = min(img.drawWidth, 65 * mm)    
            left_items.append(img)
        except Exception as e:
            logger.warning("Logo PDF ignoré : %s", e)

    right_items = []
    if doc_params:
        styles = getSampleStyleSheet()
        title_right = ParagraphStyle(
            "tr",
            parent=styles["Normal"],
            fontName="Vera-Bold",
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#1A1A1A"),
            spaceAfter=3,
        )
        small_right = ParagraphStyle(
            "sr",
            parent=styles["Normal"],
            fontName="Vera",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#262626")
        )
        
        rs = (getattr(doc_params, "raison_sociale", None) or "").strip()
        if rs:
            right_items.append(Paragraph(escape(rs), title_right))

        ad = (getattr(doc_params, "adresse_ligne", None) or "").strip()
        if ad:
            right_items.append(Paragraph(escape(ad), small_right))

        parts_contact = []
        tel = getattr(doc_params, "telephone", None)
        email = getattr(doc_params, "email", None)
        if tel: parts_contact.append(f"Tel : {tel}")
        if email: parts_contact.append(f"Email : {email}")
        if parts_contact:
            right_items.append(Paragraph(escape("  |  ".join(parts_contact)), small_right))

        parts_legal = []
        rc = getattr(doc_params, "rc", None)
        ninea = getattr(doc_params, "ninea", None)
        if rc: parts_legal.append(f"RC : {rc}")
        if ninea: parts_legal.append(f"NINEA : {ninea}")
        if parts_legal:
            right_items.append(Paragraph(escape("  |  ".join(parts_legal)), small_right))

        cb = (getattr(doc_params, "compte_bancaire", None) or "").strip()
        if cb:
            right_items.append(Paragraph(escape(f"Banque : {cb}"), small_right))

    t = Table([[left_items, right_items]], colWidths=[col1_w, col2_w])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [t, Spacer(1, 5 * mm)]



def build_proforma_pdf_bytesio(
    proforma: Any,
    doc_params: Any,
    montant_lettres: str,
    format_fcfa: Callable[[Any], str],
    logo_path: str | None,
) -> io.BytesIO:
    _ensure_fonts()
    buffer = io.BytesIO()
    LM = RM = 16 * mm
    TM = BM = 14 * mm
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM)
    usable_w = A4[0] - LM - RM

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "pt",
        parent=styles["Normal"],
        fontName="Vera-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    body = ParagraphStyle(
        "pb",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=10.5,
        leading=14,
        spaceAfter=5,
    )
    small = ParagraphStyle("ps", parent=body, fontSize=9, leading=11)

    story: list = []
    story.extend(_header_flowable(logo_path, doc_params, usable_w))
    story.append(Paragraph(escape(f"PROFORMA No {proforma.numero}"), title_style))
    cn = proforma.client.raison_sociale if getattr(proforma, "client", None) else ""
    story.append(Paragraph(f"<b>CLIENT :</b> {escape(cn)}", body))
    story.append(
        Paragraph(
            f"Arrêté le présent document à la somme de : <b>{escape(montant_lettres)}</b>.",
            body,
        )
    )
    story.extend(_story_coords(doc_params, proforma.date_emission))
    story.append(Spacer(1, 4 * mm))

    col_desc = usable_w * 0.52
    col_q = usable_w * 0.11
    col_pu = usable_w * 0.185
    col_mt = usable_w * 0.185
    hdr = ParagraphStyle("h", parent=body, fontName="Vera-Bold", fontSize=10, leading=12)
    c_left = ParagraphStyle("l", parent=body, fontSize=10, leading=12)
    c_right = ParagraphStyle("r", parent=body, fontSize=10, leading=12, alignment=TA_RIGHT)
    c_tot_l = ParagraphStyle("tl", parent=c_left, fontName="Vera-Bold")
    c_tot_r = ParagraphStyle("tr", parent=c_right, fontName="Vera-Bold")

    data = [
        [
            Paragraph("DÉSIGNATION", hdr),
            Paragraph("QUANTITÉ", hdr),
            Paragraph("PRIX<br/>UNITAIRE", hdr),
            Paragraph("MONTANT", hdr),
        ]
    ]
    for l in sorted(getattr(proforma, "lignes", None) or [], key=lambda x: x.id):
        des = l.produit.designation if getattr(l, "produit", None) else ""
        data.append(
            [
                Paragraph(escape(str(des)), c_left),
                Paragraph(escape(str(l.quantite)), c_right),
                Paragraph(escape(format_fcfa(l.prix_unitaire_ht)), c_right),
                Paragraph(escape(format_fcfa(l.montant_ht)), c_right),
            ]
        )
    data.append(
        [
            Paragraph("Total", c_tot_l),
            Paragraph("", c_right),
            Paragraph("", c_right),
            Paragraph(escape(format_fcfa(proforma.total_ht)), c_tot_r),
        ]
    )
    tbl = Table(data, colWidths=[col_desc, col_q, col_pu, col_mt], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(tbl)
    if document_affiche_tva(proforma):
        story.append(Spacer(1, 3 * mm))
        story.append(
            Paragraph(
                escape(
                    f"TVA : {format_fcfa(proforma.tva_montant)} — Total TTC : {format_fcfa(proforma.total_ttc)}"
                ),
                small,
            )
        )
    notes = (getattr(proforma, "notes", None) or "").strip()
    if notes:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Notes :</b> {escape(notes)}", small))
    pied = (getattr(doc_params, "pied_de_page", None) or "").strip()
    if pied:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(escape(pied).replace("\n", "<br/>"), small))
    doc.build(story)
    buffer.seek(0)
    return buffer


# Marges facture PDF : en-tête logo + infos société (sans pied de page).
_FACTURE_TOP_MM = 34
_FACTURE_BOTTOM_MM = 16
_FACTURE_SIDE_MM = 16
_FACTURE_LINES_PER_PAGE = 12


def _facture_coords_line(doc_params: Any) -> str:
    """Ligne unique type document proforma / facture papier (adresse + Tel RC NINEA Email compte)."""
    parts: list[str] = []
    ad = (getattr(doc_params, "adresse_ligne", None) or "").strip()
    if ad:
        parts.append(ad)
    sub: list[str] = []
    if getattr(doc_params, "telephone", None):
        sub.append(f"Tel : {doc_params.telephone}")
    if getattr(doc_params, "rc", None):
        sub.append(f"RC : {doc_params.rc}")
    if getattr(doc_params, "ninea", None):
        sub.append(f"NINEA : {doc_params.ninea}")
    if getattr(doc_params, "email", None):
        sub.append(f"Email : {doc_params.email}")
    if sub:
        parts.append(" ".join(sub))
    cb = (getattr(doc_params, "compte_bancaire", None) or "").strip()
    if cb:
        parts.append(cb)
    return " ".join(parts)


_INV_PRIMARY = colors.HexColor("#721818")
_INV_INK = colors.HexColor("#0f172a")
_INV_MUTED = colors.HexColor("#64748b")
_INV_BORDER = colors.HexColor("#e2e8f0")
_DEFAULT_SLOGAN = "Serving those who care for others"


def _resolve_slogan(doc_params: Any) -> str:
    slogan = (getattr(doc_params, "slogan", None) or "").strip()
    return slogan or _DEFAULT_SLOGAN


def _resolve_site_web(doc_params: Any) -> str:
    from .parametres_pdf import normalize_site_web_url

    return normalize_site_web_url(getattr(doc_params, "site_web", None))


def _draw_qr_on_canvas(canvas: Any, x: float, y: float, url: str, size: float) -> None:
    """Dessine un QR code (URL) sur le canvas PDF."""
    if not url:
        return
    try:
        qr = QrCodeWidget(url)
        bounds = qr.getBounds()
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        if w <= 0 or h <= 0:
            return
        drawing = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        drawing.add(qr)
        renderPDF.draw(drawing, canvas, x, y)
    except Exception as exc:
        logger.warning("QR code PDF ignoré : %s", exc)


def _wrap_text_lines(text: str, max_chars: int = 42) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines[:3]


def _facture_draw_header(
    canvas: Any, doc: Any, doc_params: Any, logo_path: str | None, site_web: str
) -> None:
    """Bandeau haut : logo, slogan, QR en dessous à droite, infos société à droite."""
    W, H = doc.pagesize
    lm = _FACTURE_SIDE_MM * mm
    rm = W - _FACTURE_SIDE_MM * mm
    band_bottom = H - _FACTURE_TOP_MM * mm

    canvas.saveState()

    # Barre d'accent en haut de page
    canvas.setFillColor(_INV_PRIMARY)
    canvas.rect(0, H - 2.5 * mm, W, 2.5 * mm, fill=1, stroke=0)

    logo_y = band_bottom + 4 * mm
    logo_h = 0.0
    logo_w = 0.0
    if logo_path and os.path.isfile(logo_path):
        try:
            ir = ImageReader(logo_path)
            iw, ih = ir.getSize()
            max_h = 28 * mm
            max_w = 65 * mm
            scale = min(max_w / iw, max_h / ih, 1.0)
            dw, dh = iw * scale, ih * scale
            canvas.drawImage(logo_path, lm, logo_y, width=dw, height=dh, mask="auto")
            logo_h = dh
            logo_w = dw
        except Exception as e:
            logger.warning("Logo facture PDF : %s", e)

    qr_size = 10 * mm
    qr_x = rm - qr_size
    qr_y = logo_y + max(0, (logo_h - qr_size) / 2)
    _draw_qr_on_canvas(canvas, qr_x, qr_y, site_web, qr_size)

    slogan = _DEFAULT_SLOGAN
    canvas.setFont("Vera-Italic", 7.5)
    canvas.setFillColor(_INV_PRIMARY)
    slogan_y = qr_y + (qr_size / 2) - 1.5 * mm
    canvas.drawRightString(qr_x - 3 * mm, slogan_y, slogan)

    # Info société à droite
    y = H - 12 * mm
    
    rs = (getattr(doc_params, "raison_sociale", None) or "").strip()
    if rs:
        canvas.setFont("Vera-Bold", 10)
        canvas.setFillColor(_INV_INK)
        canvas.drawRightString(rm, y, rs)
        y -= 6 * mm

    canvas.setFont("Vera", 9)
    canvas.setFillColor(_INV_MUTED)
    
    lines: list[str] = []
    ad = (getattr(doc_params, "adresse_ligne", None) or "").strip()
    if ad:
        lines.append(ad)

    for text in lines:
        canvas.drawRightString(rm, y, text)
        y -= 4.5 * mm

    canvas.restoreState()


def _facture_draw_bottom_qr(canvas: Any, doc: Any, site_web: str) -> None:
    """QR code en bas à droite de la page."""
    W, _H = doc.pagesize
    rm = W - _FACTURE_SIDE_MM * mm
    qr_size = 18 * mm
    qr_x = rm - qr_size
    qr_y = _FACTURE_BOTTOM_MM * mm + 2 * mm
    _draw_qr_on_canvas(canvas, qr_x, qr_y, site_web, qr_size)


def _facture_draw_footer(canvas: Any, doc: Any, doc_params: Any) -> None:
    """Pied de page supprimé à la demande de l'utilisateur."""
    pass


def _chunk_facture_lines(lignes: list, size: int = _FACTURE_LINES_PER_PAGE) -> list[list]:
    if not lignes:
        return [[]]
    return [lignes[i : i + size] for i in range(0, len(lignes), size)]


def _facture_pdf_lines_table(
    chunk: list,
    *,
    col_desc: float,
    col_q: float,
    col_pu: float,
    col_mt: float,
    hdr_l: ParagraphStyle,
    hdr_c: ParagraphStyle,
    hdr_r: ParagraphStyle,
    c_left: ParagraphStyle,
    c_center: ParagraphStyle,
    c_right: ParagraphStyle,
    format_fcfa: Callable[[Any], str],
) -> Table:
    data: list[list] = [
        [
            Paragraph("Désignation", hdr_l),
            Paragraph("Quantité", hdr_c),
            Paragraph("Prix unitaire<br/>(FCFA)", hdr_c),
            Paragraph("Total<br/>(FCFA)", hdr_r),
        ]
    ]
    for l in chunk:
        des = l.produit.designation if getattr(l, "produit", None) else ""
        data.append(
            [
                Paragraph(escape(str(des)), c_left),
                Paragraph(escape(str(l.quantite)), c_center),
                _pdf_amount_paragraph(format_fcfa(l.prix_unitaire_ht), c_center),
                _pdf_amount_paragraph(format_fcfa(l.montant_ht), c_right),
            ]
        )

    tbl = Table(data, colWidths=[col_desc, col_q, col_pu, col_mt], repeatRows=1)
    row_styles: list[tuple] = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, 0), _INV_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Vera-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOX", (0, 0), (-1, -1), 0.75, _INV_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _INV_BORDER),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            row_styles.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fafbfc")))
    tbl.setStyle(TableStyle(row_styles))
    return tbl


def _company_info_rows(
    doc_params: Any,
    *,
    card_label: ParagraphStyle,
    card_sub: ParagraphStyle,
    mode_paiement: str | None = None,
    notes: str | None = None,
) -> list:
    """Lignes du bloc INFORMATIONS (facture / BL / proforma)."""
    from .parametres_pdf import DEFAULT_COMPANY_COORDS

    def _val(key: str) -> str:
        raw = (getattr(doc_params, key, None) or "").strip() if doc_params else ""
        return raw or DEFAULT_COMPANY_COORDS.get(key, "")

    rows: list = [[Paragraph("INFORMATIONS", card_label)]]
    rows.append([Paragraph(escape(f"Tél. {_val('telephone')}"), card_sub)])
    rows.append([Paragraph(escape(f"Email {_val('email')}"), card_sub)])
    rows.append([Paragraph(escape(f"RC {_val('rc')}"), card_sub)])
    rows.append([Paragraph(escape(f"NINEA {_val('ninea')}"), card_sub)])
    if mode_paiement:
        rows.append([Paragraph(escape(f"Paiement {mode_paiement}"), card_sub)])
    rows.append([Paragraph(escape(f"Compte bancaire {_val('compte_bancaire')}"), card_sub)])
    if notes:
        rows.append([Paragraph(escape(notes), card_sub)])
    return rows


def _facture_pdf_info_grid(
    facture: Any,
    doc_params: Any,
    usable_w: float,
    *,
    card_label: ParagraphStyle,
    card_title: ParagraphStyle,
    card_sub: ParagraphStyle,
    card_name: ParagraphStyle,
    card_phone: ParagraphStyle,
) -> Table:
    left_rows: list = [
        [Paragraph("FACTURE", card_label)],
        [Paragraph(escape(f"N° {facture.numero}"), card_title)],
    ]
    if getattr(facture, "date_emission", None):
        left_rows.append(
            [Paragraph(escape(f"Émise le {facture.date_emission.strftime('%d/%m/%Y')}"), card_sub)]
        )
    bc = (getattr(facture, "bc", None) or "").strip()
    if bc:
        left_rows.append([Paragraph(escape(f"BC : {bc}"), card_sub)])
    left_rows.append([Spacer(1, 1 * mm)])
    left_rows.append([Paragraph("CLIENT", card_label)])
    cn = facture.client.raison_sociale if getattr(facture, "client", None) else "—"
    left_rows.append([Paragraph(escape(cn), card_name)])
    client = getattr(facture, "client", None)
    if client and getattr(client, "telephone", None):
        left_rows.append([Paragraph(escape(f"Tél. {client.telephone}"), card_phone)])

    right_rows = _company_info_rows(
        doc_params,
        card_label=card_label,
        card_sub=card_sub,
        mode_paiement=getattr(facture, "mode_paiement", None),
    )

    left_tbl = Table(left_rows, colWidths=[usable_w * 0.46])
    right_tbl = Table(right_rows, colWidths=[usable_w * 0.46])
    card_style = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BOX", (0, 0), (-1, -1), 0.75, _INV_BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ]
    )
    left_tbl.setStyle(card_style)
    right_tbl.setStyle(card_style)
    info_grid = Table(
        [[left_tbl, Spacer(usable_w * 0.04, 1), right_tbl]],
        colWidths=[usable_w * 0.48, usable_w * 0.04, usable_w * 0.48],
    )
    info_grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return info_grid


def _bl_pdf_info_grid(
    bl: Any,
    doc_params: Any,
    usable_w: float,
    *,
    card_label: ParagraphStyle,
    card_title: ParagraphStyle,
    card_sub: ParagraphStyle,
    card_name: ParagraphStyle,
) -> Table:
    left_rows: list = [
        [Paragraph("BON DE LIVRAISON", card_label)],
        [Paragraph(escape(f"N° {bl.numero}"), card_title)],
    ]
    if getattr(bl, "date_livraison", None):
        left_rows.append(
            [
                Paragraph(
                    escape(f"Livraison le {bl.date_livraison.strftime('%d/%m/%Y')}"),
                    card_sub,
                )
            ]
        )
    left_rows.append([Spacer(1, 1 * mm)])
    left_rows.append([Paragraph("CLIENT", card_label)])
    cn = bl.client.raison_sociale if getattr(bl, "client", None) else "—"
    left_rows.append([Paragraph(escape(cn), card_name)])
    adr = (getattr(bl, "adresse_livraison", None) or "").strip()
    if adr:
        left_rows.append([Paragraph(escape(adr), card_sub)])
    livreur = (getattr(bl, "livreur", None) or "").strip()
    if livreur:
        left_rows.append([Paragraph(escape(f"Livreur : {livreur}"), card_sub)])

    notes = (getattr(bl, "notes", None) or "").strip()
    right_rows = _company_info_rows(
        doc_params,
        card_label=card_label,
        card_sub=card_sub,
        notes=notes or None,
    )

    left_tbl = Table(left_rows, colWidths=[usable_w * 0.46])
    right_tbl = Table(right_rows, colWidths=[usable_w * 0.46])
    card_style = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BOX", (0, 0), (-1, -1), 0.75, _INV_BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ]
    )
    left_tbl.setStyle(card_style)
    right_tbl.setStyle(card_style)
    info_grid = Table(
        [[left_tbl, Spacer(usable_w * 0.04, 1), right_tbl]],
        colWidths=[usable_w * 0.48, usable_w * 0.04, usable_w * 0.48],
    )
    info_grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return info_grid


def build_facture_pdf_bytesio(
    facture: Any,
    doc_params: Any,
    montant_lettres: str,
    format_fcfa: Callable[[Any], str],
    logo_path: str | None,
    date_lieu_fr: str,
    *,
    cachet_path: str | None = None,
    avec_cachet: bool = False,
) -> io.BytesIO:
    """
    Facture PDF avec en-tête répété (logo à gauche, informations entreprise à droite),
    sans pied de page.
    """
    _ensure_fonts()
    buffer = io.BytesIO()
    LM = RM = _FACTURE_SIDE_MM * mm
    TM = _FACTURE_TOP_MM * mm
    BM = _FACTURE_BOTTOM_MM * mm

    site_web = _resolve_site_web(doc_params)
    page_info = {"total": 1}

    def on_page(c: Any, d: Any) -> None:
        _facture_draw_header(c, d, doc_params, logo_path, site_web)
        c.saveState()
        c.setFont("Vera", 8)
        c.setFillColor(_INV_MUTED)
        c.drawCentredString(A4[0] / 2, 7 * mm, f"Page {d.page} / {page_info['total']}")
        c.restoreState()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=LM,
        rightMargin=RM,
        topMargin=TM,
        bottomMargin=BM,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(
        [
            PageTemplate(
                id="Facture",
                frames=[frame],
                onPage=on_page,
                pagesize=A4,
            )
        ]
    )

    usable_w = A4[0] - LM - RM
    styles = getSampleStyleSheet()

    # Mise en page calquée sur modèle type PROFORMAT-3 (document simple, noir & blanc)
    title_line = ParagraphStyle(
        "ft_pro",
        parent=styles["Normal"],
        fontName="Vera-Bold",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=10,
    )
    body = ParagraphStyle(
        "fb",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=10.5,
        leading=14,
        spaceAfter=6,
        textColor=colors.black,
    )
    body_small = ParagraphStyle("fbs", parent=body, fontSize=9.5, leading=13, spaceAfter=8)
    small = ParagraphStyle("fs", parent=body, fontSize=9.5, leading=12)

    hdr_l = ParagraphStyle(
        "fh_l",
        parent=body,
        fontName="Vera-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    hdr_c = ParagraphStyle(
        "fh_c",
        parent=body,
        fontName="Vera-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    hdr_r = ParagraphStyle(
        "fh_r",
        parent=body,
        fontName="Vera-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_RIGHT,
    )
    c_left = ParagraphStyle("fl", parent=body, fontSize=10, leading=12.5)
    c_center = ParagraphStyle("fc", parent=body, fontSize=10, leading=12.5, alignment=TA_CENTER)
    c_right = ParagraphStyle("fr", parent=body, fontSize=10, leading=12.5, alignment=TA_RIGHT)
    body_amount = ParagraphStyle(
        "fba",
        parent=body,
        fontName="Vera",
        textColor=colors.HexColor("#164e63"),
        backColor=colors.HexColor("#ecfeff"),
        borderPadding=6,
        leftIndent=4,
    )

    card_label = ParagraphStyle(
        "card_lbl",
        parent=body,
        fontName="Vera-Bold",
        fontSize=6.5,
        leading=8,
        textColor=_INV_PRIMARY,
        spaceAfter=2,
    )
    card_title = ParagraphStyle(
        "card_doc",
        parent=body,
        fontName="Vera-Bold",
        fontSize=10,
        leading=12,
        textColor=_INV_INK,
        spaceAfter=1,
    )
    card_sub = ParagraphStyle(
        "card_sub",
        parent=body,
        fontSize=8,
        leading=10,
        textColor=_INV_MUTED,
        spaceAfter=3,
    )
    card_name = ParagraphStyle(
        "card_name",
        parent=body,
        fontName="Vera-Bold",
        fontSize=9,
        leading=11,
        textColor=_INV_INK,
        spaceAfter=1,
    )
    card_phone = ParagraphStyle(
        "card_phone",
        parent=body,
        fontName="Vera-Bold",
        fontSize=8,
        leading=10,
        textColor=_INV_INK,
        spaceAfter=1,
    )

    story: list = []

    def append_info_grid() -> None:
        story.append(
            _facture_pdf_info_grid(
                facture,
                doc_params,
                usable_w,
                card_label=card_label,
                card_title=card_title,
                card_sub=card_sub,
                card_name=card_name,
                card_phone=card_phone,
            )
        )
        story.append(Spacer(1, 4 * mm))

    col_desc = usable_w * 0.48
    col_q = usable_w * 0.14
    col_pu = usable_w * 0.19
    col_mt = usable_w * 0.19

    lignes_sorted = sorted(getattr(facture, "lignes", None) or [], key=lambda x: x.id)
    sous_total = sum(float(l.montant_ht or 0) for l in lignes_sorted)
    rem_raw = float(getattr(facture, "remise_globale", 0) or 0)
    remise_montant = max(0.0, sous_total - float(facture.total_ht or 0))
    if rem_raw > 0 and rem_raw <= 100:
        remise_pct = rem_raw
    elif sous_total > 0 and remise_montant > 0:
        remise_pct = round(remise_montant / sous_total * 100)
    else:
        remise_pct = 0
    line_chunks = _chunk_facture_lines(lignes_sorted)
    needs_break_before_bottom = (
        len(lignes_sorted) > 0 and len(line_chunks[-1]) >= _FACTURE_LINES_PER_PAGE
    )
    page_info["total"] = len(line_chunks) + (1 if needs_break_before_bottom else 0)

    for chunk_idx, chunk in enumerate(line_chunks):
        if chunk_idx > 0:
            story.append(PageBreak())
        append_info_grid()
        story.append(
            _facture_pdf_lines_table(
                chunk,
                col_desc=col_desc,
                col_q=col_q,
                col_pu=col_pu,
                col_mt=col_mt,
                hdr_l=hdr_l,
                hdr_c=hdr_c,
                hdr_r=hdr_r,
                c_left=c_left,
                c_center=c_center,
                c_right=c_right,
                format_fcfa=format_fcfa,
            )
        )
        story.append(Spacer(1, 4 * mm))

    tva_ok = document_affiche_tva(facture)
    tot_lbl = ParagraphStyle(
        "tot_lbl",
        parent=body,
        fontSize=9,
        leading=11,
        textColor=_INV_MUTED,
    )
    tot_val = ParagraphStyle(
        "tot_val",
        parent=body,
        fontName="Vera-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT,
    )
    tot_grand_l = ParagraphStyle(
        "tot_grand_l",
        parent=tot_lbl,
        fontName="Vera-Bold",
        fontSize=10,
        textColor=colors.white,
    )
    tot_grand_r = ParagraphStyle(
        "tot_grand_r",
        parent=tot_val,
        fontSize=10,
        textColor=colors.white,
    )

    totals_data: list[list] = []
    if remise_montant > 0.5:
        totals_data.append(
            [
                Paragraph("Sous-total", tot_lbl),
                _pdf_amount_paragraph(format_fcfa(sous_total), tot_val),
            ]
        )
        totals_data.append(
            [
                Paragraph(
                    escape(
                        f"Remise (−{remise_pct:g} %)"
                        if remise_pct
                        else "Remise"
                    ),
                    tot_lbl,
                ),
                _pdf_amount_paragraph(f"−{format_fcfa(remise_montant)}", tot_val),
            ]
        )

    if tva_ok:
        totals_data.append(
            [
                Paragraph("Total HT", tot_lbl),
                _pdf_amount_paragraph(format_fcfa(facture.total_ht), tot_val),
            ]
        )
        totals_data.append(
            [
                Paragraph("TVA", tot_lbl),
                _pdf_amount_paragraph(format_fcfa(facture.tva_montant), tot_val),
            ]
        )
        totals_data.append(
            [
                Paragraph("Total TTC", tot_grand_l),
                _pdf_amount_paragraph(format_fcfa(facture.total_ttc), tot_grand_r),
            ]
        )
    else:
        totals_data.append(
            [
                Paragraph("Total", tot_grand_l),
                _pdf_amount_paragraph(format_fcfa(facture.total_ht), tot_grand_r),
            ]
        )

    col_tot = usable_w * 0.42
    totals_tbl = Table(totals_data, colWidths=[col_tot * 0.36, col_tot * 0.64])
    grand_row = len(totals_data) - 1
    totals_style: list[tuple] = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.75, _INV_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _INV_BORDER),
        ("BACKGROUND", (0, grand_row), (-1, grand_row), _INV_PRIMARY),
    ]
    totals_tbl.setStyle(TableStyle(totals_style))

    col_words = usable_w * 0.56
    bottom_tbl = Table(
        [
            [
                Paragraph(
                    f"Arrêtée la présente facture à la somme de :<br/><b>{escape(montant_lettres)}</b>.",
                    body_amount,
                ),
                totals_tbl,
            ]
        ],
        colWidths=[col_words, col_tot],
    )
    bottom_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 6),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )

    if needs_break_before_bottom:
        story.append(PageBreak())
        append_info_grid()

    story.append(Spacer(1, 2 * mm))
    story.append(bottom_tbl)

    story.append(Spacer(1, 15 * mm))
    sig_style = ParagraphStyle("sig", parent=body, alignment=TA_CENTER)
    
    # Build signature layout aligned to the right
    sig_data = []
    if date_lieu_fr:
        sig_data.append([Paragraph(escape(date_lieu_fr), sig_style)])
    if avec_cachet and cachet_path and os.path.isfile(cachet_path):
        try:
            img = Image(cachet_path)
            img.hAlign = "CENTER"
            # max ~48mm wide
            max_w, max_h = 48 * mm, 48 * mm
            iw, ih = img.imageWidth, img.imageHeight
            scale = min(max_w / float(iw), max_h / float(ih), 1.0)
            img.drawWidth = iw * scale
            img.drawHeight = ih * scale
            sig_data.append([Spacer(1, 3 * mm)])
            sig_data.append([img])
        except Exception:
            sig_data.append([Spacer(1, 25 * mm)])
    else:
        sig_data.append([Spacer(1, 25 * mm)])  # space for stamp/signature
    
    sig_table = Table(sig_data, colWidths=[65 * mm])
    sig_table.hAlign = 'RIGHT'
    story.append(sig_table)

    doc.build(story)
    buffer.seek(0)
    return buffer


def build_bl_pdf_bytesio(
    bl: Any,
    doc_params: Any,
    logo_path: str | None,
    *,
    cachet_path: str | None = None,
    avec_cachet: bool = False,
) -> io.BytesIO:
    _ensure_fonts()
    buffer = io.BytesIO()
    LM = RM = 16 * mm
    TM = BM = 14 * mm
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM)
    usable_w = A4[0] - LM - RM

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "bb",
        parent=styles["Normal"],
        fontName="Vera",
        fontSize=10.5,
        leading=14,
        spaceAfter=5,
    )
    small = ParagraphStyle("bs", parent=body, fontSize=9, leading=11)
    card_label = ParagraphStyle(
        "bl_card_lbl",
        parent=body,
        fontName="Vera-Bold",
        fontSize=7,
        leading=9,
        textColor=_INV_PRIMARY,
        spaceAfter=2,
    )
    card_title = ParagraphStyle(
        "bl_card_title",
        parent=body,
        fontName="Vera-Bold",
        fontSize=11,
        leading=13,
    )
    card_sub = ParagraphStyle(
        "bl_card_sub",
        parent=body,
        fontSize=8.5,
        leading=11,
        textColor=_INV_MUTED,
    )
    card_name = ParagraphStyle(
        "bl_card_name",
        parent=body,
        fontName="Vera-Bold",
        fontSize=10,
        leading=12,
    )

    story: list = []
    story.extend(_header_flowable(logo_path, doc_params, usable_w))
    story.append(Spacer(1, 2 * mm))
    story.append(
        _bl_pdf_info_grid(
            bl,
            doc_params,
            usable_w,
            card_label=card_label,
            card_title=card_title,
            card_sub=card_sub,
            card_name=card_name,
        )
    )
    story.append(Spacer(1, 4 * mm))

    col_d = usable_w * 0.72
    col_q = usable_w * 0.28
    hdr_l = ParagraphStyle("bhl", parent=body, fontName="Vera-Bold", fontSize=10, leading=12)
    hdr_c = ParagraphStyle("bhc", parent=hdr_l, alignment=TA_CENTER)
    c_left = ParagraphStyle("bl", parent=body, fontSize=10, leading=12)
    c_right = ParagraphStyle("br", parent=body, fontSize=10, leading=12, alignment=TA_RIGHT)

    data = [[Paragraph("DÉSIGNATION", hdr_l), Paragraph("QUANTITÉ", hdr_c)]]
    for l in sorted(getattr(bl, "lignes", None) or [], key=lambda x: x.id):
        des = l.produit.designation if getattr(l, "produit", None) else ""
        if getattr(l, "lot", None) and getattr(l.lot, "numero_lot", None):
            des = f"{des} — Lot : {l.lot.numero_lot}"
        data.append(
            [
                Paragraph(escape(str(des)), c_left),
                Paragraph(escape(str(bl_quantite_document(l))), c_right),
            ]
        )
    tbl = Table(data, colWidths=[col_d, col_q], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (-1, 0), _INV_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Vera-Bold"),
                ("BOX", (0, 0), (-1, -1), 0.75, _INV_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, _INV_BORDER),
            ]
        )
    )
    story.append(tbl)

    story.append(Spacer(1, 15 * mm))
    sig_style = ParagraphStyle("sig", parent=body, alignment=TA_CENTER)

    mois = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    lieu = (getattr(doc_params, "lieu_signature", None) or "St Louis").strip()
    d = bl.date_livraison
    date_str = (
        f"{lieu}, le {d.day} {mois[d.month - 1].capitalize()} {d.year}" if d else ""
    )

    sig_data = []
    if date_str:
        sig_data.append([Paragraph(escape(date_str), sig_style)])
    if avec_cachet and cachet_path and os.path.isfile(cachet_path):
        try:
            img = Image(cachet_path)
            img.hAlign = "CENTER"
            max_w, max_h = 48 * mm, 48 * mm
            iw, ih = img.imageWidth, img.imageHeight
            scale = min(max_w / float(iw), max_h / float(ih), 1.0)
            img.drawWidth = iw * scale
            img.drawHeight = ih * scale
            sig_data.append([Spacer(1, 3 * mm)])
            sig_data.append([img])
        except Exception:
            sig_data.append([Spacer(1, 25 * mm)])
    else:
        sig_data.append([Spacer(1, 25 * mm)])

    sig_table = Table(sig_data, colWidths=[65 * mm])
    sig_table.hAlign = "RIGHT"
    story.append(sig_table)
    pied = (getattr(doc_params, "pied_de_page", None) or "").strip()
    if pied:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(escape(pied).replace("\n", "<br/>"), small))
    doc.build(story)
    buffer.seek(0)
    return buffer
