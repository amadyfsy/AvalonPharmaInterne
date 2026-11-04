"""Export tableau des factures — présentation fidèle aux feuilles Excel Avalon.

Structure comme Factures.xlsx :
  - bandeau logo + titre au-dessus
  - en-têtes sur 2 lignes fusionnées (noir / blanc, Times 12)
  - colonnes : Facture | Descrption | quantite | pu | Total | Total | Client | Date | Reste à payer
  - fusion verticale Facture / Total facture / Client / Date / Reste sur les lignes produits
"""

from __future__ import annotations

import io
import os
from datetime import date
from decimal import Decimal
from typing import Iterable

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

try:
    from openpyxl.drawing.image import Image as XLImage
except Exception:  # pragma: no cover
    XLImage = None


# Noms d'en-tête comme la feuille d'origine (+ Reste à payer)
HEADERS = (
    "Facture",
    "Descrption",
    "quantite",
    "pu",
    "Total",
    "Total",
    "Client",
    "Date",
    "Reste à payer",
)

# Colonnes fusionnées verticalement (1-index) : Facture, Total facture, Client, Date, Reste
MERGE_COLS = (1, 6, 7, 8, 9)

FONT_NAME = "Times New Roman"
FONT_SIZE = 12


def _num(v) -> float | None:
    if v is None:
        return None
    return float(Decimal(str(v)))


def _numero_affiche(numero: str) -> str:
    n = (numero or "").strip()
    if not n:
        return ""
    if n.lower().startswith("no "):
        return n
    return f"No {n}"


def build_facture_blocks(factures: Iterable) -> list[dict]:
    blocks: list[dict] = []
    for facture in factures:
        client_nom = ""
        if getattr(facture, "client", None):
            client_nom = (facture.client.raison_sociale or "").strip()
        date_str = (
            facture.date_emission.strftime("%d/%m/%Y")
            if facture.date_emission
            else ""
        )
        total_facture = _num(facture.total_ttc)
        reste = _num(facture.reste_a_payer)
        lignes_out = []
        for ligne in list(getattr(facture, "lignes", None) or []):
            designation = ""
            if getattr(ligne, "produit", None):
                designation = (ligne.produit.designation or "").strip()
            lignes_out.append(
                {
                    "description": designation,
                    "quantite": int(ligne.quantite or 0),
                    "pu": _num(ligne.prix_unitaire_ht),
                    "total_ligne": _num(ligne.montant_ht),
                }
            )
        if not lignes_out:
            lignes_out.append(
                {"description": "", "quantite": None, "pu": None, "total_ligne": None}
            )
        blocks.append(
            {
                "numero": _numero_affiche(facture.numero),
                "client": client_nom,
                "date": date_str,
                "total_facture": total_facture,
                "reste_a_payer": reste,
                "lignes": lignes_out,
            }
        )
    return blocks


def build_facture_tableau_rows(factures: Iterable) -> list[dict]:
    """Lignes plates pour PDF (rowspan sur la 1re ligne du bloc)."""
    rows: list[dict] = []
    for block_idx, block in enumerate(build_facture_blocks(factures)):
        n = len(block["lignes"])
        for idx, ligne in enumerate(block["lignes"]):
            rows.append(
                {
                    "numero": block["numero"] if idx == 0 else "",
                    "description": ligne["description"],
                    "quantite": ligne["quantite"],
                    "pu": ligne["pu"],
                    "total_ligne": ligne["total_ligne"],
                    "total_facture": block["total_facture"] if idx == 0 else None,
                    "client": block["client"] if idx == 0 else "",
                    "date": block["date"] if idx == 0 else "",
                    "reste_a_payer": block["reste_a_payer"] if idx == 0 else None,
                    "is_header": idx == 0,
                    "rowspan": n if idx == 0 else 0,
                    "block_even": block_idx % 2 == 0,
                }
            )
    return rows


def _font(*, bold: bool = False, color: str | None = None, size: int = FONT_SIZE) -> Font:
    kw = {"name": FONT_NAME, "size": size, "bold": bold}
    if color:
        kw["color"] = color
    return Font(**kw)


def generate_factures_tableau_excel(
    factures: Iterable,
    *,
    sheet_title: str = "Factures",
    filtre_label: str = "",
    logo_path: str | None = None,
    company_name: str = "Avalon Pharma",
) -> io.BytesIO:
    blocks = build_facture_blocks(factures)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = (sheet_title or "Factures")[:31]

    thin = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )
    header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    right = Alignment(horizontal="right", vertical="center")

    # ---- Bandeau logo + titre (au-dessus du tableau) ----
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    ws.merge_cells("C1:I1")
    ws["C1"] = f"Tableau des factures — {company_name}"
    ws["C1"].font = _font(bold=True, size=14)
    ws["C1"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("C2:I2")
    ws["C2"] = filtre_label or f"Export du {date.today().strftime('%d/%m/%Y')}"
    ws["C2"].font = _font(size=12)
    ws["C2"].alignment = Alignment(horizontal="left", vertical="center")

    logo_ok = False
    if logo_path and os.path.isfile(logo_path) and XLImage is not None:
        try:
            img = XLImage(logo_path)
            max_h = 50
            if img.height and img.height > max_h:
                ratio = max_h / float(img.height)
                img.height = max_h
                img.width = max(1, int(img.width * ratio))
            img.anchor = "A1"
            ws.add_image(img)
            logo_ok = True
        except Exception:
            logo_ok = False
    if not logo_ok:
        ws.merge_cells("A1:B2")
        ws["A1"] = company_name
        ws["A1"].font = _font(bold=True, size=12)
        ws["A1"].alignment = center
    else:
        ws.merge_cells("A1:B2")

    # ---- En-têtes sur 2 lignes (comme la feuille d'origine) ----
    header_r1, header_r2 = 4, 5
    for col, title in enumerate(HEADERS, 1):
        cell = ws.cell(row=header_r1, column=col, value=title)
        cell.fill = header_fill
        cell.font = _font(bold=True, color="FFFFFF")
        cell.alignment = center
        cell.border = thin
        cell2 = ws.cell(row=header_r2, column=col, value=None)
        cell2.fill = header_fill
        cell2.border = thin
        letter = get_column_letter(col)
        ws.merge_cells(f"{letter}{header_r1}:{letter}{header_r2}")

    ws.row_dimensions[header_r1].height = 18
    ws.row_dimensions[header_r2].height = 18

    # ---- Données ----
    current = header_r2 + 1
    for block in blocks:
        n = len(block["lignes"])
        start = current
        end = current + n - 1

        for i, ligne in enumerate(block["lignes"]):
            r = current + i
            # Valeur uniquement sur 1re ligne pour les colonnes fusionnées
            values = [
                block["numero"] if i == 0 else None,
                ligne["description"],
                ligne["quantite"],
                ligne["pu"],
                ligne["total_ligne"],
                block["total_facture"] if i == 0 else None,
                block["client"] if i == 0 else None,
                block["date"] if i == 0 else None,
                block["reste_a_payer"] if i == 0 else None,
            ]
            for c_idx, value in enumerate(values, 1):
                cell = ws.cell(row=r, column=c_idx, value=value)
                cell.border = thin
                cell.font = _font()
                if c_idx in (1, 7, 8):
                    cell.alignment = center
                elif c_idx == 2:
                    cell.alignment = left
                else:
                    cell.alignment = right
                if c_idx in (4, 5, 6, 9) and isinstance(value, (int, float)):
                    cell.number_format = "#,##0"
                if c_idx == 3 and isinstance(value, (int, float)):
                    cell.number_format = "0"

        if n > 1:
            for col in MERGE_COLS:
                letter = get_column_letter(col)
                ws.merge_cells(f"{letter}{start}:{letter}{end}")
                top = ws.cell(row=start, column=col)
                top.alignment = center
                top.font = _font()

        current = end + 1

    # Largeurs proches de la feuille d'origine
    widths = (18.5, 37.25, 12, 13.75, 15.88, 20.63, 43.0, 13.0, 16.0)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = f"A{header_r2 + 1}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_filename(annee=None, mois=None, client_slug: str = "", ext: str = "xlsx") -> str:
    parts = ["Factures"]
    if annee:
        parts.append(str(annee))
    if mois:
        parts.append(f"{int(mois):02d}")
    if client_slug:
        parts.append(client_slug[:40])
    parts.append(date.today().strftime("%Y%m%d"))
    return "_".join(parts) + f".{ext}"
