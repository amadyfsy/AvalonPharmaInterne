#!/usr/bin/env python3
"""
Import factures historiques Avalon (oct. 2025 → août 2026).
Normalise clients / produits / numéros et crée factures + lignes.

Usage (depuis GestAvalon) :
  python sql/seed_factures_historique.py
  python sql/seed_factures_historique.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Données brutes : une facture = {numero, date, client, lignes:[(designation, qty, pu)]}
# Les lignes « Remise », « Réduction », « TVA » sont gérées à part.
# ---------------------------------------------------------------------------

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
        "numero": "2025/10/05",
        "date": date(2025, 10, 23),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Gants de révision utérine", 400, 650),
            ("Kit de traction adulte", 20, 5000),
            ("Kit de traction enfant", 10, 5000),
        ],
    },
    {
        "numero": "2025/10/06",
        "date": date(2025, 10, 23),
        "client": "Hôpital Tivaouane",
        "lignes": [("Filtre antibactérien", 100, 1820)],
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
    {
        "numero": "2026/01/02",
        "date": date(2026, 1, 2),
        "client": "RAJUNT DISTRIBUTION",
        "lignes": [("Valves d'Heimlich simple", 10, 8000)],
    },
    {
        "numero": "2026/01/03",
        "date": date(2026, 1, 3),
        "client": "Hôpital Tivaouane",
        "lignes": [("Valves d'Heimlich double", 20, 14000)],
    },
    {
        "numero": "2026/01/04",
        "date": date(2026, 1, 4),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Papier ECG 280x210 - 200 pages", 10, 18000),
            ("Papier ECG 295x210 - 100 pages", 10, 9000),
        ],
    },
    {
        "numero": "2026/01/05",
        "date": date(2026, 1, 5),
        "client": "RAJUNT DISTRIBUTION",
        "lignes": [("Valves d'Heimlich simple", 10, 8000)],
    },
    {
        "numero": "2026/02/01",
        "date": date(2026, 2, 1),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Kit de traction adulte", 20, 5000),
            ("Kit de traction enfant", 10, 5000),
        ],
    },
    {
        "numero": "2026/02/02",
        "date": date(2026, 2, 2),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Drap d'accouchement avec poche de recueil", 200, 3500),
            ("Robinet 3 voies", 200, 140),
            ("Prolongateur 75 à 100 cm", 200, 360),
        ],
    },
    {
        "numero": "2026/02/17",
        "date": date(2026, 2, 17),
        "client": "Centre de Santé 28 de Touba",
        "lignes": [
            ("Lampe à fente + tonomètre + table motorisée", 1, 1600000),
            ("Autoréfracto kératomètre + table motorisée", 1, 2760000),
            ("Microscope opératoire", 1, 1900000),
            ("Boîte verre à essai + montures", 1, 120000),
            ("Échelle d'acuité + projecteur test", 1, 400000),
            ("Ophtalmoscope indirect", 1, 80000),
            ("Lentille Volk 90", 1, 90000),
            ("Boîte cataracte", 1, 120000),
            ("Boîte de petite chirurgie", 1, 80000),
            ("Boîte de trichiasis", 1, 110000),
            ("Autoclave", 1, 800000),
            ("Boîte de chalazion", 1, 110000),
        ],
    },
    {
        "numero": "2026/03/01",
        "date": date(2026, 3, 10),
        "client": "Hôpital Tivaouane",
        "lignes": [("Câble vidéo Olympus MD148", 1, 412400)],
    },
    {
        "numero": "2026/03/02",
        "date": date(2026, 3, 10),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Kit de traction adulte", 20, 5000),
            ("Kit de traction enfant", 20, 5000),
            ("Gants pour invasion utérine", 400, 650),
        ],
    },
    {
        "numero": "2026/03/03",
        "date": date(2026, 3, 23),
        "client": "Inspection Médicale Scolaire Saint-Louis",
        "lignes": [("Rouleau papier ECG 210mm x 20m", 10, 8500)],
    },
    {
        "numero": "2026/03/04",
        "date": date(2026, 3, 30),
        "client": "Centre de Santé Serigne Saliou Touba",
        "lignes": [("Échobiométrie Scan AB", 1, 4000000)],
    },
    {
        "numero": "2026/03/05",
        "date": date(2026, 3, 31),
        "client": "Centre de Santé Keur Niang Touba",
        "lignes": [("Réfrigérateur médical 400L", 1, 510000)],
    },
    {
        "numero": "2026/04/01",
        "date": date(2026, 4, 7),
        "client": "CHR Saint-Louis",
        "lignes": [("Électrode B/50", 90, 3000)],
    },
    {
        "numero": "2026/04/03",
        "date": date(2026, 4, 7),
        "client": "Pharmacie MIFTAH S. Alioune Gueye",
        "lignes": [("Réfrigérateur médical 400L", 1, 510000)],
    },
    {
        "numero": "2026/04/05",
        "date": date(2026, 4, 13),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Drap d'accouchement avec poche de recueil", 300, 3500),
            ("Gants stériles T 7,5", 1000, 150),
            ("Gants pour invasion utérine", 400, 650),
        ],
    },
    {
        "numero": "2026/04/06",
        "date": date(2026, 4, 13),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Papier échographie UPP-110-HG", 10, 10000),
            ("Papier ECG 295x210 - 100 pages", 6, 9000),
        ],
    },
    {
        "numero": "2026/04/08",
        "date": date(2026, 4, 27),
        "client": "Centre de Santé 28 de Touba",
        "lignes": [("Table opératoire électrique", 1, 2300000)],
    },
    {
        "numero": "2026/04/09",
        "date": date(2026, 4, 29),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Surgicel", 11, 11500),
            ("Sinapi", 5, 20000),
            ("Aiguille de biopsie 16G 200mm", 10, 13500),
        ],
    },
    {
        "numero": "2026/05/01",
        "date": date(2026, 5, 1),
        "client": "Mme Sow",
        "lignes": [
            ("Drap d'accouchement avec poche de recueil", 20, 3200),
            ("Gants stériles T 7,5", 1000, 150),
            ("Électrode B/50", 900, 60),
            ("Gants pour invasion utérine", 100, 650),
        ],
    },
    {
        "numero": "2026/05/02",
        "date": date(2026, 5, 3),
        "client": "AM2S",
        "lignes": [
            ("Kit pour cataracte", 40, 50000),
            ("Boîte de bandelettes fluorescéine", 20, 16000),
        ],
    },
    {
        "numero": "2026/05/04",
        "date": date(2026, 5, 4),
        "client": "CH Maguette Lo de Linguère",
        "lignes": [("Turbine à deux trous", 4, 35000)],
    },
    {
        "numero": "2026/05/03",
        "date": date(2026, 5, 6),
        "client": "Medical Distribution",
        "lignes": [
            ("Aiguille de bloc nerveux 22G - 80 mm", 100, 5500),
            ("Aiguille de bloc nerveux 22G - 100 mm", 100, 5500),
        ],
    },
    {
        "numero": "2026/05/05",
        "date": date(2026, 5, 12),
        "client": "RAJUNT DISTRIBUTION",
        "lignes": [("Valves d'Heimlich double", 8, 14000)],
    },
    {
        "numero": "2026/05/06",
        "date": date(2026, 5, 18),
        "client": "Medical Distribution",
        "lignes": [("Hystéro", 30, 9000)],
    },
    {
        "numero": "2026/05/07",
        "date": date(2026, 5, 26),
        "client": "Hôpital Tivaouane",
        "lignes": [("Aiguille de bloc nerveux 22G - 150 mm", 30, 5500)],
    },
    {
        "numero": "2026/05/08",
        "date": date(2026, 5, 26),
        "client": "Hôpital Tivaouane",
        "lignes": [("Filtre HME", 196, 1900)],
    },
    {
        "numero": "2026/06/01",
        "date": date(2026, 6, 1),
        "client": "AM2S",
        "lignes": [
            ("Pince écartante", 3, 31500),
            ("Guide sonde", 2, 27000),
            ("Mandrin d'Eschmann", 2, 40500),
            ("Ciseau à plâtre", 2, 9000),
            ("Davier articulaire", 2, 9000),
            ("Davier de Lambotte", 2, 31500),
            ("Davier de Verbrugge à crémaillère GM/M", 8, 13500),
            ("Fer à courber les plaques", 4, 36000),
            ("Pince coupe-fil", 2, 49500),
            ("Presse à courber les plaques", 2, 175500),
        ],
        "remise_pct": Decimal("10"),
    },
    {
        "numero": "2026/06/02",
        "date": date(2026, 6, 2),
        "client": "Medical Distribution",
        "lignes": [
            ("Aiguille de bloc nerveux 22G - 80 mm", 100, 5500),
            ("Aiguille de bloc nerveux 22G - 100 mm", 100, 5500),
        ],
    },
    {
        "numero": "2026/06/03",
        "date": date(2026, 6, 2),
        "client": "CHR Saint-Louis",
        "lignes": [("Bistouri électrique Ysesu 350Y + accessoires", 1, 1100000)],
        "tva_pct": Decimal("18"),
    },
    {
        "numero": "2026/06/04",
        "date": date(2026, 6, 3),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Capteur SPO2 doigt adulte + câble 2,5 m", 2, 50000),
            ("Brassard NIBP adulte 27-35 cm", 2, 32000),
        ],
    },
    {
        "numero": "2026/06/05",
        "date": date(2026, 6, 5),
        "client": "Hôpital Tivaouane",
        "lignes": [("Cire à os", 12, 13500)],
    },
    {
        "numero": "2026/06/09",
        "date": date(2026, 6, 17),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Papier ECG 295x210 - 100 pages", 20, 9000),
            ("Électrode B/50", 1800, 60),
        ],
    },
    {
        "numero": "2026/06/10",
        "date": date(2026, 6, 17),
        "client": "CHR Diourbel",
        "lignes": [("Kit pour cataracte", 10, 50000)],
    },
    {
        "numero": "2026/06/11",
        "date": date(2026, 6, 22),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Drap d'accouchement avec poche de recueil", 300, 3500),
            ("Gants stériles T 7,5", 2000, 150),
            ("Prolongateur 75 à 100 cm", 200, 360),
        ],
    },
    {
        "numero": "2026/06/12",
        "date": date(2026, 6, 22),
        "client": "Hôpital Fann",
        "lignes": [("Pleurevac", 40, 45000)],
    },
    {
        "numero": "2026/06/08",
        "date": date(2026, 6, 24),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Bonnet S/100", 100, 2000),
            ("Couvre-chaussure S/100", 100, 1000),
            ("Gants de soins B/100", 5000, 1800),
            ("Masque chirurgical B/50", 580, 2000),
            ("Pièce de gaze (unité)", 500, 6500),
        ],
    },
    {
        "numero": "2026/06/13",
        "date": date(2026, 6, 30),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Bande de crêpe 10 cm", 1000, 300),
            ("Gants stériles T 7,5", 200, 6500),
            ("Casaque renforcée XL stérile", 1500, 1400),
            ("Casaque renforcée XXL stérile", 1000, 1500),
        ],
    },
    {
        "numero": "2026/06/14",
        "date": date(2026, 6, 30),
        "client": "CHR Saint-Louis",
        "lignes": [("Papier échographie UPP-110-HG", 85, 15000)],
    },
    {
        "numero": "2026/07/01",
        "date": date(2026, 7, 1),
        "client": "AM2S",
        "lignes": [
            ("Set d'urologie", 1, 420000),
            ("Set rénal", 1, 268000),
            ("Set orthopédie pédiatrique", 1, 232000),
            ("Set cataracte", 1, 120000),
            ("Set prostate", 1, 293000),
            ("Set de chirurgie générale", 1, 198000),
            ("Set vasculaire", 1, 238000),
            ("Boîte autodurable GM", 8, 30000),
            ("Boîte autodurable MM", 8, 25000),
        ],
    },
    {
        "numero": "2026/07/02",
        "date": date(2026, 7, 1),
        "client": "AM2S",
        "lignes": [
            ("Set amygdalectomie adulte", 1, 400000),
            ("Set amygdalectomie pédiatrie", 1, 400000),
            ("Set consultation gynéco", 1, 300000),
            ("Set césarienne", 1, 470000),
            ("Set laparotomie", 1, 385000),
        ],
    },
    {
        "numero": "2026/07/03",
        "date": date(2026, 7, 2),
        "client": "Hôpital Tivaouane",
        "lignes": [
            ("Pince de Kelly courbe 10 cm", 8, 4000),
            ("Ciseaux Mayo courbes 14 cm", 4, 10000),
            ("Ciseaux Metzenbaum courbes 14 cm", 6, 10000),
            ("Ciseaux à fil Spencer", 8, 6000),
            ("Boîte stérilisation inox 200x120x60 mm", 4, 30000),
            ("Boîte stérilisation inox 50x20x12 cm", 4, 40000),
            ("Écarteur Farabeuf 26x10", 4, 8000),
            ("Écarteur Farabeuf 30x10", 4, 10000),
            ("Écarteur Farabeuf 10x6", 4, 6000),
            ("Pince dissection Micro Girafe 10 cm", 4, 4000),
        ],
        "remise_pct": Decimal("10"),
    },
    {
        "numero": "2026/07/06",
        "date": date(2026, 7, 7),
        "client": "Clinique Abdou Lahad",
        "lignes": [
            ("Table motorisée", 1, 300000),
            ("Implant", 29, 4000),
        ],
    },
    {
        "numero": "2026/07/11",
        "date": date(2026, 7, 29),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Boîte césarienne", 10, 305500),
            ("Boîte d'hystérectomie", 5, 445500),
            ("Boîte d'accouchement", 30, 233000),
            ("Pinces à col", 15, 10000),
            ("Pinces à biopsie du col", 15, 35000),
            ("Pinces à cœur", 20, 10000),
            ("Pinces de Koogan", 5, 20000),
        ],
    },
    {
        "numero": "2026/07/12",
        "date": date(2026, 7, 29),
        "client": "CH Maguette Lo de Linguère",
        "lignes": [("Lampe à fente", 1, 950000)],
    },
    {
        "numero": "2026/08/01",
        "date": date(2026, 8, 1),
        "client": "CHR Saint-Louis",
        "lignes": [("Bonnet S/100", 600, 2000)],
    },
    {
        "numero": "2026/08/02",
        "date": date(2026, 8, 5),
        "client": "Pharmacie MIFTAH S. Alioune Gueye",
        "lignes": [("Flacon de Redon 600 ml", 150, 2800)],
    },
    {
        "numero": "2026/08/03",
        "date": date(2026, 8, 8),
        "client": "Demba Thioubou",
        "lignes": [
            ("Tonomètre", 1, 2250000),
            ("Imprimante Sony", 1, 500000),
        ],
    },
    {
        "numero": "2026/08/04",
        "date": date(2026, 8, 8),
        "client": "Centre de Santé de Vélingara",
        "lignes": [("Kit pour cataracte", 2, 50000)],
    },
    {
        "numero": "2026/08/05",
        "date": date(2026, 8, 11),
        "client": "CHR Saint-Louis",
        "lignes": [
            ("Kit pour cataracte", 10, 50000),
            ("Boîte de bandelettes fluorescéine", 5, 16000),
            ("Boîte fil 8/0", 3, 45000),
            ("Boîte fil 10/0", 5, 35000),
        ],
    },
]


# Alias → nom canonique (évite les doublons clients)
CLIENT_ALIASES = {
    "Hôpital Linguère": "CH Maguette Lo de Linguère",
    "Hopital Linguère": "CH Maguette Lo de Linguère",
    "Hôpital Linguere": "CH Maguette Lo de Linguère",
    "C H Magatte Lo de Linguère": "CH Maguette Lo de Linguère",
    "CH Magatte Lo de Linguère": "CH Maguette Lo de Linguère",
    "Centre Hospitalier Maguette Lo de Linguere": "CH Maguette Lo de Linguère",
    "Centre de Santé Keur Niang": "Centre de Santé Keur Niang Touba",
    "Centre de santé Keur Niang": "Centre de Santé Keur Niang Touba",
    "CENTRE DE SANTE KEUR NIANG TOUBA": "Centre de Santé Keur Niang Touba",
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").upper()
    return text[:40] or "X"


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def run(dry_run: bool = False) -> None:
    from app import create_app
    from app.extensions import db
    from app.models.client import Client
    from app.models.facture import Facture, LigneFacture
    from app.models.produit import CategorieProduit, Produit
    from app.models.stock import Stock

    app = create_app()
    with app.app_context():
        db.create_all()

        cat = CategorieProduit.query.filter_by(nom="Dispositifs médicaux").first()
        if not cat:
            cat = CategorieProduit(
                nom="Dispositifs médicaux",
                description="Consommables et équipements médicaux",
                code_formulaire="dispositifs",
            )
            db.session.add(cat)
            db.session.flush()

        clients_by_name: dict[str, Client] = {
            c.raison_sociale: c for c in Client.query.all()
        }
        produits_by_name: dict[str, Produit] = {
            p.designation: p for p in Produit.query.all()
        }

        created_clients = created_produits = created_factures = skipped = 0
        total_ttc_all = Decimal("0")

        for raw in FACTURES:
            numero = raw["numero"]
            if Facture.query.filter_by(numero=numero).first():
                skipped += 1
                print(f"  skip {numero} (existe déjà)")
                continue

            client_name = CLIENT_ALIASES.get(raw["client"], raw["client"])
            client = clients_by_name.get(client_name)
            if not client:
                code = "CLI-" + slugify(client_name)[:20]
                n = 1
                base_code = code
                while Client.query.filter_by(code=code).first():
                    n += 1
                    code = f"{base_code}-{n}"
                # Type client heuristique
                low = client_name.lower()
                if "pharmacie" in low:
                    ctype = "pharmacie"
                elif "hôpital" in low or "hopital" in low or "chr" in low or "ch " in low:
                    ctype = "hopital"
                elif "centre" in low or "inspection" in low:
                    ctype = "clinique"
                elif any(x in low for x in ("distribution", "medical", "am2s", "rajunt")):
                    ctype = "grossiste"
                else:
                    ctype = "autre"
                client = Client(
                    code=code,
                    raison_sociale=client_name,
                    type_client=ctype,
                    est_actif=True,
                )
                db.session.add(client)
                db.session.flush()
                clients_by_name[client_name] = client
                created_clients += 1

            lignes_data = []
            sous_total = Decimal("0")
            for designation, qty, pu in raw["lignes"]:
                produit = produits_by_name.get(designation)
                if not produit:
                    ref = "PRD-" + slugify(designation)[:24]
                    n = 1
                    base_ref = ref
                    while Produit.query.filter_by(reference=ref).first():
                        n += 1
                        ref = f"{base_ref}-{n}"
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
                    produits_by_name[designation] = produit
                    created_produits += 1

                montant = money(Decimal(qty) * Decimal(pu))
                sous_total += montant
                lignes_data.append((produit, int(qty), money(pu), montant))

            remise = Decimal("0")
            if raw.get("remise_pct"):
                remise = money(sous_total * Decimal(raw["remise_pct"]) / Decimal("100"))

            base_ht = money(sous_total - remise)
            tva_pct = Decimal(raw.get("tva_pct") or 0)
            tva_montant = money(base_ht * tva_pct / Decimal("100")) if tva_pct else Decimal("0")
            total_ttc = money(base_ht + tva_montant)

            # Échéance = date + 30 jours
            from datetime import timedelta

            d_emis = raw["date"]
            facture = Facture(
                numero=numero,
                client_id=client.id,
                date_emission=d_emis,
                date_echeance=d_emis + timedelta(days=30),
                remise_globale=remise,
                total_ht=base_ht,
                tva_montant=tva_montant,
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

            created_factures += 1
            total_ttc_all += total_ttc
            print(f"  + {numero} | {client_name} | {total_ttc:,.0f} FCFA")

        if dry_run:
            db.session.rollback()
            print("\n[DRY-RUN] aucune écriture.")
        else:
            db.session.commit()

        print(
            f"\nRésumé : {created_factures} factures, "
            f"{created_clients} clients, {created_produits} produits, "
            f"{skipped} ignorées, total TTC ≈ {total_ttc_all:,.0f} FCFA"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
