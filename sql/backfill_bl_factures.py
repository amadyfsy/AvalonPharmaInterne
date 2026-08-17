#!/usr/bin/env python3
"""Crée un BL pour chaque facture qui n'en a pas encore.

Les factures historiques (émises / payées, date passée) reçoivent un BL « livré ».
Les brouillons et factures du jour restent en BL « préparé ».

Usage (depuis GestAvalon) :
  python sql/backfill_bl_factures.py
  python sql/backfill_bl_factures.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from app import create_app
    from app.extensions import db
    from app.models.bon_livraison import BonLivraison
    from app.models.facture import Facture
    from app.utils.bl_from_facture import assurer_bl_pour_facture

    app = create_app()
    with app.app_context():
        from datetime import date, timedelta

        factures = Facture.query.order_by(Facture.date_emission.asc(), Facture.id.asc()).all()
        created = 0
        already = 0
        cutoff = date.today() - timedelta(days=30)
        for facture in factures:
            existed = BonLivraison.query.filter_by(facture_id=facture.id).first() is not None
            d = facture.date_emission or date.today()
            statut = None
            if (
                facture.statut in ("emise", "partiellement_payee", "payee")
                and d < cutoff
            ):
                statut = "livre"
            bl = assurer_bl_pour_facture(facture, statut=statut) if statut else assurer_bl_pour_facture(facture)
            if existed:
                already += 1
            else:
                created += 1
                print(f"  + BL {bl.numero} ({bl.statut}) ← facture {facture.numero}")
        if args.dry_run:
            db.session.rollback()
            print(f"\n[DRY-RUN] {created} BL auraient été créés, {already} déjà présents.")
        else:
            db.session.commit()
            print(f"\nTerminé : {created} BL créés, {already} déjà présents.")


if __name__ == "__main__":
    main()
