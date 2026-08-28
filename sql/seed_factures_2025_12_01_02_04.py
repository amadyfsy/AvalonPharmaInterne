#!/usr/bin/env python3
"""Ajoute / resynchronise les factures 2025/12/01, 2025/12/02 et 2025/12/04.

Usage (PythonAnywhere — activer le venv d'abord) :
  source ~/.virtualenvs/avalon-interne/bin/activate
  python sql/seed_factures_2025_12_01_02_04.py
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
        "numero": "2025/12/01",
        "date": date(2025, 12, 10),
        "client": "Mme Sow",
        "client_type": "autre",
        "lignes": [
            ("Ballon respiration manuel", 1, 20000),
            ("Gants pour invasion utérine", 1, 30000),
            ("Drap d'accouchement avec poche de recueil post partum", 50, 3200),
        ],
        "total_attendu": 210000,
    },
    {
        "numero": "2025/12/02",
        "date": date(2025, 12, 15),
        "client": "Mme Sow",
        "client_type": "autre",
        "lignes": [
            ("Masque nébuliseur adulte", 30, 1200),
            ("Masque nébuliseur enfant", 18, 1200),
            ("Masque nébuliseur néonatal", 2, 1200),
        ],
        # 30*1200 + 18*1200 + 2*1200 = 60 000 (ligne « 22 600 » du document est une erreur de calcul)
        "total_attendu": 60000,
    },
    {
        "numero": "2025/12/04",
        "date": date(2025, 12, 18),
        "client": "CHR de Ndioum",
        "client_aliases": (
            "CHR de Ndioum",
            "Centre Hospitalier Régional de Ndioum",
            "CHR Ndioum",
        ),
        "client_type": "hopital",
        "lignes": [
            ("Déshumidificateur", 2, 250000),
        ],
        "total_attendu": 500000,
    },
]

PRODUIT_ALIASES = {
    "drap d accouchement avec poche de recueil post partum": (
        "Drap d'accouchement avec poche de recueil",
        "Drap d'accouchement avec poche de recueil post partum",
    ),
    "gants pour invasion uterine": (
        "Gants pour invasion utérine",
        "Gants pour invasion uterine",
    ),
    "masque nebuliseur neonatale": (
        "Masque nébuliseur néonatal",
        "Masque nébuliseur Néonatale",
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
    if "sow" in name_n:
        for c in Client.query.all():
            if "sow" in _norm(c.raison_sociale or ""):
                return c
    if "ndioum" in name_n:
        for c in Client.query.all():
            if "ndioum" in _norm(c.raison_sociale or ""):
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


def resolve_lignes(raw, produits, cat, db):
    from app.models.produit import Produit
    from app.models.stock import Stock

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
    return lignes_data, money(sous_total)


def apply_facture(facture, client, raw, lignes_data, total_ttc, LigneFacture, db):
    d_emis = raw["date"]
    facture.client_id = client.id
    facture.date_emission = d_emis
    facture.date_echeance = d_emis + timedelta(days=30)
    facture.remise_globale = Decimal("0")
    facture.total_ht = total_ttc
    facture.tva_montant = Decimal("0")
    facture.total_ttc = total_ttc

    mp = float(facture.montant_paye or 0)
    if mp <= 0:
        facture.montant_paye = Decimal("0")
        facture.reste_a_payer = total_ttc
        facture.statut = "emise"
    else:
        reste = max(0.0, float(total_ttc) - mp)
        facture.reste_a_payer = money(reste)
        if reste <= 0.001:
            facture.reste_a_payer = Decimal("0")
            facture.statut = "payee"
        else:
            facture.statut = "partiellement_payee"

    LigneFacture.query.filter_by(facture_id=facture.id).delete(synchronize_session=False)
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


def sync_bl(facture, raw_date):
    from app.utils.bl_from_facture import _ecrire_lignes_bl, assurer_bl_pour_facture

    bl = assurer_bl_pour_facture(facture, statut="livre", date_livraison=raw_date)
    if bl:
        bl.client_id = facture.client_id
        bl.date_livraison = raw_date
        bl.statut = "livre"
        _ecrire_lignes_bl(facture, bl, livre=True)
    return bl


def main() -> None:
    try:
        from app import create_app
    except ModuleNotFoundError as exc:
        print(
            "Erreur : environnement Python incomplet.\n"
            "Sur PythonAnywhere :\n"
            "  source ~/.virtualenvs/avalon-interne/bin/activate\n"
            "  pip install -r requirements.txt\n"
            "  python sql/seed_factures_2025_12_01_02_04.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    from app.extensions import db
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.paiement_client import PaiementClient
    from app.models.produit import CategorieProduit

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

        from app.models.produit import Produit

        produits = {p.designation: p for p in Produit.query.all()}
        created = 0
        repaired = 0

        for raw in FACTURES:
            numero = raw["numero"]
            name = raw["client"]
            client = get_or_create_client(
                Client,
                db,
                name,
                raw.get("client_type") or "autre",
                raw.get("client_aliases") or (),
            )
            lignes_data, total_ttc = resolve_lignes(raw, produits, cat, db)
            attendu = money(raw["total_attendu"])
            if total_ttc != attendu:
                print(f"  ⚠ {numero} total calculé {total_ttc} ≠ {attendu}")

            existing = Facture.query.filter_by(numero=numero).first()
            if existing:
                old_client = existing.client.raison_sociale if existing.client else "?"
                old_total = float(existing.total_ttc or 0)
                apply_facture(existing, client, raw, lignes_data, total_ttc, LigneFacture, db)
                for pay in PaiementClient.query.filter_by(facture_id=existing.id).all():
                    pay.client_id = client.id
                sync_bl(existing, raw["date"])
                repaired += 1
                note = ""
                if _norm(old_client) != _norm(client.raison_sociale):
                    note = f" client {old_client} → {client.raison_sociale}"
                if abs(old_total - float(total_ttc)) > 0.5:
                    note += f" total {old_total:,.0f} → {float(total_ttc):,.0f}"
                print(
                    f"  ↻ {numero} | {client.raison_sociale} | {total_ttc:,.0f} FCFA"
                    f"{note or ' (resynchronisée)'}"
                )
                continue

            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=raw["date"],
                date_echeance=raw["date"] + timedelta(days=30),
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
            apply_facture(facture, client, raw, lignes_data, total_ttc, LigneFacture, db)
            sync_bl(facture, raw["date"])
            created += 1
            print(f"  + {numero} | {client.raison_sociale} | {total_ttc:,.0f} FCFA")

        db.session.commit()
        print(f"\nTerminé : {created} créée(s), {repaired} resynchronisée(s).")


if __name__ == "__main__":
    main()
