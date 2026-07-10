"""Génération des références de dépenses (format N°26/06/19)."""
from __future__ import annotations

from datetime import date, datetime

from ..extensions import db
from ..models.depense import Depense


def _as_date(value: date | datetime | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    return value


def prochaine_reference_depense(date_depense: date | datetime | None = None) -> str:
    """
    Prochaine référence au format N°{année}/{mois}/{n° du mois}.
    Ex. N°26/06/19 — 26 = année en cours (2 ch.), 06 = mois, 19 = n° séquentiel du mois.
    """
    d = _as_date(date_depense)
    yy = d.year % 100
    mm = d.month
    prefix = f"N°{yy:02d}/{mm:02d}/"

    rows = (
        db.session.query(Depense.reference)
        .filter(Depense.reference.like(f"{prefix}%"))
        .all()
    )
    max_seq = 0
    for (ref,) in rows:
        if not ref or not ref.startswith(prefix):
            continue
        tail = ref[len(prefix) :]
        try:
            max_seq = max(max_seq, int(tail))
        except ValueError:
            continue
    return f"{prefix}{max_seq + 1}"
