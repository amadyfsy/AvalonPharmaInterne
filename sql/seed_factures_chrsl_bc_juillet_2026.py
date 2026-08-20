#!/usr/bin/env python3
"""Importe les 2 bons de commande CHRSL (PDF Avalon Pharma) en factures.

BC 0000517 du 28/07/2026 — 2 363 000 FCFA
BC 0000657 du 30/07/2026 — 6 090 000 FCFA

Usage :
  python sql/seed_factures_chrsl_bc_juillet_2026.py
"""
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

CLIENT_NAME = "CHR Saint-Louis"
CLIENT_ALIASES = (
    "CHR de Saint-Louis",
    "CHR Saint-Louis",
    "Centre Hospitalier Regional Lt. Colonel Mamadou Diouf de Saint Louis",
)

FACTURES = [
    {
        "bc": "0000517",
        "date_bc": date(2026, 7, 28),
        "date_emission": date(2026, 7, 28),
        "ref_proforma": "F/0348/25 du 25/11/25",
        "total_attendu": 2363000,
        "lignes": [
            ("Lame de delbet 25x25", 100, 7000),
            ("Drain de Penrose", 100, 7000),
            ("Kit ponction Péricardique", 5, 16000),
            ("Kit de ponction pleurale", 5, 16000),
            ("Ballon de ventilation enfant", 16, 6000),
            ("Ballon de ventilation néonatal", 16, 6000),
            ("Pince de Magill pte taille", 10, 8500),
            ("Kit voie intra osseuse péd", 30, 10000),
            ("Sonde rectale n° 10", 10, 400),
            ("Kit de ponction lombaire", 5, 16000),
            ("Aiguille ponction lombaire 22G", 100, 500),
            ("Aiguille ponction lombaire 25G", 100, 500),
            ("Sonde vésicale 4", 30, 350),
            ("Sonde vésicale 6", 30, 350),
            ("Sonde vésicale 8", 30, 350),
            ("Sonde vésicale 10", 30, 350),
        ],
    },
    {
        "bc": "0000657",
        "date_bc": date(2026, 7, 30),
        "date_emission": date(2026, 7, 30),
        "ref_proforma": "F/005/26 du 07/07/26",
        "total_attendu": 6090000,
        "lignes": [
            ("Coton hydrophile", 1000, 2800),
            ("Pièces de gaze", 500, 6500),
            ("Masque Chirurgical", 20, 2000),
        ],
    },
]


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").upper()
    return text[:40] or "X"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def find_client(Client):
    wanted = {_norm(CLIENT_NAME), *(_norm(a) for a in CLIENT_ALIASES)}
    for c in Client.query.all():
        if _norm(c.raison_sociale or "") in wanted:
            return c
    for c in Client.query.all():
        rs = _norm(c.raison_sociale or "")
        if "saint" in rs and "louis" in rs and ("chr" in rs or "hopital" in rs or "diouf" in rs):
            return c
    return None


def find_produit(produits: dict, designation: str):
    if designation in produits:
        return produits[designation]
    key = _norm(designation)
    for existing, p in produits.items():
        if _norm(existing) == key:
            return p
    # aliases proches
    aliases = {
        "pieces de gaze": ("piece de gaze", "pièce de gaze", "pièces de gaze"),
        "masque chirurgical": ("masque chirurgie", "masque chirurgical b 50"),
    }
    for group in aliases.values():
        if key in {_norm(x) for x in group} or key == _norm(group[0]):
            for existing, p in produits.items():
                if _norm(existing) in {_norm(x) for x in group}:
                    return p
    return None


def main() -> None:
    from app import create_app
    from app.extensions import db
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.produit import CategorieProduit, Produit
    from app.models.stock import Stock
    from app.utils.bl_from_facture import assurer_bl_pour_facture
    from app.utils.document_numero import prochain_numero_document

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

        client = find_client(Client)
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
                telephone="+221 33 938 24 00",
                email="hpsl@orange.sn",
                adresse="BP 401 Saint-Louis",
                ville="Saint-Louis",
                est_actif=True,
            )
            db.session.add(client)
            db.session.flush()
            print(f"  + client {CLIENT_NAME}")

        produits = {p.designation: p for p in Produit.query.all()}
        created = 0

        for raw in FACTURES:
            bc = raw["bc"]
            existing = Facture.query.filter_by(bc=bc, client_id=client.id).first()
            if existing:
                existing.date_bc = raw["date_bc"]
                assurer_bl_pour_facture(existing, statut="livre")
                db.session.commit()
                print(f"  skip BC {bc} → facture {existing.numero} (date BC à jour)")
                continue

            sous_total = Decimal("0")
            lignes_data = []
            for designation, qty, pu in raw["lignes"]:
                produit = find_produit(produits, designation)
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
                        Stock(
                            produit_id=produit.id,
                            quantite_disponible=1000,
                            quantite_reservee=0,
                        )
                    )
                    produits[designation] = produit
                    print(f"  + produit {designation}")

                montant = money(Decimal(qty) * Decimal(pu))
                sous_total += montant
                lignes_data.append((produit, int(qty), money(pu), montant))

            total_ttc = money(sous_total)
            attendu = money(raw["total_attendu"])
            if total_ttc != attendu:
                print(f"  ⚠ BC {bc} total calculé {total_ttc} ≠ {attendu}")

            d_emis = raw["date_emission"]
            numero = prochain_numero_document(d_emis)
            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=d_emis,
                date_echeance=d_emis + timedelta(days=30),
                bc=bc,
                date_bc=raw["date_bc"],
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
            db.session.flush()
            assurer_bl_pour_facture(facture, statut="livre")
            created += 1
            print(
                f"  + {numero} | BC {bc} du {raw['date_bc'].strftime('%d/%m/%Y')} "
                f"| {total_ttc:,.0f} FCFA"
            )

        # Corrige aussi 2025/10/02 si présente sans date BC
        f1002 = Facture.query.filter_by(numero="2025/10/02").first()
        if f1002 and f1002.bc and not f1002.date_bc:
            f1002.date_bc = date(2025, 9, 19)
            print("  corrigé 2025/10/02 : date BC 19/09/2025")

        db.session.commit()
        print(f"\nTerminé : {created} facture(s) créée(s).")


if __name__ == "__main__":
    main()
