#!/usr/bin/env python3
"""Ajoute les factures 2026/01/01 à 2026/01/05.

Usage (PythonAnywhere — activer le venv d'abord) :
  source ~/.virtualenvs/avalon-interne/bin/activate
  python sql/seed_factures_2026_01_01_05.py
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

FACTURES = [
    {
        "numero": "2026/01/01",
        "date": date(2026, 1, 14),
        "client": "RAJUNT DISTRIBUTION",
        "client_type": "grossiste",
        "lignes": [
            ("Valves d'Heimlich double", 20, 14000),
            ("Valves d'Heimlich Simple", 10, 8000),
        ],
        "total_attendu": 360000,
    },
    {
        "numero": "2026/01/02",
        "date": date(2026, 1, 14),
        "client": "HÔPITAL TIVAOUANE",
        "client_type": "hopital",
        "lignes": [
            ("Valves d'Heimlich double", 20, 14000),
        ],
        "total_attendu": 280000,
    },
    {
        "numero": "2026/01/03",
        "date": date(2026, 1, 14),
        "client": "HÔPITAL TIVAOUANE",
        "client_type": "hopital",
        "lignes": [
            ("Papier ECG 280*210 - 200 pages", 10, 18000),
            ("Papier ECG 295*210 - 100 pages", 10, 9000),
        ],
        "total_attendu": 270000,
    },
    {
        "numero": "2026/01/04",
        "date": date(2026, 1, 21),
        "client": "RAJUNT DISTRIBUTION",
        "client_type": "grossiste",
        "lignes": [
            ("Valves d'Heimlich Simple", 10, 8000),
        ],
        "total_attendu": 80000,
    },
    {
        "numero": "2026/01/05",
        "date": date(2026, 1, 23),
        "client": "HÔPITAL TIVAOUANE",
        "client_type": "hopital",
        "lignes": [
            ("Kit de Traction Adulte", 20, 5000),
            ("Kit de Traction Enfant", 10, 5000),
        ],
        "total_attendu": 150000,
    },
]

PRODUIT_ALIASES = {
    "valves d heimlich simple": (
        "Valves d'Heimlich simple",
        "Valves d'Heimlich Simple",
    ),
    "valves d heimlich double": (
        "Valves d'Heimlich double",
    ),
    "papier ecg 280 210 200 pages": (
        "Papier ECG 280x210 - 200 pages",
        "Papier ECG 280*210 - 200 pages",
    ),
    "papier ecg 295 210 100 pages": (
        "Papier ECG 295x210 - 100 pages",
        "Papier ECG 295*210 - 100 pages",
    ),
    "kit de traction adulte": (
        "Kit de traction adulte",
    ),
    "kit de traction enfant": (
        "Kit de traction enfant",
    ),
}


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


def find_client(Client, name: str, aliases: tuple[str, ...] = ()):
    wanted = {_norm(name), *(_norm(a) for a in aliases)}
    for c in Client.query.all():
        if _norm(c.raison_sociale or "") in wanted:
            return c
    name_n = _norm(name)
    if "tivaouane" in name_n:
        for c in Client.query.all():
            rs = _norm(c.raison_sociale or "")
            if "tivaouane" in rs:
                return c
    if "rajunt" in name_n:
        for c in Client.query.all():
            rs = _norm(c.raison_sociale or "")
            if "rajunt" in rs:
                return c
    return None


def get_or_create_client(Client, db, name: str, client_type: str, aliases: tuple[str, ...] = ()):
    client = find_client(Client, name, aliases)
    if client:
        return client
    code = "CLI-" + slugify(name)[:20]
    base = code
    n = 1
    while Client.query.filter_by(code=code).first():
        n += 1
        code = f"{base}-{n}"
    client = Client(
        code=code,
        raison_sociale=name,
        type_client=client_type or "autre",
        est_actif=True,
    )
    db.session.add(client)
    db.session.flush()
    print(f"  + client {name}")
    return client


def find_produit(produits: dict, designation: str):
    if designation in produits:
        return produits[designation]
    key = _norm(designation)
    for existing, p in produits.items():
        if _norm(existing) == key:
            return p
    alias_group = PRODUIT_ALIASES.get(key)
    if alias_group:
        wanted = {key, *(_norm(a) for a in alias_group)}
        for existing, p in produits.items():
            if _norm(existing) in wanted:
                return p
    return None


def main() -> None:
    try:
        from app import create_app
    except ModuleNotFoundError as exc:
        print(
            "Erreur : environnement Python incomplet.\n"
            "Sur PythonAnywhere :\n"
            "  source ~/.virtualenvs/avalon-interne/bin/activate\n"
            "  pip install -r requirements.txt\n"
            "  python sql/seed_factures_2026_01_01_05.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    from app.extensions import db
    from app.models.bon_livraison import BonLivraison
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.paiement_client import PaiementClient
    from app.models.produit import CategorieProduit, Produit
    from app.models.stock import Stock
    from app.models.user import User
    from app.utils.bl_from_facture import assurer_bl_pour_facture

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

        produits = {p.designation: p for p in Produit.query.all()}
        user = User.query.order_by(User.id.asc()).first()
        created = 0

        for raw in FACTURES:
            numero = raw["numero"]
            name = raw["client"]
            existing = Facture.query.filter_by(numero=numero).first()
            if existing:
                client = get_or_create_client(
                    Client,
                    db,
                    name,
                    raw.get("client_type") or "autre",
                    raw.get("client_aliases") or (),
                )
                changed = False
                if existing.client_id != client.id:
                    old = existing.client.raison_sociale if existing.client else "?"
                    existing.client_id = client.id
                    for pay in PaiementClient.query.filter_by(facture_id=existing.id).all():
                        pay.client_id = client.id
                    for bl in BonLivraison.query.filter_by(facture_id=existing.id).all():
                        bl.client_id = client.id
                    print(f"  corrigé {numero} : {old} → {client.raison_sociale}")
                    changed = True
                assurer_bl_pour_facture(existing, statut="livre")
                db.session.commit()
                print(
                    f"  ok {numero} | {client.raison_sociale}"
                    + (" (mise à jour)" if changed else " (déjà présente)")
                )
                continue

            client = get_or_create_client(
                Client,
                db,
                name,
                raw.get("client_type") or "autre",
                raw.get("client_aliases") or (),
            )

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
                print(f"  ⚠ {numero} total calculé {total_ttc} ≠ {attendu}")

            d_emis = raw["date"]
            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=d_emis,
                date_echeance=d_emis + timedelta(days=30),
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
            print(f"  + {numero} | {client.raison_sociale} | {total_ttc:,.0f} FCFA")

        db.session.commit()
        print(f"\nTerminé : {created} facture(s) ajoutée(s).")


if __name__ == "__main__":
    main()
