#!/usr/bin/env python3
"""
Renomme les numéros de factures au format FACT-YYYY-MM-NNNN (séquence mensuelle).

Cible : lignes dont le numéro commence par FACT- mais ne correspond pas déjà au
nouveau motif (ex. ancien FACT-2026-0001 → FACT-2026-05-0007 selon date d'émission).

Les préfixes hors FACT- (FAC-IMP-, etc.) ne sont pas modifiés.

Met à jour les libellés de dépenses du type « … (vente FACT-…) ».

Usage (racine projet, dossier avec config.py) :
  PYTHONPATH=. python GestAvalon/sql/migrate_factures_numero_format.py           # simulation
  PYTHONPATH=. python GestAvalon/sql/migrate_factures_numero_format.py --apply   # exécution
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

NEW_NUMERO = re.compile(r"^FACT-\d{4}-\d{2}-\d{4}$")


def needs_renumber(numero: str | None) -> bool:
    if not numero or not numero.startswith("FACT-"):
        return False
    return NEW_NUMERO.match(numero) is None


def _max_seq_new_format_month(y: int, m: int) -> int:
    from GestAvalon.app.extensions import db
    from GestAvalon.app.models.facture import Facture

    mx = 0
    rows = Facture.query.filter(
        db.extract("year", Facture.date_emission) == y,
        db.extract("month", Facture.date_emission) == m,
    ).all()
    for f in rows:
        if NEW_NUMERO.match(f.numero or ""):
            parts = (f.numero or "").split("-")
            if len(parts) >= 4 and parts[3].isdigit():
                mx = max(mx, int(parts[3]))
    return mx


def _collect_migration_plan():
    from GestAvalon.app.models.facture import Facture

    to_fix = [
        f
        for f in Facture.query.order_by(Facture.date_emission, Facture.id).all()
        if needs_renumber(f.numero)
    ]
    if not to_fix:
        return []

    from collections import defaultdict

    by_month: dict[tuple[int, int], list] = defaultdict(list)
    for f in to_fix:
        by_month[(f.date_emission.year, f.date_emission.month)].append(f)

    plan: list[tuple[int, str, str]] = []
    for key in sorted(by_month.keys()):
        y, m = key
        seq = _max_seq_new_format_month(y, m)
        for f in sorted(by_month[key], key=lambda x: x.id):
            seq += 1
            new_num = f"FACT-{y}-{m:02d}-{seq:04d}"
            plan.append((f.id, f.numero, new_num))
    return plan


def _update_depense_libelles(old: str, new: str) -> int:
    from GestAvalon.app.models.depense import Depense

    needle = f"(vente {old})"
    replacement = f"(vente {new})"
    n = 0
    for d in Depense.query.filter(Depense.libelle.contains(needle)).all():
        if needle in (d.libelle or ""):
            d.libelle = (d.libelle or "").replace(needle, replacement)
            n += 1
    return n


def run(apply_changes: bool) -> None:
    from GestAvalon.app import create_app
    from GestAvalon.app.extensions import db
    from GestAvalon.app.models.facture import Facture

    app = create_app("default")
    with app.app_context():
        plan = _collect_migration_plan()
        if not plan:
            print(
                "Aucune facture à migrer (déjà au format FACT-YYYY-MM-NNNN ou aucun ancien numéro FACT-)."
            )
            return

        print(f"{'APPLY' if apply_changes else 'DRY-RUN'} — {len(plan)} facture(s) concernée(s) :\n")
        for fid, old, new in plan:
            print(f"  id={fid}  {old!r}  →  {new!r}")

        if not apply_changes:
            print("\nRelancez avec --apply pour écrire en base.")
            return

        for fid, _old, _new in plan:
            f = db.session.get(Facture, fid)
            if f:
                f.numero = f"__MG{fid}__"
        db.session.flush()

        dep_updates = 0
        for fid, old, new in plan:
            f = db.session.get(Facture, fid)
            if not f:
                continue
            dep_updates += _update_depense_libelles(old, new)
            f.numero = new

        db.session.commit()
        print(
            f"\nTerminé : {len(plan)} facture(s) renommée(s), "
            f"{dep_updates} libellé(s) de dépense mis à jour."
        )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--apply",
        action="store_true",
        help="Appliquer les changements (sans cet argument : simulation seulement)",
    )
    args = p.parse_args()
    run(apply_changes=args.apply)


if __name__ == "__main__":
    main()
