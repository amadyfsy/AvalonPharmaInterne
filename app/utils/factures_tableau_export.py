"""Export tableau des factures (présentation type feuille Excel Avalon).

Colonnes :
  Facture | Description | Quantité | PU | Total | Total facture | Client | Date | Reste à payer
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from typing import Iterable

import openpyxl
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


def _num(v) -> float | None:
    if v is None:
        return None
    return float(Decimal(str(v)))


def build_facture_tableau_rows(factures: Iterable) -> list[dict]:
    """Construit les lignes plates (1re ligne facture complète, suivantes = produits)."""
    rows: list[dict] = []
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
        lignes = list(getattr(facture, "lignes", None) or [])
        if not lignes:
            rows.append(
                {
                    "numero": facture.numero,
                    "description": "",
                    "quantite": None,
                    "pu": None,
                    "total_ligne": None,
                    "total_facture": total_facture,
                    "client": client_nom,
                    "date": date_str,
                    "reste_a_payer": reste,
                    "is_header": True,
                }
            )
            continue
        for idx, ligne in enumerate(lignes):
            designation = ""
            if getattr(ligne, "produit", None):
                designation = (ligne.produit.designation or "").strip()
            base = {
                "description": designation,
                "quantite": int(ligne.quantite or 0),
                "pu": _num(ligne.prix_unitaire_ht),
                "total_ligne": _num(ligne.montant_ht),
            }
            if idx == 0:
                rows.append(
                    {
                        **base,
                        "numero": facture.numero,
                        "total_facture": total_facture,
                        "client": client_nom,
                        "date": date_str,
                        "reste_a_payer": reste,
                        "is_header": True,
                    }
                )
            else:
                rows.append(
                    {
                        **base,
                        "numero": "",
                        "total_facture": None,
                        "client": "",
                        "date": "",
                        "reste_a_payer": None,
                        "is_header": False,
                    }
                )
    return rows


def generate_factures_tableau_excel(
    factures: Iterable,
    *,
    sheet_title: str = "Factures",
    filtre_label: str = "",
) -> io.BytesIO:
    rows = build_facture_tableau_rows(factures)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = (sheet_title or "Factures")[:31]

    header_fill = PatternFill(start_color="721818", end_color="721818", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, name="Calibri", size=11)
    title_font = Font(bold=True, name="Calibri", size=13, color="721818")
    meta_font = Font(name="Calibri", size=10, color="666666")
    thin = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    header_row_fill = PatternFill(start_color="F7FBFB", end_color="F7FBFB", fill_type="solid")
    money_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.merge_cells("A1:I1")
    ws["A1"] = "Tableau des factures — Avalon Pharma"
    ws["A1"].font = title_font
    ws.merge_cells("A2:I2")
    ws["A2"] = filtre_label or f"Export du {date.today().strftime('%d/%m/%Y')}"
    ws["A2"].font = meta_font

    for col, title in enumerate(HEADERS, 1):
        cell = ws.cell(row=4, column=col, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin

    for r_idx, row in enumerate(rows, 5):
        values = [
            row["numero"],
            row["description"],
            row["quantite"],
            row["pu"],
            row["total_ligne"],
            row["total_facture"],
            row["client"],
            row["date"],
            row["reste_a_payer"],
        ]
        for c_idx, value in enumerate(values, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.border = thin
            cell.alignment = left_align if c_idx in (1, 2, 7, 8) else money_align
            if c_idx in (4, 5, 6, 9) and isinstance(value, (int, float)):
                cell.number_format = "#,##0"
            if row.get("is_header"):
                cell.fill = header_row_fill
                if c_idx == 1:
                    cell.font = Font(bold=True, color="721818", name="Calibri")

    widths = (14, 42, 10, 12, 14, 14, 28, 12, 14)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.auto_filter.ref = f"A4:I{max(4, 4 + len(rows))}"
    ws.freeze_panes = "A5"

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
