#!/usr/bin/env python3
"""Ajoute les factures 2025/10/01 (OPK Ndiaye Sokone) et 2025/10/02 (CHR Saint-Louis).

Usage :
  python sql/seed_factures_2025_10_01_02.py
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
        "numero": "2025/10/01",
        "date": date(2025, 10, 6),
        "client": "OPK Ndiaye Sokone",
        "client_type": "autre",
        "lignes": [
            ("Microscope opératoire", 1, 1950000),
            ("Lampe à fente 5 steps", 1, 950000),
        ],
        "total_attendu": 2900000,
        "acompte": 2100000,
    },
    {
        "numero": "2025/10/02",
        "date": date(2025, 10, 2),
        "client": "CHR Saint-Louis",
        "client_aliases": ("CHR de Saint-Louis", "CHR Saint-Louis"),
        "client_type": "hopital",
        "bc": "01640",
        "lignes": [
            ("Bonnet", 300, 2000),
            ("Gant d'examen", 2000, 1800),
            ("Masque Chirurgie", 200, 2000),
            ("Pièce de Gaze", 300, 6500),
            ("Blouse non Stérile", 1000, 530),
        ],
        "total_attendu": 7080000,
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


def find_client(Client, name: str, aliases: tuple[str, ...] = ()):
    wanted = {_norm(name), *(_norm(a) for a in aliases)}
    for c in Client.query.all():
        if _norm(c.raison_sociale or "") in wanted:
            return c
    # Correspondance partielle uniquement si le nom demandé est bien ce client.
    name_n = _norm(name)
    if "saint" in name_n and "louis" in name_n:
        for c in Client.query.all():
            rs = _norm(c.raison_sociale or "")
            if "saint" in rs and "louis" in rs and ("chr" in rs or "hopital" in rs):
                return c
    if "opk" in name_n or "sokone" in name_n:
        for c in Client.query.all():
            rs = _norm(c.raison_sociale or "")
            if "opk" in rs or "sokone" in rs:
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
    return None


def main() -> None:
    from app import create_app
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
                if existing.client_id != client.id:
                    old = (existing.client.raison_sociale if existing.client else "?")
                    existing.client_id = client.id
                    for pay in PaiementClient.query.filter_by(facture_id=existing.id).all():
                        pay.client_id = client.id
                    for bl in BonLivraison.query.filter_by(facture_id=existing.id).all():
                        bl.client_id = client.id
                    print(f"  corrigé {numero} : {old} → {client.raison_sociale}")
                assurer_bl_pour_facture(existing, statut="livre")
                db.session.commit()
                print(f"  ok {numero} | {client.raison_sociale}")
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

            acompte = money(raw.get("acompte") or 0)
            if acompte < 0:
                acompte = Decimal("0")
            if acompte > total_ttc:
                acompte = total_ttc
            reste = money(total_ttc - acompte)
            if acompte <= 0:
                statut = "emise"
            elif reste <= 0:
                statut = "payee"
                reste = Decimal("0")
            else:
                statut = "partiellement_payee"

            d_emis = raw["date"]
            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=d_emis,
                date_echeance=d_emis + timedelta(days=30),
                bc=raw.get("bc"),
                remise_globale=Decimal("0"),
                total_ht=total_ttc,
                tva_montant=Decimal("0"),
                total_ttc=total_ttc,
                statut=statut,
                montant_paye=acompte,
                reste_a_payer=reste,
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
            if acompte > 0 and user:
                year = d_emis.year
                prefix = f"ENC-{year}-"
                rows = (
                    db.session.query(PaiementClient.reference)
                    .filter(PaiementClient.reference.like(f"{prefix}%"))
                    .all()
                )
                max_seq = 0
                for (ref,) in rows:
                    if not ref or not ref.startswith(prefix):
                        continue
                    try:
                        max_seq = max(max_seq, int(ref[len(prefix) :]))
                    except ValueError:
                        continue
                enc_ref = f"{prefix}{max_seq + 1:04d}"
                db.session.add(
                    PaiementClient(
                        client_id=client.id,
                        facture_id=facture.id,
                        reference=enc_ref,
                        montant=acompte,
                        mode_paiement="espece",
                        date_paiement=d_emis,
                        created_by=user.id,
                    )
                )
            assurer_bl_pour_facture(facture, statut="livre")
            created += 1
            extra = f" | acompte {acompte:,.0f} | reliquat {reste:,.0f}" if acompte else ""
            print(f"  + {numero} | {client.raison_sociale} | {total_ttc:,.0f} FCFA{extra}")

        db.session.commit()
        print(f"\nTerminé : {created} facture(s) ajoutée(s).")


if __name__ == "__main__":
    main()
