"""Export tableau des dépenses — présentation fidèle à DEPENSES.xlsx + charte Avalon.

Colonnes : Facture No | Titre | Description | Total | Fournisseur | Date
Titre général, titre de période par mois, totaux, PDF A4 portrait.
"""

from __future__ import annotations

import calendar
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
    "Facture No",
    "Titre",
    "Description",
    "Total",
    "Fournisseur",
    "Date",
)

FONT_NAME = "Times New Roman"
FONT_SIZE = 12

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


def mois_label(mois: int) -> str:
    if 1 <= mois <= 12:
        return MOIS_NOMS[mois - 1]
    return str(mois)


def sheet_title_mois(mois: int) -> str:
    if 1 <= mois <= 12:
        return MOIS_SHEET[mois - 1][:31]
    return f"Mois {mois}"[:31]


def periode_mois(mois: int, annee: int | None = None) -> tuple[date | None, date | None]:
    if not (1 <= mois <= 12):
        return None, None
    y = annee or date.today().year
    debut = date(y, mois, 1)
    fin = date(y, mois, calendar.monthrange(y, mois)[1])
    return debut, fin


def titre_periode_mois(mois: int, annee: int | None = None) -> str:
    if not (1 <= mois <= 12):
        return "Sans date"
    label = mois_label(mois)
    debut, fin = periode_mois(mois, annee)
    if annee and debut and fin:
        return f"{label} {annee} ({debut.strftime('%d/%m/%Y')} – {fin.strftime('%d/%m/%Y')})"
    if debut and fin:
        return f"{label} ({debut.strftime('%d/%m/%Y')} – {fin.strftime('%d/%m/%Y')})"
    return label


def titre_general_export(
    *,
    company_name: str = "Avalon Pharma",
    annee: int | None = None,
    mois: int | None = None,
) -> str:
    base = f"Tableau des dépenses — {company_name}"
    if annee and mois:
        return f"{base} · {titre_periode_mois(mois, annee)}"
    if annee:
        return f"{base} · Année {annee}"
    if mois:
        return f"{base} · {mois_label(mois)}"
    return base


def infer_annee_from_depenses(depenses: Iterable) -> int | None:
    years = {
        d.date_depense.year
        for d in depenses
        if getattr(d, "date_depense", None)
    }
    if len(years) == 1:
        return next(iter(years))
    return None


def group_depenses_by_month(depenses: Iterable) -> OrderedDict[int, list]:
    buckets: dict[int, list] = {}
    for dep in depenses:
        d = getattr(dep, "date_depense", None)
        key = int(d.month) if d else 0
        buckets.setdefault(key, []).append(dep)
    # Mois 1–12 puis sans date (0)
    ordered = OrderedDict()
    for key in sorted(k for k in buckets if k > 0) + ([0] if 0 in buckets else []):
        ordered[key] = buckets[key]
    return ordered


def compute_totaux(depenses: Iterable) -> dict:
    total = 0.0
    nb = 0
    for dep in depenses:
        nb += 1
        m = _num(getattr(dep, "montant_ttc", None))
        if m is not None:
            total += m
    return {"total": total, "nb_depenses": nb}


def build_depense_rows(depenses: Iterable) -> list[dict]:
    rows: list[dict] = []
    for idx, dep in enumerate(depenses):
        titre = ""
        if getattr(dep, "categorie", None):
            titre = (dep.categorie.nom or "").strip()
        fourn = ""
        if getattr(dep, "fournisseur", None):
            fourn = (dep.fournisseur.raison_sociale or "").strip()
        date_str = (
            dep.date_depense.strftime("%d/%m/%Y") if dep.date_depense else ""
        )
        # Facture No Excel ≈ référence Avalon (pas de n° fournisseur séparé en base)
        rows.append(
            {
                "facture_no": (dep.reference or "").strip(),
                "titre": titre,
                "description": (dep.libelle or "").strip(),
                "total": _num(dep.montant_ttc),
                "fournisseur": fourn,
                "date": date_str,
                "row_even": idx % 2 == 0,
            }
        )
    return rows


def build_depense_sections_by_month(
    depenses: Iterable,
    *,
    annee: int | None = None,
) -> tuple[list[dict], dict]:
    deps_list = list(depenses)
    if annee is None:
        annee = infer_annee_from_depenses(deps_list)
    sections: list[dict] = []
    grand = {"total": 0.0, "nb_depenses": 0}
    for mois_num, facts in group_depenses_by_month(deps_list).items():
        y = annee or infer_annee_from_depenses(facts)
        title = titre_periode_mois(mois_num, y) if mois_num else "Sans date"
        tot = compute_totaux(facts)
        grand["total"] += tot["total"]
        grand["nb_depenses"] += tot["nb_depenses"]
        sections.append(
            {
                "mois": mois_num,
                "annee": y,
                "title": title,
                "rows": build_depense_rows(facts),
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
    depenses: Iterable,
    *,
    filtre_label: str = "",
    logo_path: str | None = None,
    company_name: str = "Avalon Pharma",
    titre_general: str | None = None,
    titre_mois: str | None = None,
) -> None:
    rows = build_depense_rows(depenses)

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
    month_fill = PatternFill(
        start_color=COLOR_MINT, end_color=COLOR_MINT, fill_type="solid"
    )
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    right = Alignment(horizontal="right", vertical="center")
    right_top = Alignment(horizontal="right", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18

    ws.merge_cells("C1:F1")
    ws["C1"] = titre_general or f"Tableau des dépenses — {company_name}"
    ws["C1"].font = _font(bold=True, size=14, color=COLOR_BURGUNDY)
    ws["C1"].alignment = right_top

    ws.merge_cells("C2:F2")
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

    if titre_mois:
        ws.row_dimensions[3].height = 22
        ws.merge_cells("A3:F3")
        ws["A3"] = titre_mois
        ws["A3"].font = _font(bold=True, size=12, color=COLOR_BURGUNDY)
        ws["A3"].alignment = center
        for c in range(1, 7):
            ws.cell(row=3, column=c).border = thin
            ws.cell(row=3, column=c).fill = month_fill
    else:
        ws.row_dimensions[3].height = 10

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
    for row in rows:
        values = (
            row["facture_no"],
            row["titre"],
            row["description"],
            row["total"],
            row["fournisseur"],
            row["date"],
        )
        for c_idx, value in enumerate(values, 1):
            cell = ws.cell(row=current, column=c_idx, value=value)
            cell.border = thin
            cell.font = _font(color=COLOR_INK)
            if not row["row_even"]:
                cell.fill = alt_fill
            if c_idx in (1, 6):
                cell.alignment = center
            elif c_idx == 4:
                cell.alignment = right
                if isinstance(value, (int, float)):
                    cell.number_format = "#,##0"
            else:
                cell.alignment = left
        current += 1

    totaux = compute_totaux(depenses)
    current += 1
    total_fill = PatternFill(
        start_color=COLOR_MINT, end_color=COLOR_MINT, fill_type="solid"
    )
    burgundy_fill = PatternFill(
        start_color=COLOR_BURGUNDY, end_color=COLOR_BURGUNDY, fill_type="solid"
    )
    for c in range(1, 7):
        cell = ws.cell(row=current, column=c)
        cell.fill = burgundy_fill
        cell.border = thin
        cell.font = _font(bold=True, color=COLOR_WHITE)
        cell.alignment = center
    ws.merge_cells(f"A{current}:C{current}")
    ws.cell(row=current, column=1).value = "TOTAL"
    ws.cell(row=current, column=4).value = "Montant total"
    ws.cell(row=current, column=5).value = f"{totaux['nb_depenses']} dépense(s)"
    ws.merge_cells(f"E{current}:F{current}")

    current += 1
    for c in range(1, 7):
        cell = ws.cell(row=current, column=c)
        cell.fill = total_fill
        cell.border = thin
    ws.merge_cells(f"A{current}:C{current}")
    amt = ws.cell(row=current, column=4, value=totaux["total"])
    amt.font = _font(bold=True, color=COLOR_BURGUNDY)
    amt.alignment = right
    amt.number_format = "#,##0"
    ws.merge_cells(f"E{current}:F{current}")

    widths = (18, 28, 42, 16, 28, 14)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"A{header_r2 + 1}"


def _write_synthese_sheet(
    ws,
    groups: OrderedDict,
    *,
    filtre_label: str = "",
    company_name: str = "Avalon Pharma",
    titre_general: str | None = None,
    annee: int | None = None,
) -> None:
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

    ws["A1"] = titre_general or f"Tableau des dépenses — {company_name}"
    ws["A1"].font = _font(bold=True, size=14, color=COLOR_BURGUNDY)
    ws.merge_cells("A1:C1")
    ws["A2"] = "Synthèse par mois"
    ws["A2"].font = _font(bold=True, size=12, color=COLOR_BURGUNDY)
    ws.merge_cells("A2:C2")
    ws["A3"] = filtre_label or f"Export du {date.today().strftime('%d/%m/%Y')}"
    ws["A3"].font = _font(size=11, color=COLOR_MUTED)
    ws.merge_cells("A3:C3")

    headers = ("Période", "Nb dépenses", "Montant total")
    for col, title in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col, value=title)
        cell.fill = header_fill
        cell.font = _font(bold=True, color=COLOR_WHITE)
        cell.alignment = center
        cell.border = thin

    row = 6
    grand = {"total": 0.0, "nb_depenses": 0}
    for idx, (mois_num, facts) in enumerate(groups.items()):
        tot = compute_totaux(facts)
        grand["total"] += tot["total"]
        grand["nb_depenses"] += tot["nb_depenses"]
        y = annee or infer_annee_from_depenses(facts)
        label = titre_periode_mois(mois_num, y) if mois_num else "Sans date"
        values = (label, tot["nb_depenses"], tot["total"])
        for c, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=val)
            cell.border = thin
            cell.font = _font(color=COLOR_INK)
            if idx % 2 == 1:
                cell.fill = alt_fill
            cell.alignment = left if c == 1 else (center if c == 2 else right)
            if c == 3:
                cell.number_format = "#,##0"
        row += 1

    for c, val in enumerate(
        ("TOTAL", grand["nb_depenses"], grand["total"]),
        1,
    ):
        cell = ws.cell(row=row, column=c, value=val)
        cell.border = thin
        cell.font = _font(bold=True, color=COLOR_BURGUNDY)
        cell.fill = total_fill
        cell.alignment = center if c <= 2 else right
        if c == 3:
            cell.number_format = "#,##0"

    for i, w in enumerate((42, 14, 22), 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def generate_depenses_tableau_excel(
    depenses: Iterable,
    *,
    sheet_title: str = "Depenses",
    filtre_label: str = "",
    logo_path: str | None = None,
    company_name: str = "Avalon Pharma",
    split_by_month: bool = False,
    annee: int | None = None,
    mois: int | None = None,
) -> io.BytesIO:
    deps_list = list(depenses)
    if annee is None:
        annee = infer_annee_from_depenses(deps_list)
    titre_gen = titre_general_export(
        company_name=company_name,
        annee=annee,
        mois=mois if not split_by_month else None,
    )
    wb = openpyxl.Workbook()

    if split_by_month:
        groups = group_depenses_by_month(deps_list)
        default = wb.active
        wb.remove(default)
        if not groups:
            ws = wb.create_sheet(title=(sheet_title or "Depenses")[:31])
            _write_sheet(
                ws,
                [],
                filtre_label=filtre_label,
                logo_path=logo_path,
                company_name=company_name,
                titre_general=titre_gen,
            )
        else:
            if len(groups) > 1:
                syn = wb.create_sheet(title="Synthese", index=0)
                _write_synthese_sheet(
                    syn,
                    groups,
                    filtre_label=filtre_label,
                    company_name=company_name,
                    titre_general=titre_gen,
                    annee=annee,
                )
            for mois_num, facts in groups.items():
                title = sheet_title_mois(mois_num) if mois_num else "Sans date"
                y = annee or infer_annee_from_depenses(facts)
                titre_m = titre_periode_mois(mois_num, y) if mois_num else "Sans date"
                ws = wb.create_sheet(title=title)
                _write_sheet(
                    ws,
                    facts,
                    filtre_label=filtre_label,
                    logo_path=logo_path,
                    company_name=company_name,
                    titre_general=titre_gen,
                    titre_mois=titre_m,
                )
    else:
        ws = wb.active
        ws.title = (sheet_title or "Depenses")[:31]
        titre_m = titre_periode_mois(mois, annee) if mois else None
        _write_sheet(
            ws,
            deps_list,
            filtre_label=filtre_label,
            logo_path=logo_path,
            company_name=company_name,
            titre_general=titre_gen,
            titre_mois=titre_m,
        )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_filename(annee=None, mois=None, ext: str = "xlsx") -> str:
    parts = ["Depenses"]
    if annee:
        parts.append(str(annee))
    if mois:
        parts.append(f"{int(mois):02d}")
    parts.append(date.today().strftime("%Y%m%d"))
    return "_".join(parts) + f".{ext}"
