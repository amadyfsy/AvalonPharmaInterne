#!/usr/bin/env python3
"""Audit / realignement des BL liés aux factures existantes.

Vérifie pour chaque facture non annulée :
  - présence d'un BL
  - même client / numéro (si possible)
  - mêmes quantités nettes d'avoirs

Usage — console Bash PythonAnywhere (compte DMS07) :

  NE PAS faire « source .env » : bash mange le $ du nom de base.
  dotenv charge .env correctement depuis Python.

  cd ~/AvalonPharmaInterne
  git pull
  unset DATABASE_URL MYSQL_USER MYSQL_PASSWORD MYSQL_HOST MYSQL_DATABASE
  ~/.virtualenvs/avalon-interne/bin/python sql/aligner_bl_factures_existantes.py
  ~/.virtualenvs/avalon-interne/bin/python sql/aligner_bl_factures_existantes.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(*, apply: bool = False, include_annulees: bool = False) -> int:
    from sqlalchemy.orm import joinedload

    from app import create_app
    from app.extensions import db
    from app.models.bon_livraison import BonLivraison
    from app.models.facture import Facture, LigneFacture
    from app.utils.bl_from_facture import aligner_bl_sur_facture, bl_est_desaligne

    app = create_app()
    with app.app_context():
        q = Facture.query.options(
            joinedload(Facture.lignes).joinedload(LigneFacture.produit),
            joinedload(Facture.client),
        ).order_by(Facture.date_emission.asc(), Facture.id.asc())
        if not include_annulees:
            q = q.filter(Facture.statut != "annulee")

        factures = q.all()
        bl_by_facture = {
            bl.facture_id: bl
            for bl in BonLivraison.query.options(
                joinedload(BonLivraison.lignes),
                joinedload(BonLivraison.client),
            ).filter(BonLivraison.facture_id.isnot(None)).all()
        }

        total = len(factures)
        ok = 0
        issues: list[tuple[Facture, BonLivraison | None, list[str]]] = []

        for f in factures:
            bl = bl_by_facture.get(f.id)
            desaligne, reasons = bl_est_desaligne(f, bl)
            if not desaligne:
                ok += 1
                continue
            issues.append((f, bl, reasons))

        print(f"Factures examinées : {total}")
        print(f"Alignées OK        : {ok}")
        print(f"À corriger         : {len(issues)}")
        print("-" * 72)

        for f, bl, reasons in issues:
            cli_f = (
                f.client.raison_sociale
                if f.client
                else f"id={f.client_id}"
            )
            if bl and bl.client:
                cli_bl = bl.client.raison_sociale
            elif bl:
                cli_bl = f"id={bl.client_id}"
            else:
                cli_bl = "—"
            bl_info = (
                f"BL {bl.numero} (statut={bl.statut}, client={cli_bl})"
                if bl
                else "aucun BL"
            )
            print(
                f"  {f.numero}  statut={f.statut}  "
                f"client={cli_f}  → {bl_info}"
            )
            for r in reasons:
                print(f"      - {r}")

        if not issues:
            print("Rien à faire : tous les BL sont alignés.")
            return 0

        if not apply:
            print("-" * 72)
            print("Mode audit uniquement. Relancez avec --apply pour corriger.")
            return 0

        print("-" * 72)
        print("Application des corrections…")
        fixed = 0
        for f, bl, _reasons in issues:
            aligner_bl_sur_facture(f, bl)
            fixed += 1
        db.session.commit()
        print(f"Corrigé : {fixed} facture(s).")

        # Re-vérif
        still = 0
        for f, _bl, _ in issues:
            db.session.refresh(f)
            bl2 = BonLivraison.query.options(
                joinedload(BonLivraison.lignes)
            ).filter_by(facture_id=f.id).first()
            desaligne, reasons = bl_est_desaligne(f, bl2)
            if desaligne:
                still += 1
                print(f"  ENCORE : {f.numero} → {', '.join(reasons)}")
        if still:
            print(f"Attention : {still} facture(s) encore désalignée(s) (ex. conflit de n° BL).")
            return 1
        print("Vérification post-correction : OK.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applique les corrections (sinon audit seul).",
    )
    parser.add_argument(
        "--include-annulees",
        action="store_true",
        help="Inclure aussi les factures annulées.",
    )
    args = parser.parse_args()
    raise SystemExit(run(apply=args.apply, include_annulees=args.include_annulees))


if __name__ == "__main__":
    main()
