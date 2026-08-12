"""Numérotation commune factures / BL : YYYY/MM/NN (ex. 2026/06/02)."""

from __future__ import annotations

import re
from datetime import date

from ..models.bon_livraison import BonLivraison
from ..models.facture import Facture

_NUMERO_RE = re.compile(r"^(\d{4})/(\d{2})/(\d+)$")


def parse_numero_seq(numero: str | None) -> tuple[int, int, int] | None:
    """Retourne (année, mois, séquence) si le numéro est au format YYYY/MM/NN."""
    if not numero:
        return None
    m = _NUMERO_RE.match(numero.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def format_numero(y: int, m: int, seq: int) -> str:
    """Formate un numéro document (séquence sur 2 chiffres min.)."""
    return f"{y}/{m:02d}/{seq:02d}" if seq < 100 else f"{y}/{m:02d}/{seq}"


def _numeros_utilises_mois(y: int, m: int) -> set[str]:
    prefix = f"{y}/{m:02d}/"
    used: set[str] = set()
    for (num,) in (
        Facture.query.filter(Facture.numero.like(f"{prefix}%"))
        .with_entities(Facture.numero)
        .all()
    ):
        if num:
            used.add(num)
    for (num,) in (
        BonLivraison.query.filter(BonLivraison.numero.like(f"{prefix}%"))
        .with_entities(BonLivraison.numero)
        .all()
    ):
        if num:
            used.add(num)
    return used


def _max_seq_mois(y: int, m: int, exclude_facture_id=None, exclude_bl_id=None) -> int:
    mx = 0
    fq = Facture.query.filter(Facture.numero.like(f"{y}/{m:02d}/%"))
    if exclude_facture_id is not None:
        fq = fq.filter(Facture.id != exclude_facture_id)
    for f in fq.all():
        parsed = parse_numero_seq(f.numero)
        if parsed and parsed[0] == y and parsed[1] == m:
            mx = max(mx, parsed[2])

    bq = BonLivraison.query.filter(BonLivraison.numero.like(f"{y}/{m:02d}/%"))
    if exclude_bl_id is not None:
        bq = bq.filter(BonLivraison.id != exclude_bl_id)
    for b in bq.all():
        parsed = parse_numero_seq(b.numero)
        if parsed and parsed[0] == y and parsed[1] == m:
            mx = max(mx, parsed[2])
    return mx


def prochain_numero_document(
    d: date,
    *,
    exclude_facture_id=None,
    exclude_bl_id=None,
) -> str:
    """
    Prochain numéro libre au format YYYY/MM/NN pour le mois de ``d``.

    La séquence est partagée entre factures et BL pour éviter les collisions
    (un couple facture+BL partage ensuite le même numéro).
    """
    y, m = d.year, d.month
    seq = _max_seq_mois(y, m, exclude_facture_id, exclude_bl_id) + 1
    # Garde-fou si un trou / format mixte laisse un numéro déjà pris
    used = _numeros_utilises_mois(y, m)
    while format_numero(y, m, seq) in used:
        seq += 1
    return format_numero(y, m, seq)


def numero_bl_pour_facture(facture: Facture) -> str:
    """Le BL lié à une facture reprend exactement le numéro de la facture."""
    return (facture.numero or "").strip()
