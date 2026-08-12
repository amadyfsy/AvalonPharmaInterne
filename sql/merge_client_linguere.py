#!/usr/bin/env python3
"""Fusionne « Hôpital Linguère » dans « CH Maguette Lo de Linguère »."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CANONICAL = "CH Maguette Lo de Linguère"
DUPLICATES = (
    "Hôpital Linguère",
    "Hopital Linguère",
    "Hôpital Linguere",
    "Hopital Linguere",
    "C H Magatte Lo de Linguère",
    "CH Magatte Lo de Linguère",
    "Centre Hospitalier Maguette Lo de Linguere",
)


def main() -> None:
    from app import create_app
    from app.extensions import db
    from app.models.bon_livraison import BonLivraison
    from app.models.client import Client
    from app.models.facture import Facture
    from app.models.paiement_client import PaiementClient
    from app.models.proforma import Proforma

    app = create_app()
    with app.app_context():
        keep = Client.query.filter_by(raison_sociale=CANONICAL).first()
        if not keep:
            # Prendre le premier doublon comme base et le renommer
            for name in DUPLICATES:
                keep = Client.query.filter_by(raison_sociale=name).first()
                if keep:
                    keep.raison_sociale = CANONICAL
                    db.session.flush()
                    print(f"Renommé → {CANONICAL} (id={keep.id})")
                    break
        if not keep:
            print("Aucun client Linguère trouvé.")
            return

        merged = 0
        for name in DUPLICATES:
            other = Client.query.filter_by(raison_sociale=name).first()
            if not other or other.id == keep.id:
                continue
            n_f = Facture.query.filter_by(client_id=other.id).update(
                {"client_id": keep.id}, synchronize_session=False
            )
            n_bl = BonLivraison.query.filter_by(client_id=other.id).update(
                {"client_id": keep.id}, synchronize_session=False
            )
            n_pf = Proforma.query.filter_by(client_id=other.id).update(
                {"client_id": keep.id}, synchronize_session=False
            )
            n_pay = PaiementClient.query.filter_by(client_id=other.id).update(
                {"client_id": keep.id}, synchronize_session=False
            )
            db.session.delete(other)
            merged += 1
            print(
                f"Fusionné « {name} » (id={other.id}) → id={keep.id} "
                f"[factures={n_f}, BL={n_bl}, proformas={n_pf}, paiements={n_pay}]"
            )

        db.session.commit()
        facts = Facture.query.filter_by(client_id=keep.id).order_by(Facture.numero).all()
        print(f"\nClient unique : {keep.raison_sociale} (id={keep.id})")
        for f in facts:
            print(f"  - {f.numero}")
        print(f"Doublons fusionnés : {merged}")


if __name__ == "__main__":
    main()
