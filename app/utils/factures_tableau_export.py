"""Export tableau des factures — présentation Avalon (charte + fusions).

Structure :
  - bandeau logo à gauche, titre / filtre alignés à droite
  - en-têtes burgundy (#721818), Times 12
  - colonnes : Facture | Descrption | quantite | pu | Total | Total | Client | Date | Reste à payer
  - fusion verticale Facture / Total facture / Client / Date / Reste
  - si tous les mois : un onglet Excel (ou section PDF) par mois
"""

from __future__ import annotations

import io
import os
from collections import OrderedDict
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

MERGE_COLS = (1, 6, 7, 8, 9)

FONT_NAME = "Times New Roman"
FONT_SIZE = 12

# Charte Avalon
COLOR_BURGUNDY = "721818"
COLOR_BURGUNDY_DARK = "5A1218"
COLOR_MINT = "B0DBDD"
COLOR_MINT_SOFT = "EEF8F9"
COLOR_INK = "212529"
COLOR_MUTED = "6C757D"
COLOR_WHITE = "FFFFFF"

MOIS_NOMS = (
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
)

MOIS_SHEET = (
    "Janvier",
    "Fevrier",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Aout",
    "Septembre",
    "Octobre",
    "Novembre",
    "Decembre",
)


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


def mois_label(mois: int) -> str:
    if 1 <= mois <= 12:
        return MOIS_NOMS[mois - 1]
    return str(mois)


def sheet_title_mois(mois: int) -> str:
    if 1 <= mois <= 12:
        return MOIS_SHEET[mois - 1][:31]
    return f"Mois {mois}"[:31]


def group_factures_by_month(factures: Iterable) -> OrderedDict[int, list]:
    """Groupe les factures par mois (1–12), ordre chronologique. Sans date → 0."""
    groups: OrderedDict[int, list] = OrderedDict()
    for facture in factures:
        d = getattr(facture, "date_emission", None)
        key = int(d.month) if d else 0
        groups.setdefault(key, []).append(facture)
    return groups


def compute_totaux(factures: Iterable) -> dict:
    """Chiffre d'affaires (sum TTC) et reste à payer."""
    ca = 0.0
    reste = 0.0
    nb = 0
    for facture in factures:
        nb += 1
        t = _num(getattr(facture, "total_ttc", None))
        r = _num(getattr(facture, "reste_a_payer", None))
        if t is not None:
            ca += t
        if r is not None:
            reste += r
    return {
        "chiffre_affaires": ca,
        "reste_a_payer": reste,
        "nb_factures": nb,
    }


def compute_totaux_from_blocks(blocks: list[dict]) -> dict:
    ca = 0.0
    reste = 0.0
    for block in blocks:
        t = block.get("total_facture")
        r = block.get("reste_a_payer")
        if t is not None:
            ca += float(t)
        if r is not None:
            reste += float(r)
    return {
        "chiffre_affaires": ca,
        "reste_a_payer": reste,
        "nb_factures": len(blocks),
    }


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


def build_facture_sections_by_month(factures: Iterable) -> tuple[list[dict], dict]:
    """Sections PDF : une par mois (titre + rows + totaux) et totaux globaux."""
    sections: list[dict] = []
    grand = {"chiffre_affaires": 0.0, "reste_a_payer": 0.0, "nb_factures": 0}
    for mois_num, facts in group_factures_by_month(factures).items():
        title = mois_label(mois_num) if mois_num else "Sans date"
        tot = compute_totaux(facts)
        grand["chiffre_affaires"] += tot["chiffre_affaires"]
        grand["reste_a_payer"] += tot["reste_a_payer"]
        grand["nb_factures"] += tot["nb_factures"]
        sections.append(
            {
                "mois": mois_num,
                "title": title,
                "rows": build_facture_tableau_rows(facts),
                "totaux": tot,
            }
        )
    return sections, grand


def _font(*, bold: bool = False, color: str | None = None, size: int = FONT_SIZE) -> Font:
    kw = {"name": FONT_NAME, "size": size, "bold": bold}
    if color:
        kw["color"] = color
    return Font(**kw)


def _write_sheet(
    ws,
    factures: Iterable,
    *,
    filtre_label: str = "",
    logo_path: str | None = None,
    company_name: str = "Avalon Pharma",
) -> None:
    blocks = build_facture_blocks(factures)

    thin = Border(
        left=Side(style="thin", color=COLOR_BURGUNDY_DARK),
        right=Side(style="thin", color=COLOR_BURGUNDY_DARK),
        top=Side(style="thin", color=COLOR_BURGUNDY_DARK),
        bottom=Side(style="thin", color=COLOR_BURGUNDY_DARK),
    )
    header_fill = PatternFill(
        start_color=COLOR_BURGUNDY, end_color=COLOR_BURGUNDY, fill_type="solid"
    )
    alt_fill = PatternFill(
        start_color=COLOR_MINT_SOFT, end_color=COLOR_MINT_SOFT, fill_type="solid"
    )
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    right = Alignment(horizontal="right", vertical="center")
    right_top = Alignment(horizontal="right", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    ws.merge_cells("C1:I1")
    ws["C1"] = f"Tableau des factures — {company_name}"
    ws["C1"].font = _font(bold=True, size=14, color=COLOR_BURGUNDY)
    ws["C1"].alignment = right_top

    ws.merge_cells("C2:I2")
    ws["C2"] = filtre_label or f"Export du {date.today().strftime('%d/%m/%Y')}"
    ws["C2"].font = _font(size=11, color=COLOR_MUTED)
    ws["C2"].alignment = right_top

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
        ws["A1"].font = _font(bold=True, size=12, color=COLOR_BURGUNDY)
        ws["A1"].alignment = center
    else:
        ws.merge_cells("A1:B2")

    header_r1, header_r2 = 4, 5
    for col, title in enumerate(HEADERS, 1):
        cell = ws.cell(row=header_r1, column=col, value=title)
        cell.fill = header_fill
        cell.font = _font(bold=True, color=COLOR_WHITE)
        cell.alignment = center
        cell.border = thin
        cell2 = ws.cell(row=header_r2, column=col, value=None)
        cell2.fill = header_fill
        cell2.border = thin
        letter = get_column_letter(col)
        ws.merge_cells(f"{letter}{header_r1}:{letter}{header_r2}")

    ws.row_dimensions[header_r1].height = 18
    ws.row_dimensions[header_r2].height = 18

    current = header_r2 + 1
    for block_idx, block in enumerate(blocks):
        n = len(block["lignes"])
        start = current
        end = current + n - 1
        use_alt = block_idx % 2 == 1

        for i, ligne in enumerate(block["lignes"]):
            r = current + i
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
                cell.font = _font(color=COLOR_INK)
                if use_alt:
                    cell.fill = alt_fill
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
                top.font = _font(color=COLOR_INK)
                if use_alt:
                    top.fill = alt_fill

        current = end + 1

    # ---- Totaux CA + reste à payer ----
    totaux = compute_totaux_from_blocks(blocks)
    current += 1  # ligne vide
    total_fill = PatternFill(
        start_color=COLOR_MINT, end_color=COLOR_MINT, fill_type="solid"
    )
    burgundy_fill = PatternFill(
        start_color=COLOR_BURGUNDY, end_color=COLOR_BURGUNDY, fill_type="solid"
    )

    # Ligne libellés
    for c in range(1, 10):
        cell = ws.cell(row=current, column=c)
        cell.fill = burgundy_fill
        cell.border = thin
        cell.font = _font(bold=True, color=COLOR_WHITE)
        cell.alignment = center
    ws.merge_cells(f"A{current}:E{current}")
    ws.cell(row=current, column=1).value = "TOTAL"
    ws.cell(row=current, column=6).value = "Chiffre d'affaires"
    ws.cell(row=current, column=7).value = f"{totaux['nb_factures']} facture(s)"
    ws.merge_cells(f"G{current}:H{current}")
    ws.cell(row=current, column=9).value = "Reste à payer"

    # Ligne montants
    current += 1
    for c in range(1, 10):
        cell = ws.cell(row=current, column=c)
        cell.fill = total_fill
        cell.border = thin
    ws.merge_cells(f"A{current}:E{current}")
    ca_cell = ws.cell(row=current, column=6, value=totaux["chiffre_affaires"])
    ca_cell.font = _font(bold=True, color=COLOR_BURGUNDY)
    ca_cell.alignment = right
    ca_cell.number_format = "#,##0"
    ws.merge_cells(f"G{current}:H{current}")
    reste_cell = ws.cell(row=current, column=9, value=totaux["reste_a_payer"])
    reste_cell.font = _font(bold=True, color=COLOR_BURGUNDY)
    reste_cell.alignment = right
    reste_cell.number_format = "#,##0"

    widths = (18.5, 37.25, 12, 13.75, 15.88, 20.63, 43.0, 13.0, 16.0)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = f"A{header_r2 + 1}"


def _write_synthese_sheet(
    ws,
    groups: OrderedDict,
    *,
    filtre_label: str = "",
    company_name: str = "Avalon Pharma",
) -> None:
    """Onglet synthèse : CA et reste par mois + total."""
    thin = Border(
        left=Side(style="thin", color=COLOR_BURGUNDY_DARK),
        right=Side(style="thin", color=COLOR_BURGUNDY_DARK),
        top=Side(style="thin", color=COLOR_BURGUNDY_DARK),
        bottom=Side(style="thin", color=COLOR_BURGUNDY_DARK),
    )
    header_fill = PatternFill(
        start_color=COLOR_BURGUNDY, end_color=COLOR_BURGUNDY, fill_type="solid"
    )
    total_fill = PatternFill(
        start_color=COLOR_MINT, end_color=COLOR_MINT, fill_type="solid"
    )
    alt_fill = PatternFill(
        start_color=COLOR_MINT_SOFT, end_color=COLOR_MINT_SOFT, fill_type="solid"
    )
    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    ws["A1"] = f"Synthèse — {company_name}"
    ws["A1"].font = _font(bold=True, size=14, color=COLOR_BURGUNDY)
    ws.merge_cells("A1:D1")
    ws["A2"] = filtre_label or f"Export du {date.today().strftime('%d/%m/%Y')}"
    ws["A2"].font = _font(size=11, color=COLOR_MUTED)
    ws.merge_cells("A2:D2")

    headers = ("Mois", "Nb factures", "Chiffre d'affaires", "Reste à payer")
    for col, title in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=title)
        cell.fill = header_fill
        cell.font = _font(bold=True, color=COLOR_WHITE)
        cell.alignment = center
        cell.border = thin

    row = 5
    grand = {"chiffre_affaires": 0.0, "reste_a_payer": 0.0, "nb_factures": 0}
    for idx, (mois_num, facts) in enumerate(groups.items()):
        tot = compute_totaux(facts)
        grand["chiffre_affaires"] += tot["chiffre_affaires"]
        grand["reste_a_payer"] += tot["reste_a_payer"]
        grand["nb_factures"] += tot["nb_factures"]
        label = mois_label(mois_num) if mois_num else "Sans date"
        values = (label, tot["nb_factures"], tot["chiffre_affaires"], tot["reste_a_payer"])
        for c, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=val)
            cell.border = thin
            cell.font = _font(color=COLOR_INK)
            if idx % 2 == 1:
                cell.fill = alt_fill
            cell.alignment = left if c == 1 else (center if c == 2 else right)
            if c in (3, 4):
                cell.number_format = "#,##0"
        row += 1

    for c, val in enumerate(
        ("TOTAL", grand["nb_factures"], grand["chiffre_affaires"], grand["reste_a_payer"]),
        1,
    ):
        cell = ws.cell(row=row, column=c, value=val)
        cell.border = thin
        cell.font = _font(bold=True, color=COLOR_BURGUNDY)
        cell.fill = total_fill
        cell.alignment = center if c <= 2 else right
        if c in (3, 4):
            cell.number_format = "#,##0"

    for i, w in enumerate((18, 14, 22, 18), 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def generate_factures_tableau_excel(
    factures: Iterable,
    *,
    sheet_title: str = "Factures",
    filtre_label: str = "",
    logo_path: str | None = None,
    company_name: str = "Avalon Pharma",
    split_by_month: bool = False,
) -> io.BytesIO:
    factures_list = list(factures)
    wb = openpyxl.Workbook()

    if split_by_month:
        groups = group_factures_by_month(factures_list)
        default = wb.active
        wb.remove(default)
        if not groups:
            ws = wb.create_sheet(title=(sheet_title or "Factures")[:31])
            _write_sheet(
                ws,
                [],
                filtre_label=filtre_label,
                logo_path=logo_path,
                company_name=company_name,
            )
        else:
            if len(groups) > 1:
                syn = wb.create_sheet(title="Synthese", index=0)
                _write_synthese_sheet(
                    syn,
                    groups,
                    filtre_label=filtre_label,
                    company_name=company_name,
                )
            for mois_num, facts in groups.items():
                title = sheet_title_mois(mois_num) if mois_num else "Sans date"
                mois_filtre = filtre_label
                if mois_num:
                    label_m = mois_label(mois_num)
                    if filtre_label:
                        mois_filtre = f"{filtre_label} · {label_m}"
                    else:
                        mois_filtre = label_m
                ws = wb.create_sheet(title=title)
                _write_sheet(
                    ws,
                    facts,
                    filtre_label=mois_filtre,
                    logo_path=logo_path,
                    company_name=company_name,
                )
    else:
        ws = wb.active
        ws.title = (sheet_title or "Factures")[:31]
        _write_sheet(
            ws,
            factures_list,
            filtre_label=filtre_label,
            logo_path=logo_path,
            company_name=company_name,
        )

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
