#!/usr/bin/env python3
"""Ajoute les factures 2025 manquantes (Excel 2025_EXTD + Pro Pharma).

Anti-doublons : skip si numero existe, ou meme date + client + montant.
Reutilise clients/produits existants ; ne cree un produit que s'il est absent.
Cree aussi les BL associes.

Usage — console Bash PythonAnywhere (compte DMS07) :

  cd ~/AvalonPharmaInterne
  unset DATABASE_URL MYSQL_USER MYSQL_PASSWORD MYSQL_HOST MYSQL_DATABASE
  set -a && source .env && set +a
  ~/.virtualenvs/avalon-interne/bin/python sql/seed_factures_2025_excel_manquantes.py --dry-run
  ~/.virtualenvs/avalon-interne/bin/python sql/seed_factures_2025_excel_manquantes.py
"""
from __future__ import annotations

import argparse
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
        "numero": '2025/01/004',
        "date": date(2025, 1, 7),
        "client": 'CHR Thiès',
        "lignes": [
            ('Masque à haute concentration', 1000, 1000),
            ('Robinet 3 voies', 2500, 140),
            ('Prolongateur 75 à 100 cm', 2500, 360),
            ('Lame de bistouri n°10', 100, 800),
            ('Electrode Cardiaque p/50', 200, 3000),
            ('Manche de bistouri', 10, 3500),
            ('Lame de bistouri n°22 8/100', 500, 2800),
            ('Lame de bistouri n°11 8/100', 50, 2800),
            ('Filament hémostatique', 300, 1820),
            ('Masque à oxygène', 2000, 450),
            ('Pansement ERS 50/70', 200, 8000),
        ],
        "total_attendu": 7551000,
    },
    {
        "numero": '2025/01/148',
        "date": date(2025, 1, 27),
        "client": 'Inspection Médicale Scolaire Saint-Louis',
        "lignes": [
            ('Electrocardiographe contec 1200G 12 PISTE', 1, 650000),
        ],
        "total_attendu": 650000,
    },
    {
        "numero": '2025/02/002',
        "date": date(2025, 2, 5),
        "client": 'CHR Thiès',
        "lignes": [
            ('Robinet 3 voies', 2500, 140),
            ('Prolongateur 75 à 100 cm', 2500, 360),
            ('Masque à oxygène', 2000, 450),
        ],
        "total_attendu": 2150000,
    },
    {
        "numero": '2025/02/3B',
        "date": date(2025, 2, 24),
        "client": 'Hôpital Tivaouane',
        "lignes": [
            ('Papier ECG 295x210 - 100 pages', 20, 9000),
            ('Papier ECG 140x210 - 100 feuilles', 20, 8000),
            ('Papier ECG 110x140 - 100 feuilles', 20, 8000),
            ('Rouleau sachets stérilisation 40cm x 200m', 1, 96000),
        ],
        "total_attendu": 596000,
    },
    {
        "numero": '2025/03/16C',
        "date": date(2025, 3, 26),
        "client": 'Inspection Médicale Scolaire Saint-Louis',
        "lignes": [
            ('Rouleau papier ECG 210mm x 20m', 10, 8500),
        ],
        "total_attendu": 85000,
    },
    {
        "numero": '2025/03/7D',
        "date": date(2025, 3, 31),
        "client": 'Hôpital Tivaouane',
        "lignes": [
            ('Kit circuit respiratoire anesthésie pédiatre/néonatal', 30, 10000),
        ],
        "total_attendu": 300000,
    },
    {
        "numero": '2025/04/01',
        "date": date(2025, 4, 7),
        "client": 'CHR Saint-Louis',
        "lignes": [
            ('Masque chirurgical B/50', 200, 2000),
            ('Bonnet S/100', 150, 2000),
        ],
        "total_attendu": 700000,
    },
    {
        "numero": '2025/04/19D',
        "date": date(2025, 4, 28),
        "client": 'Hôpital Tivaouane',
        "lignes": [
            ('Pièce de gaze (unité)', 60, 6500),
            ('Coton hydrophile', 60, 1400),
            ('Couvre-chaussure S/100', 30, 2000),
        ],
        "total_attendu": 534000,
    },
    {
        "numero": '2025/05/012',
        "date": date(2025, 5, 13),
        "client": 'CHR Saint-Louis',
        "lignes": [
            ('Pièce de gaze (unité)', 900, 6500),
            ('Coton hydrophile', 500, 2800),
            ('Bonnet S/100', 50, 2000),
        ],
        "total_attendu": 7350000,
    },
    {
        "numero": '2025/06/43',
        "date": date(2025, 6, 2),
        "client": 'Demba Thioubou',
        "lignes": [
            ('Autoclave 18L', 1, 880000),
        ],
        "total_attendu": 880000,
    },
    {
        "numero": '2025/06/017-1',
        "date": date(2025, 6, 27),
        "client": 'CHR Saint-Louis',
        "lignes": [
            ('Soft bande', 498, 300),
            ('Bande de crêpe 10 cm', 2052, 300),
            ('Bande de crêpe 15 cm', 885, 400),
        ],
        "total_attendu": 1119000,
    },
    {
        "numero": '2025/06/017-2',
        "date": date(2025, 6, 27),
        "client": 'CHR Saint-Louis',
        "lignes": [
            ('Masque chirurgical B/50', 624, 2000),
            ('Coton hydrophile', 188, 2800),
            ('Bonnet S/100', 50, 2000),
            ('Couvre-chaussure S/100', 375, 1000),
        ],
        "total_attendu": 2249400,
    },
    {
        "numero": '2025/06/017-3',
        "date": date(2025, 6, 27),
        "client": 'CHR Saint-Louis',
        "lignes": [
            ('Soft bande', 498, 300),
            ('Bande de crêpe 10 cm', 1800, 300),
            ('Bande de crêpe 15 cm', 1000, 400),
        ],
        "total_attendu": 1089400,
    },
    {
        "numero": '2025/07/53',
        "date": date(2025, 7, 11),
        "client": 'Demba Thioubou',
        "lignes": [
            ('Lampe remplacement microscope', 1, 120000),
            ('Logiciel vision chart', 1, 120000),
            ('Autoclave 18L', 1, 880000),
        ],
        "total_attendu": 1120000,
    },
    {
        "numero": '2025/07/007',
        "date": date(2025, 7, 24),
        "client": 'Hôpital Tivaouane',
        "lignes": [
            ('Bulbe ECG', 10, 35000),
            ('Clamp ECG', 10, 25000),
            ('Implant', 38, 5000),
        ],
        "total_attendu": 790000,
    },
    {
        "numero": '2025/08/018',
        "date": date(2025, 8, 10),
        "client": 'CHR Diourbel',
        "lignes": [
            ('Boîte de bandelettes fluorescéine', 5, 16000),
        ],
        "total_attendu": 80000,
    },
    {
        "numero": '2025/08/02',
        "date": date(2025, 8, 25),
        "client": 'Pro Pharma',
        "lignes": [
            ('Transducer mono channel', 60, 41800),
            ('Transducer dual channel', 144, 51800),
        ],
        "total_attendu": 9967200,
    },
    {
        "numero": '2025/09/106',
        "date": date(2025, 9, 17),
        "client": 'Clinique medical de Tivaouane',
        "lignes": [
            ('Boîte césarienne', 1, 470000),
            ('Set laparotomie', 1, 385000),
            ('Boîte courante', 2, 65000),
        ],
        "total_attendu": 985000,
    },
    {
        "numero": '2025/09/107',
        "date": date(2025, 9, 17),
        "client": 'Hôpital Tivaouane',
        "lignes": [
            ('Sachet de stérilisation 400mm x 200', 1, 68000),
            ('Sachet de stérilisation 75mm x 200', 1, 18000),
        ],
        "total_attendu": 86000,
    },
    {
        "numero": '2025/09/004',
        "date": date(2025, 9, 23),
        "client": 'Hôpital Tivaouane',
        "lignes": [
            ("Drap d'accouchement avec poche de recueil", 50, 3500),
        ],
        "total_attendu": 175000,
    },
    {
        "numero": '2025/09/05',
        "date": date(2025, 9, 23),
        "client": 'CHR de Ndioum',
        "lignes": [
            ('Boîte de bandelettes fluorescéine', 5, 36000),
        ],
        "total_attendu": 180000,
    },
    {
        "numero": '2025/11/08',
        "date": date(2025, 11, 27),
        "client": 'Hôpital Tivaouane',
        "note": 'Excel 2025/11/703',
        "lignes": [
            ('Gants stériles T 7,5', 2000, 150),
            ("Drap d'accouchement avec poche de recueil", 250, 3500),
        ],
        "total_attendu": 1175000,
    },
]

# designation Excel/curated -> désignations catalogue acceptées
PRODUIT_ALIASES = {
    "robinet 3 voies": ("Robinet 3 voies",),
    "prolongateur 75 a 100 cm": ("Prolongateur 75 à 100 cm",),
    "electrode cardiaque p 50": ("Electrode Cardiaque p/50",),
    "lame de bistouri n 10": ("Lame de bistouri",),
    "lame de bistouri n 22 8 100": ("Lame de bistouri",),
    "lame de bistouri n 11 8 100": ("Lame de bistouri",),
    "filament hemostatique": ("Fil Antibactérienne",),
    "masque a oxygene": ("Masque á oxigene Adult", "Masque á oxigene enfant"),
    "electrocardiographe contec 1200g 12 piste": (
        "Appareil ECG (12 pistes Contec 1212G ou 1200)",
        "Appareil ECG 12 pistes Contec 1212G ou 1200",
        "Appareil ECG",
    ),
    "papier ecg 295x210 100 pages": ("Papier ECG 295x210 - 100 pages",),
    "rouleau papier ecg 210mm x 20m": ("Rouleau papier ECG 210mm x 20m",),
    "masque chirurgical b 50": ("Masque chirurgical B/50", "Masque Chirurgical"),
    "bonnet s 100": ("Bonnet S/100", "Bonnet"),
    "piece de gaze unite": ("Pièce de gaze (unité)", "Pièce de Gaze"),
    "coton hydrophile": ("Coton hydrophile",),
    "couvre chaussure s 100": ("Couvre-chaussure S/100",),
    "autoclave 18l": ("Autoclave 18L", "Autoclave de table", "Autoclave"),
    "bande de crepe 10 cm": ("Bande de crêpe 10 cm",),
    "logiciel vision chart": ("Tableau AV ou Logiciel",),
    "implant": ("Implant",),
    "boite de bandelettes fluoresceine": ("Boîte de bandelettes fluorescéine",),
    "boite cesarienne": ("Set césarienne", "Boîte césarienne"),
    "set laparotomie": ("Set laparotomie",),
    "drap d accouchement avec poche de recueil": (
        "Drap d'accouchement avec poche de recueil",
        "Drap d'accouchement avec poche de recueil post partum",
    ),
    "gants steriles t 7 5": ("Gants stériles T 7,5", "Gants Stériles T 7,5"),
}

CLIENT_ALIASES = {
    "CHR Thiès": ("CHR Thiès", "CHR Thies", "Centre Hospitalier Régional de Thiès"),
    "Inspection Médicale Scolaire Saint-Louis": (
        "Inspection Médicale Scolaire Saint-Louis",
        "Inspection Médicale de st louis",
        "Inspection medical de Ecoles de saint louis",
    ),
    "Hôpital Tivaouane": (
        "Hôpital Mame Abdou Aziz Sy Dabakh de Tivaouane",
        "Hôpital Tivaouane",
        "Hopital Tivaouane",
        "HOPITAL TIVAOUANE",
    ),
    "CHR Saint-Louis": ("CHR Saint-Louis", "CHR de Saint-Louis", "Centre Hospitalier Régional de Saint Louis"),
    "Demba Thioubou": ("Demba Thioubou", "Cabinet Demba Thioubou", "Cabinet Demba THIOUBOU"),
    "CHR Diourbel": ("CHR Diourbel", "Centre Hospitalier Régional de Diourbel"),
    "Pro Pharma": ("Pro Pharma",),
    "CHR de Ndioum": ("CHR de Ndioum", "CHR Ndioum", "Centre Hospitalier Régional de Ndioum"),
    "Clinique medical de Tivaouane": ("Clinique medical de Tivaouane",),
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


def find_client(Client, key: str):
    aliases = CLIENT_ALIASES.get(key, (key,))
    wanted = {_norm(a) for a in aliases}
    for c in Client.query.all():
        if _norm(c.raison_sociale or "") in wanted:
            return c
    # fallback contains
    key_n = _norm(key)
    for c in Client.query.all():
        rs = _norm(c.raison_sociale or "")
        if key_n and (key_n in rs or rs in key_n):
            return c
    if "tivaouane" in key_n and "clinique" not in key_n:
        for c in Client.query.all():
            if "tivaouane" in _norm(c.raison_sociale or ""):
                return c
    return None


def find_produit(produits: dict, designation: str):
    if designation in produits:
        return produits[designation]
    key = _norm(designation)
    for existing, p in produits.items():
        if _norm(existing) == key:
            return p
    for existing, p in produits.items():
        if key and _norm(existing) == key:
            return p
    alias_group = PRODUIT_ALIASES.get(key)
    if alias_group:
        wanted = {key, *(_norm(a) for a in alias_group)}
        for existing, p in produits.items():
            if _norm(existing) in wanted:
                return p
    return None


def run(dry_run: bool = False) -> None:
    from app import create_app
    from app.extensions import db
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.produit import CategorieProduit, Produit
    from app.models.stock import Stock
    from app.utils.bl_from_facture import assurer_bl_pour_facture

    app = create_app()
    with app.app_context():
        cat = CategorieProduit.query.filter_by(nom="Dispositifs médicaux").first()
        if not cat:
            cat = CategorieProduit.query.first()
        if not cat:
            raise SystemExit("Aucune catégorie produit — abort")

        produits = {p.designation: p for p in Produit.query.all()}
        created_f = created_c = created_p = skipped = 0

        for raw in FACTURES:
            numero = raw["numero"]
            existing = Facture.query.filter_by(numero=numero).first()
            if existing:
                print(f"  skip {numero} (numero existe)")
                skipped += 1
                assurer_bl_pour_facture(existing, statut="livre")
                continue

            client = find_client(Client, raw["client"])
            if not client:
                code = "CLI-" + slugify(raw["client"])[:20]
                base = code
                n = 1
                while Client.query.filter_by(code=code).first():
                    n += 1
                    code = f"{base}-{n}"
                low = raw["client"].lower()
                ctype = "clinique" if "clinique" in low or "inspection" in low else (
                    "hopital" if any(x in low for x in ("hopital", "hôpital", "chr")) else "autre"
                )
                client = Client(code=code, raison_sociale=raw["client"], type_client=ctype, est_actif=True)
                db.session.add(client)
                db.session.flush()
                created_c += 1
                print(f"  + client {raw['client']}")

            total_calc = money(sum(Decimal(q) * Decimal(p) for _, q, p in raw["lignes"]))
            dup = (
                Facture.query.filter_by(
                    client_id=client.id,
                    date_emission=raw["date"],
                    total_ttc=total_calc,
                ).first()
            )
            if dup:
                print(f"  skip {numero} (doublon date+client+montant -> {dup.numero})")
                skipped += 1
                continue

            if raw.get("total_attendu") is not None and money(raw["total_attendu"]) != total_calc:
                raise SystemExit(f"Total incohérent {numero}: calc={total_calc} attendu={raw['total_attendu']}")

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
                    db.session.add(Stock(produit_id=produit.id, quantite_disponible=1000, quantite_reservee=0))
                    produits[designation] = produit
                    created_p += 1
                    print(f"  + produit {designation}")

                montant = money(Decimal(qty) * Decimal(pu))
                lignes_data.append((produit, int(qty), money(pu), montant))

            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=raw["date"],
                date_echeance=raw["date"] + timedelta(days=30),
                remise_globale=Decimal("0"),
                total_ht=total_calc,
                tva_montant=Decimal("0"),
                total_ttc=total_calc,
                statut="emise",
                montant_paye=Decimal("0"),
                reste_a_payer=total_calc,
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
            created_f += 1
            print(f"  + {numero} | {client.raison_sociale} | {total_calc:,.0f} FCFA")

        if dry_run:
            db.session.rollback()
            print("\n[DRY-RUN] rollback — aucune écriture.")
        else:
            db.session.commit()
        print(f"\nRésumé : {created_f} factures, {created_c} clients, {created_p} produits, {skipped} ignorées")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
