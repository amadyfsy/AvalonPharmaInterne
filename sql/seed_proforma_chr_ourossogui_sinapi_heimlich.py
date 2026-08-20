#!/usr/bin/env python3
"""Crée un proforma CHR Ourossogui : 100 Sinapi + 22 valves Heimlich double.

Prix repris de l’historique Avalon :
  - Sinapi : 20 000 FCFA
  - Valves d'Heimlich double : 14 000 FCFA
  Total : 2 308 000 FCFA

Usage :
  python sql/seed_proforma_chr_ourossogui_sinapi_heimlich.py
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

CLIENT_NAME = "CHR Ourossogui"
LIGNES = [
    ("Sinapi", 100, 20000),
    ("Valves d'Heimlich double", 22, 14000),
]
TOTAL_ATTENDU = 2308000
NOTE_CLE = "seed:chr-ourossogui-sinapi-heimlich"


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
    wanted = _norm(CLIENT_NAME)
    for c in Client.query.all():
        rs = _norm(c.raison_sociale or "")
        if rs == wanted or ("ourossogui" in rs and "chr" in rs):
            return c
    return None


def find_produit(produits: dict, designation: str):
    if designation in produits:
        return produits[designation]
    key = _norm(designation)
    for existing, p in produits.items():
        if _norm(existing) == key:
            return p
    if key == "sinapi":
        for existing, p in produits.items():
            if "sinapi" in _norm(existing):
                return p
    if "heimlich" in key and "double" in key:
        for existing, p in produits.items():
            n = _norm(existing)
            if "heimlich" in n and "double" in n:
                return p
    return None


def prochain_numero_proforma(Proforma, annee: int) -> str:
    prefix = f"PROF-{annee}-"
    rows = (
        Proforma.query.filter(Proforma.numero.like(f"{prefix}%"))
        .with_entities(Proforma.numero)
        .all()
    )
    max_seq = 0
    for (num,) in rows:
        if not num or not num.startswith(prefix):
            continue
        try:
            max_seq = max(max_seq, int(num[len(prefix) :]))
        except ValueError:
            continue
    return f"{prefix}{max_seq + 1:04d}"


def main() -> None:
    from app import create_app
    from app.extensions import db
    from app.models.client import Client
    from app.models.produit import CategorieProduit, Produit
    from app.models.proforma import LigneProforma, Proforma
    from app.models.stock import Stock
    from app.models.user import User

    app = create_app()
    with app.app_context():
        existing = Proforma.query.filter(Proforma.notes.contains(NOTE_CLE)).first()
        if existing:
            print(f"Déjà présent : {existing.numero} (client {existing.client.raison_sociale if existing.client else '?'})")
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
                est_actif=True,
            )
            db.session.add(client)
            db.session.flush()
            print(f"  + client {CLIENT_NAME}")

        produits = {p.designation: p for p in Produit.query.all()}
        lignes_data = []
        sous_total = Decimal("0")
        for designation, qty, pu in LIGNES:
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
        if total_ttc != money(TOTAL_ATTENDU):
            print(f"  ⚠ total calculé {total_ttc} ≠ {TOTAL_ATTENDU}")

        today = date.today()
        user = User.query.order_by(User.id.asc()).first()
        numero = prochain_numero_proforma(Proforma, today.year)
        proforma = Proforma(
            numero=numero,
            client_id=client.id,
            date_emission=today,
            date_validite=today + timedelta(days=30),
            remise_globale=Decimal("0"),
            total_ht=total_ttc,
            tva_montant=Decimal("0"),
            total_ttc=total_ttc,
            statut="envoye",
            notes=f"{NOTE_CLE} | 100 Sinapi + 22 valves Heimlich double",
            commercial_id=user.id if user else None,
        )
        db.session.add(proforma)
        db.session.flush()
        for produit, qty, pu, montant in lignes_data:
            db.session.add(
                LigneProforma(
                    proforma_id=proforma.id,
                    produit_id=produit.id,
                    quantite=qty,
                    prix_unitaire_ht=pu,
                    remise=Decimal("0"),
                    montant_ht=montant,
                )
            )
        db.session.commit()
        print(f"  + {numero} | {CLIENT_NAME} | {total_ttc:,.0f} FCFA")
        print("Terminé.")


if __name__ == "__main__":
    main()
