#!/usr/bin/env python3
"""Ajoute uniquement les factures 2025 manquantes (10/03, 10/04, 10/08, 10/09, 11/01)."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FACTURES = [
    {
        "numero": "2025/10/03",
        "date": date(2025, 10, 9),
        "client": "Tambedou TSO Touba",
        "lignes": [
            ("Table Motorisée", 1, 360000),
            ("Valise à monture de verres", 1, 100000),
        ],
    },
    {
        "numero": "2025/10/04",
        "date": date(2025, 10, 23),
        "client": "Hôpital Tivaouane",
        "lignes": [("Boîte d'amputation", 1, 350000)],
    },
    {
        "numero": "2025/10/08",
        "date": date(2025, 10, 27),
        "client": "Centre de Santé Keur Niang Touba",
        "lignes": [("Autoclave 18L", 1, 800000)],
        "remise_pct": Decimal("50"),
    },
    {
        "numero": "2025/10/09",
        "date": date(2025, 10, 29),
        "client": "Centre de Santé Keur Niang Touba",
        "lignes": [("Autoclave 18L", 1, 800000)],
    },
    {
        "numero": "2025/11/01",
        "date": date(2025, 11, 3),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Gants Stériles T 7,5", 300, 6500),
            ("Gants Stériles T 8", 150, 6500),
            ("Gants pour invasion utérine", 10, 32500),
            ("Trousse Universelle", 1200, 9860),
            ("Surgicel", 25, 13985),
            ("Kit de Fixation", 25, 10985),
        ],
    },
]


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def main() -> None:
    import re
    import unicodedata

    from app import create_app
    from app.extensions import db
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.produit import CategorieProduit, Produit
    from app.models.stock import Stock
    from app.utils.bl_from_facture import assurer_bl_pour_facture

    def slugify(text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").upper()
        return text[:40] or "X"

    app = create_app()
    with app.app_context():
        cat = CategorieProduit.query.filter_by(nom="Dispositifs médicaux").first()
        if not cat:
            cat = CategorieProduit(
                nom="Dispositifs médicaux",
                description="Consommables et équipements médicaux",
                code_formulaire="dispositifs",
            )
            db.session.add(cat)
            db.session.flush()

        clients = {c.raison_sociale: c for c in Client.query.all()}
        produits = {p.designation: p for p in Produit.query.all()}
        created = 0

        for raw in FACTURES:
            numero = raw["numero"]
            existing = Facture.query.filter_by(numero=numero).first()
            if existing:
                assurer_bl_pour_facture(existing, statut="livre")
                print(f"  skip {numero} (BL vérifié)")
                continue

            name = raw["client"]
            client = clients.get(name)
            if not client:
                # Réutilise un client proche si déjà créé sous un nom court
                for existing_name, c in clients.items():
                    if name.lower() in existing_name.lower() or existing_name.lower() in name.lower():
                        client = c
                        break
            if not client:
                low = name.lower()
                if "hôpital" in low or "hopital" in low or "chr" in low:
                    ctype = "hopital"
                elif "centre" in low:
                    ctype = "clinique"
                else:
                    ctype = "autre"
                code = "CLI-" + slugify(name)[:20]
                base = code
                n = 1
                while Client.query.filter_by(code=code).first():
                    n += 1
                    code = f"{base}-{n}"
                client = Client(
                    code=code, raison_sociale=name, type_client=ctype, est_actif=True
                )
                db.session.add(client)
                db.session.flush()
                clients[name] = client
                print(f"  + client {name}")

            sous_total = Decimal("0")
            lignes_data = []
            for designation, qty, pu in raw["lignes"]:
                produit = produits.get(designation)
                if not produit:
                    for existing, p in produits.items():
                        if existing.lower() == designation.lower():
                            produit = p
                            break
                if not produit:
                    ref = "PRD-" + slugify(designation)[:24]
                    base = ref
                    n = 1
                    while Produit.query.filter_by(reference=ref).first():
                        n += 1
                        ref = f"{base}-{n}"
                    pu_d = money(pu)
                    produit = Produit(
                        reference=ref,
                        designation=designation,
                        categorie_id=cat.id,
                        forme="dispositif",
                        unite="unité",
                        prix_achat_ht=money(pu_d * Decimal("0.7")),
                        prix_vente_ht=pu_d,
                        tva=Decimal("0"),
                        prix_vente_ttc=pu_d,
                        seuil_alerte_stock=5,
                        est_actif=True,
                    )
                    db.session.add(produit)
                    db.session.flush()
                    db.session.add(
                        Stock(produit_id=produit.id, quantite_disponible=1000, quantite_reservee=0)
                    )
                    produits[designation] = produit

                montant = money(Decimal(qty) * Decimal(pu))
                sous_total += montant
                lignes_data.append((produit, int(qty), money(pu), montant))

            remise = Decimal("0")
            remise_pct_store = Decimal("0")
            if raw.get("remise_pct"):
                remise_pct_store = Decimal(raw["remise_pct"])
                remise = money(sous_total * remise_pct_store / Decimal("100"))
            total_ttc = money(sous_total - remise)
            d_emis = raw["date"]
            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=d_emis,
                date_echeance=d_emis + timedelta(days=30),
                remise_globale=remise_pct_store,
                total_ht=total_ttc,
                tva_montant=Decimal("0"),
                total_ttc=total_ttc,
                statut="emise",
                montant_paye=Decimal("0"),
                reste_a_payer=total_ttc,
            )
            db.session.add(facture)
            db.session.flush()
            for produit, qty, pu, montant in lignes_data:
                db.session.add(
                    LigneFacture(
                        facture_id=facture.id,
                        produit_id=produit.id,
                        quantite=qty,
                        prix_unitaire_ht=pu,
                        remise=Decimal("0"),
                        montant_ht=montant,
                    )
                )
            db.session.flush()
            assurer_bl_pour_facture(facture, statut="livre")
            created += 1
            print(f"  + {numero} | {name} | {total_ttc:,.0f} FCFA")

        db.session.commit()
        print(f"\nTerminé : {created} facture(s) ajoutée(s).")


if __name__ == "__main__":
    main()
