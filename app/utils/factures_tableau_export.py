"""Export tableau des factures (présentation type feuille Excel Avalon).

Colonnes :
  Facture | Description | Quantité | PU | Total | Total facture | Client | Date | Reste à payer

Les colonnes Facture / Total facture / Client / Date / Reste à payer sont fusionnées
verticalement sur toutes les lignes produits d'une même facture.
"""

from __future__ import annotations

import io
import os
from datetime import date
from decimal import Decimal
from typing import Iterable

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


HEADERS = (
    "Facture",
    "Description",
    "Quantité",
    "PU",
    "Total",
    "Total facture",
    "Client",
    "Date",
    "Reste à payer",
)

# Colonnes à fusionner verticalement (1-indexed) : Facture, Total facture, Client, Date, Reste
MERGE_COLS = (1, 6, 7, 8, 9)

FONT_NAME = "Calibri"
FONT_SIZE = 12


def _num(v) -> float | None:
    if v is None:
        return None
    return float(Decimal(str(v)))


def build_facture_blocks(factures: Iterable) -> list[dict]:
    """Un bloc = une facture + ses lignes produits (pour fusions)."""
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
                {
                    "description": "",
                    "quantite": None,
                    "pu": None,
                    "total_ligne": None,
                }
            )
        blocks.append(
            {
                "numero": facture.numero,
                "client": client_nom,
                "date": date_str,
                "total_facture": total_facture,
                "reste_a_payer": reste,
                "lignes": lignes_out,
            }
        )
    return blocks


def build_facture_tableau_rows(factures: Iterable) -> list[dict]:
    """Lignes plates (PDF / compat) avec rowspan sur la 1re ligne du bloc."""
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


def _base_font(*, bold: bool = False, color: str | None = None, size: int = FONT_SIZE) -> Font:
    kwargs = {"name": FONT_NAME, "size": size, "bold": bold}
    if color:
        kwargs["color"] = color
    return Font(**kwargs)


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

    header_fill = PatternFill(start_color="721818", end_color="721818", fill_type="solid")
    band_fill = PatternFill(start_color="F7FBFB", end_color="F7FBFB", fill_type="solid")
    alt_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    thin = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    right = Alignment(horizontal="right", vertical="center")

    # ---- En-tête : logo + titre ----
    # Lignes 1-4 réservées au bandeau
    ws.merge_cells("C1:I2")
    title_cell = ws["C1"]
    title_cell.value = f"Tableau des factures — {company_name}"
    title_cell.font = _base_font(bold=True, color="721818", size=16)
    title_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("C3:I3")
    meta_cell = ws["C3"]
    meta_cell.value = filtre_label or f"Export du {date.today().strftime('%d/%m/%Y')}"
    meta_cell.font = _base_font(color="666666", size=12)
    meta_cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 8

    if logo_path and os.path.isfile(logo_path):
        try:
            img = XLImage(logo_path)
            # Conserver proportions, hauteur ~55 px
            max_h = 55
            if img.height and img.height > max_h:
                ratio = max_h / float(img.height)
                img.height = max_h
                img.width = int(img.width * ratio)
            img.anchor = "A1"
            ws.add_image(img)
            ws.merge_cells("A1:B3")
        except Exception:
            ws.merge_cells("A1:B3")
            ws["A1"] = company_name
            ws["A1"].font = _base_font(bold=True, color="721818", size=14)
    else:
        ws.merge_cells("A1:B3")
        ws["A1"] = company_name
        ws["A1"].font = _base_font(bold=True, color="721818", size=14)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    header_row = 5
    for col, title in enumerate(HEADERS, 1):
        cell = ws.cell(row=header_row, column=col, value=title)
        cell.fill = header_fill
        cell.font = _base_font(bold=True, color="FFFFFF")
        cell.alignment = center
        cell.border = thin
    ws.row_dimensions[header_row].height = 22

    data_start = header_row + 1
    current_row = data_start

    for block_idx, block in enumerate(blocks):
        n = len(block["lignes"])
        start = current_row
        end = current_row + n - 1
        fill = band_fill if block_idx % 2 == 0 else alt_fill

        for i, ligne in enumerate(block["lignes"]):
            r = current_row + i
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
                cell.fill = fill
                cell.font = _base_font(bold=(c_idx == 1 and i == 0), color="721818" if c_idx == 1 and i == 0 else None)
                if c_idx in (1, 7, 8):
                    cell.alignment = center
                elif c_idx == 2:
                    cell.alignment = left
                else:
                    cell.alignment = right
                if c_idx in (4, 5, 6, 9) and isinstance(value, (int, float)):
                    cell.number_format = "#,##0"
            ws.row_dimensions[r].height = 18

        if n > 1:
            for col in MERGE_COLS:
                letter = get_column_letter(col)
                ws.merge_cells(f"{letter}{start}:{letter}{end}")
                top = ws.cell(row=start, column=col)
                top.alignment = center
                if col == 1:
                    top.font = _base_font(bold=True, color="721818")

        current_row = end + 1

    widths = (16, 44, 11, 12, 14, 14, 30, 12, 14)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    last_data = max(header_row, current_row - 1)
    ws.auto_filter.ref = f"A{header_row}:I{last_data}"
    ws.freeze_panes = f"A{data_start}"
    ws.print_title_rows = f"{header_row}:{header_row}"

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
