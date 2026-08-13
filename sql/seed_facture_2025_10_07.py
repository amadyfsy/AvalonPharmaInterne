#!/usr/bin/env python3
"""Ajoute la facture 2025/10/07 — CHR Thiès (BC 1000439)."""

from __future__ import annotations

import re
import sys
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NUMERO = "2025/10/07"
DATE_EMISSION = date(2025, 10, 27)
CLIENT_NAME = "CHR Thiès"
BC = "1000439"
LIGNES = [
    ("Robinet 3 voies", 2000, 140),
    ("Lame de delbet P/10", 100, 800),
    ("Electrode Cardiaque p/50", 344, 3000),
    ("Fil Antibactérienne", 300, 1820),
    ("Prolongateur 75 à 100 cm", 5000, 360),
    ("Nébuliseur", 15, 25000),
    ("Clamp Barre", 5000, 60),
]


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").upper()
    return text[:40] or "X"


def main() -> None:
    from app import create_app
    from app.extensions import db
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.produit import CategorieProduit, Produit
    from app.models.stock import Stock

    app = create_app()
    with app.app_context():
        if Facture.query.filter_by(numero=NUMERO).first():
            print(f"Déjà présente : {NUMERO}")
            return

        cat = CategorieProduit.query.filter_by(nom="Dispositifs médicaux").first()
        if not cat:
            cat = CategorieProduit(
                nom="Dispositifs médicaux",
                description="Consommables et équipements médicaux",
                code_formulaire="dispositifs",
            )
            db.session.add(cat)
            db.session.flush()

        client = None
        for c in Client.query.all():
            rs = (c.raison_sociale or "").lower()
            if "thiès" in rs or "thies" in rs:
                if "chr" in rs:
                    client = c
                    break
        if not client:
            code = "CLI-" + slugify(CLIENT_NAME)[:20]
            base = code
            n = 1
            while Client.query.filter_by(code=code).first():
                n += 1
                code = f"{base}-{n}"
            client = Client(
                code=code,
                raison_sociale=CLIENT_NAME,
                type_client="hopital",
                est_actif=True,
            )
            db.session.add(client)
            db.session.flush()
            print(f"  + client {CLIENT_NAME}")

        produits = {p.designation: p for p in Produit.query.all()}
        sous_total = Decimal("0")
        lignes_data = []
        for designation, qty, pu in LIGNES:
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
                print(f"  + produit {designation}")

            montant = money(Decimal(qty) * Decimal(pu))
            sous_total += montant
            lignes_data.append((produit, int(qty), money(pu), montant))

        total_ttc = money(sous_total)
        expected = money(4413000)
        if total_ttc != expected:
            print(f"Attention : total calculé {total_ttc} ≠ {expected}")

        facture = Facture(
            numero=NUMERO,
            client_id=client.id,
            date_emission=DATE_EMISSION,
            date_echeance=DATE_EMISSION + timedelta(days=30),
            bc=BC,
            remise_globale=Decimal("0"),
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
        db.session.commit()
        print(
            f"+ {NUMERO} | {client.raison_sociale} | BC {BC} | "
            f"{total_ttc:,.0f} FCFA | {DATE_EMISSION.isoformat()}"
        )


if __name__ == "__main__":
    main()
