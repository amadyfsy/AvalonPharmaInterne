#!/usr/bin/env python3
"""Ajoute les dépenses manquantes depuis DEPENSES.xlsx (2025).

Anti-doublons : même date + montant TTC + libellé (ou n° facture Excel
dans le libellé). Convertit USD/MAD/INR → XOF (taux indicatifs).
Réutilise catégories / fournisseurs existants.

Usage — console Bash PythonAnywhere (compte DMS07) :

  NE PAS faire « source .env » : bash mange le $ du nom de base.
  dotenv charge .env correctement depuis Python.

  cd ~/AvalonPharmaInterne
  unset DATABASE_URL MYSQL_USER MYSQL_PASSWORD MYSQL_HOST MYSQL_DATABASE
  ~/.virtualenvs/avalon-interne/bin/python sql/seed_depenses_excel_manquantes.py --dry-run
  ~/.virtualenvs/avalon-interne/bin/python sql/seed_depenses_excel_manquantes.py
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

TAUX_XOF = {
    "XOF": Decimal("1"),
    "USD": Decimal("600"),
    "MAD": Decimal("60"),
    "INR": Decimal("7"),
}

# Catégories Avalon ciblées (code_systeme ou nom exact)
#  - appro_achats          Dépenses liées aux achats
#  - appro_douane          Douane (formalités / transitaires)
#  - appro_impot_douane    Impôt douane (droits / IMPO)
#  - rh_transport_personnel Transport du personnel
#  - vente_liee            Dépenses liées aux ventes (cahiers de charge / marchés)
#  - nom:Frais bancaires & agios  (garanties SONAC)
#  - nom:Maintenance & réparations (véhicules, locaux)

DEPENSES = [
    {
        'facture_no': 'FA49009',
        'titre': 'Tranport',
        'description': 'Transportt produits chine ->Dakar',
        'montant_xof': 192000.0,
        'montant_brut': 192000.0,
        'devise': 'XOF',
        'fournisseur': 'Expert Cargo',
        'date': date(2025, 11, 25),
    },
    {
        'facture_no': '582880',
        'titre': 'Maintenance vehicule',
        'description': 'Achat de batteries',
        'montant_xof': 200000.0,
        'montant_brut': 200000.0,
        'devise': 'XOF',
        'fournisseur': 'Elton Ngallele St-Louis',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'Tranport',
        'description': 'retour de produits 14 Cartons  (St louis --> Dakar)',
        'montant_xof': 30000.0,
        'montant_brut': 30000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 12, 30),
    },
    {
        'facture_no': '123/08',
        'titre': 'Approvisionnement',
        'description': '',
        'montant_xof': 1000000.0,
        'montant_brut': 1000000.0,
        'devise': 'XOF',
        'fournisseur': 'Distrix group',
        'date': date(2025, 8, 8),
    },
    {
        'facture_no': '',
        'titre': 'Tranport',
        'description': 'retour de produits 40 Cartons  (Dakar --> St louis )',
        'montant_xof': 50000.0,
        'montant_brut': 50000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 8, 9),
    },
    {
        'facture_no': 'psl 0011432.   15642.00',
        'titre': 'Approvisionnement + Transport',
        'description': 'sinapi tranport Afrique du sud --> AIBD',
        'montant_xof': 2771550.0,
        'montant_brut': 4619.25,
        'devise': 'USD',
        'fournisseur': 'Sinapi biomedical',
        'date': date(2025, 11, 27),
    },
    {
        'facture_no': '',
        'titre': 'Transport',
        'description': 'Aibd --> st Louis',
        'montant_xof': 15000.0,
        'montant_brut': 15000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': 'x044/172092024',
        'titre': 'Appovisionnement',
        'description': 'Inde',
        'montant_xof': 3510480.0,
        'montant_brut': 5850.8,
        'devise': 'USD',
        'fournisseur': 'ROMSON INTERNATIONAL',
        'date': date(2025, 4, 14),
    },
    {
        'facture_no': 'FA009225',
        'titre': 'ENTRETIENT DU LOCAL',
        'description': 'ENTRETIENT DU LOCAL',
        'montant_xof': 303000.0,
        'montant_brut': 303000.0,
        'devise': 'XOF',
        'fournisseur': 'KEUR SONGOMA',
        'date': date(2025, 11, 13),
    },
    {
        'facture_no': '7600032410',
        'titre': 'Approvisionnement',
        'description': 'Inde',
        'montant_xof': 861600.0,
        'montant_brut': 1436.0,
        'devise': 'USD',
        'fournisseur': 'ROMSON INTERNATIONAL',
        'date': date(2025, 4, 15),
    },
    {
        'facture_no': '5770/25',
        'titre': 'Appovisionnement',
        'description': 'CHINE',
        'montant_xof': 720600.0,
        'montant_brut': 1201.0,
        'devise': 'USD',
        'fournisseur': 'FORTUNE MEDICAL',
        'date': date(2025, 11, 21),
    },
    {
        'facture_no': 'CAAU8375888',
        'titre': 'TRANSPORT',
        'description': 'Transport produit chine --> dakar',
        'montant_xof': 214000.0,
        'montant_brut': 214000.0,
        'devise': 'XOF',
        'fournisseur': 'Expert cargo',
        'date': date(2025, 11, 18),
    },
    {
        'facture_no': 'FVA001983',
        'titre': 'TRANSIT',
        'description': '',
        'montant_xof': 1772156.0,
        'montant_brut': 1772156.0,
        'devise': 'XOF',
        'fournisseur': 'CO -TRANSEN',
        'date': date(2025, 11, 23),
    },
    {
        'facture_no': 'DE/073',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 36000.0,
        'montant_brut': 60.0,
        'devise': 'USD',
        'fournisseur': 'DARWIN EXPORT',
        'date': date(2025, 11, 4),
    },
    {
        'facture_no': 'DC50117',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 360570.0,
        'montant_brut': 600.95,
        'devise': 'USD',
        'fournisseur': 'CLARITY BIOPRODUCTS Dashmesh Sonal healthcare',
        'date': date(2025, 1, 17),
    },
    {
        'facture_no': '2025/WXX039',
        'titre': 'Appovisionnement',
        'description': 'CHINE',
        'montant_xof': 1008000.0,
        'montant_brut': 1680.0,
        'devise': 'USD',
        'fournisseur': 'HEBEI ORIENT',
        'date': date(2025, 11, 10),
    },
    {
        'facture_no': 'SC251024812',
        'titre': 'Appovisionnement',
        'description': 'CHINE',
        'montant_xof': 14109600.0,
        'montant_brut': 23516.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 12, 1),
    },
    {
        'facture_no': 'DS/24-25/40749',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 321230.0,
        'montant_brut': 45890.0,
        'devise': 'INR',
        'fournisseur': 'Dashmesh Sonal healthcare',
        'date': date(2024, 12, 30),
    },
    {
        'facture_no': '7600017658',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 3909600.0,
        'montant_brut': 6516.0,
        'devise': 'USD',
        'fournisseur': 'ROMSON INTERNATIONAL',
        'date': date(2025, 4, 15),
    },
    {
        'facture_no': '760032410',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 861600.0,
        'montant_brut': 1436.0,
        'devise': 'USD',
        'fournisseur': 'ROMSON INTERNATIONAL',
        'date': date(2025, 4, 15),
    },
    {
        'facture_no': 'MPI 102A 25-26 DT 24,5,25',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 9661200.0,
        'montant_brut': 16102.0,
        'devise': 'USD',
        'fournisseur': 'MODERN INDIA PRODUCT',
        'date': date(2025, 5, 24),
    },
    {
        'facture_no': '',
        'titre': 'GARANTIE DE SOUMISSION',
        'description': '',
        'montant_xof': 28500.0,
        'montant_brut': 28500.0,
        'devise': 'XOF',
        'fournisseur': 'SONAC',
        'date': date(2025, 8, 5),
    },
    {
        'facture_no': 'DE/2025-2601261',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 3744600.0,
        'montant_brut': 6241.0,
        'devise': 'USD',
        'fournisseur': 'DARWIN EXPORT',
        'date': date(2025, 11, 4),
    },
    {
        'facture_no': 'ORABANK',
        'titre': 'TRANSIT',
        'description': 'POUR LE CONTENEUR(ORABANK)',
        'montant_xof': 92613.0,
        'montant_brut': 92613.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 14),
    },
    {
        'facture_no': 'psl 0011432.   15642.00',
        'titre': 'Approvisionnement + Transport',
        'description': 'sinapi tranport Afrique du sud --> AIBD',
        'montant_xof': 2771550.0,
        'montant_brut': 4619.25,
        'devise': 'USD',
        'fournisseur': 'Sinapi biomedical',
        'date': date(2024, 12, 5),
    },
    {
        'facture_no': 'EAU',
        'titre': 'Appovisionnement',
        'description': 'CHINE',
        'montant_xof': 300000.0,
        'montant_brut': 500.0,
        'devise': 'USD',
        'fournisseur': 'SHANGHAI SHUOJIE OPTICS',
        'date': date(2025, 7, 15),
    },
    {
        'facture_no': 'MPI/154/24-25',
        'titre': 'Appovisionnement',
        'description': 'INDE',
        'montant_xof': 6816000.0,
        'montant_brut': 11360.0,
        'devise': 'USD',
        'fournisseur': 'MODERN INDIA PRODUCT',
        'date': date(2025, 2, 1),
    },
    {
        'facture_no': '',
        'titre': 'GARANTIE DE SOUMISSION',
        'description': '',
        'montant_xof': 56313.0,
        'montant_brut': 56313.0,
        'devise': 'XOF',
        'fournisseur': 'SONAC',
        'date': date(2025, 6, 20),
    },
    {
        'facture_no': '',
        'titre': 'GARANTIE DE SOUMISSION',
        'description': '',
        'montant_xof': 34770.0,
        'montant_brut': 34770.0,
        'devise': 'XOF',
        'fournisseur': 'SONAC',
        'date': date(2025, 2, 13),
    },
    {
        'facture_no': '',
        'titre': 'Appovisionnement',
        'description': 'INDE (70% DU MONTANT TOTAL)',
        'montant_xof': 5103600.0,
        'montant_brut': 8506.0,
        'devise': 'USD',
        'fournisseur': 'MODERN INDIA PRODUCT',
        'date': date(2025, 4, 30),
    },
    {
        'facture_no': 'FA25003918',
        'titre': 'Appovisionnement',
        'description': '',
        'montant_xof': 145000.0,
        'montant_brut': 145000.0,
        'devise': 'XOF',
        'fournisseur': 'MEDICAL DISTRIBUTION',
        'date': date(2025, 7, 25),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'DAKAR -->ST LOUIS',
        'montant_xof': 8000.0,
        'montant_brut': 8000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 7, 25),
    },
    {
        'facture_no': '740848',
        'titre': 'Maintenance vehicule',
        'description': 'PLAQUETTE DE FREIN',
        'montant_xof': 25000.0,
        'montant_brut': 25000.0,
        'devise': 'XOF',
        'fournisseur': 'Elton Ngallele St-Louis',
        'date': date(2025, 7, 25),
    },
    {
        'facture_no': '324486',
        'titre': 'Maintenance vehicule',
        'description': 'LIQUIDE FREIN,HUILE ,LAVAGE',
        'montant_xof': 103000.0,
        'montant_brut': 103000.0,
        'devise': 'XOF',
        'fournisseur': 'Elton Ngallele St-Louis',
        'date': date(2025, 7, 22),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'DHL',
        'montant_xof': 47960.0,
        'montant_brut': 47960.0,
        'devise': 'XOF',
        'fournisseur': 'DHL ST LOUIS',
        'date': date(2025, 4, 28),
    },
    {
        'facture_no': '',
        'titre': 'APPROVISIONNEMENT',
        'description': 'CHINE',
        'montant_xof': 225000.0,
        'montant_brut': 375.0,
        'devise': 'USD',
        'fournisseur': 'TSING YIHENG UNIVERSAL TECHNOLOGY',
        'date': date(2025, 7, 17),
    },
    {
        'facture_no': '',
        'titre': 'APPROVISIONNEMENT',
        'description': 'CHINE',
        'montant_xof': 258000.0,
        'montant_brut': 430.0,
        'devise': 'USD',
        'fournisseur': 'TSING YIHENG UNIVERSAL TECHNOLOGY',
        'date': date(2025, 7, 17),
    },
    {
        'facture_no': '',
        'titre': 'APPROVISIONNEMENT',
        'description': 'CHINE',
        'montant_xof': 138000.0,
        'montant_brut': 230.0,
        'devise': 'USD',
        'fournisseur': 'TSING YIHENG UNIVERSAL TECHNOLOGY',
        'date': date(2025, 7, 17),
    },
    {
        'facture_no': 'MRKU5146347',
        'titre': 'TRANSPORT',
        'description': 'Transport produit chine --> dakar',
        'montant_xof': 32000.0,
        'montant_brut': 32000.0,
        'devise': 'XOF',
        'fournisseur': 'Expert cargo',
        'date': date(2025, 9, 13),
    },
    {
        'facture_no': 'TCKU7983226',
        'titre': 'TRANSPORT',
        'description': 'Transport produit chine --> dakar',
        'montant_xof': 137000.0,
        'montant_brut': 137000.0,
        'devise': 'XOF',
        'fournisseur': 'Expert cargo',
        'date': date(2025, 8, 21),
    },
    {
        'facture_no': 'TGBU6922257',
        'titre': 'TRANSPORT',
        'description': 'Transport produit chine --> dakar',
        'montant_xof': 184000.0,
        'montant_brut': 184000.0,
        'devise': 'XOF',
        'fournisseur': 'Expert cargo',
        'date': date(2025, 8, 26),
    },
    {
        'facture_no': '5049605775099',
        'titre': 'RESERVATION',
        'description': 'MAROC',
        'montant_xof': 365731.2,
        'montant_brut': 6095.52,
        'devise': 'MAD',
        'fournisseur': 'SUITE LOC',
        'date': date(2025, 9, 28),
    },
    {
        'facture_no': 'SC251009800',
        'titre': 'Appovisionnement',
        'description': 'CHINE',
        'montant_xof': 832200.0,
        'montant_brut': 1387.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 10, 9),
    },
    {
        'facture_no': '24346',
        'titre': 'Appovisionnement',
        'description': 'DAKAR',
        'montant_xof': 3519750.0,
        'montant_brut': 3519750.0,
        'devise': 'XOF',
        'fournisseur': 'DDS MEDICAL',
        'date': date(2025, 10, 7),
    },
    {
        'facture_no': 'SNDKRP250008240',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 57287.0,
        'montant_brut': 57287.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': 'SNDKRPM250036329',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 4921.0,
        'montant_brut': 4921.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': 'SNDKRP250035736',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 6496.0,
        'montant_brut': 6496.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 13),
    },
    {
        'facture_no': 'SNDKRP250008090',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 85917.0,
        'montant_brut': 85917.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 13),
    },
    {
        'facture_no': 'G927775-1',
        'titre': 'APPROVISIONNEMENT',
        'description': 'PAKISTAN',
        'montant_xof': 1416600.0,
        'montant_brut': 2361.0,
        'devise': 'USD',
        'fournisseur': 'SKLAR MEDIX INTERNATIONAL',
        'date': date(2025, 9, 18),
    },
    {
        'facture_no': 'SNDKRP250037894',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 92447.0,
        'montant_brut': 92447.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 9),
    },
    {
        'facture_no': 'SNDKRP25007937',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 1648683.0,
        'montant_brut': 1648683.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 9),
    },
    {
        'facture_no': 'port',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 1770.0,
        'montant_brut': 1770.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': 'port',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 903355.0,
        'montant_brut': 903355.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': 'port',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 206840.0,
        'montant_brut': 206840.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': 'port',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 3183.0,
        'montant_brut': 3183.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': 'port',
        'titre': 'TRANSIT',
        'description': 'Transport produit',
        'montant_xof': 24093.0,
        'montant_brut': 24093.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 10, 16),
    },
    {
        'facture_no': '0555247 2025',
        'titre': 'DOUANE',
        'description': 'AIBD',
        'montant_xof': 12445.0,
        'montant_brut': 12445.0,
        'devise': 'XOF',
        'fournisseur': 'DOUANE',
        'date': None,
    },
    {
        'facture_no': 'MRKU5146347',
        'titre': 'TRANSPORT',
        'description': 'Transport produit chine --> dakar',
        'montant_xof': 214400.0,
        'montant_brut': 214400.0,
        'devise': 'XOF',
        'fournisseur': 'Expert cargo',
        'date': date(2025, 10, 18),
    },
    {
        'facture_no': '.00326',
        'titre': 'TRANSIT',
        'description': 'Chine ---> dakar',
        'montant_xof': 52500.0,
        'montant_brut': 52500.0,
        'devise': 'XOF',
        'fournisseur': 'Touba khaira',
        'date': date(2024, 12, 30),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 3000.0,
        'montant_brut': 3000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2024, 12, 30),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'DAKAR -->ST LOUIS',
        'montant_xof': 9000.0,
        'montant_brut': 9000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2024, 12, 30),
    },
    {
        'facture_no': '12/03/2025216929',
        'titre': 'ACHAT CAHIER DE CHARGE',
        'description': 'HOGIP',
        'montant_xof': 30000.0,
        'montant_brut': 30000.0,
        'devise': 'XOF',
        'fournisseur': 'HOGIP',
        'date': date(2025, 3, 12),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': '',
        'montant_xof': 5000.0,
        'montant_brut': 5000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 3, 12),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 6000.0,
        'montant_brut': 6000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 7, 3),
    },
    {
        'facture_no': '',
        'titre': 'ACHAT CAHIER DE CHARGE',
        'description': 'HOPITAL ST LOUIS',
        'montant_xof': 30000.0,
        'montant_brut': 30000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 8, 2),
    },
    {
        'facture_no': '',
        'titre': 'ACHAT CAHIER DE CHARGE',
        'description': 'HOPITAL TAMBA',
        'montant_xof': 30000.0,
        'montant_brut': 30000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 1),
    },
    {
        'facture_no': '2025/T0027',
        'titre': 'SENI',
        'description': 'SENI TRANSITAIRE',
        'montant_xof': 210000.0,
        'montant_brut': 210000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 30),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 1500.0,
        'montant_brut': 1500.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 22),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 4000.0,
        'montant_brut': 4000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 22),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 1500.0,
        'montant_brut': 1500.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 22),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'TRANPORT PRODUIT ST LOUIS TOUBA',
        'montant_xof': 3000.0,
        'montant_brut': 3000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 22),
    },
    {
        'facture_no': '18094',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'CAMION (KHADIM)',
        'montant_xof': 100000.0,
        'montant_brut': 100000.0,
        'devise': 'XOF',
        'fournisseur': 'BAOL POIDS LOURD',
        'date': date(2025, 9, 28),
    },
    {
        'facture_no': 'FA43830',
        'titre': 'TRANSIT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 96000.0,
        'montant_brut': 96000.0,
        'devise': 'XOF',
        'fournisseur': 'EXPET CARGO',
        'date': date(2025, 9, 1),
    },
    {
        'facture_no': '',
        'titre': 'TRANSIT',
        'description': 'TRANPORT PRODUIT',
        'montant_xof': 32000.0,
        'montant_brut': 32000.0,
        'devise': 'XOF',
        'fournisseur': 'EXPET CARGO',
        'date': date(2025, 10, 9),
    },
    {
        'facture_no': 'ORABANK',
        'titre': 'TRANSIT',
        'description': 'POUR LE CONTENEUR(ORABANK)',
        'montant_xof': 1741330.0,
        'montant_brut': 1741330.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 10),
    },
    {
        'facture_no': 'ORABANK',
        'titre': 'TRANSIT',
        'description': 'POUR LE CONTENEUR(ORABANK)',
        'montant_xof': 153050.0,
        'montant_brut': 153050.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 20),
    },
    {
        'facture_no': 'ORABANK',
        'titre': 'TRANSIT',
        'description': 'POUR LE CONTENEUR(ORABANK)',
        'montant_xof': 152050.0,
        'montant_brut': 152050.0,
        'devise': 'XOF',
        'fournisseur': 'MSC',
        'date': date(2025, 10, 20),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'CARBURANT CAMION',
        'montant_xof': 70000.0,
        'montant_brut': 70000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 10, 22),
    },
    {
        'facture_no': 'SC251024812',
        'titre': 'Appovisionnement',
        'description': '',
        'montant_xof': 9747600.0,
        'montant_brut': 16246.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 10, 24),
    },
    {
        'facture_no': 'F01847/25',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 270000.0,
        'montant_brut': 270000.0,
        'devise': 'XOF',
        'fournisseur': 'AFIA´MEDIC SI',
        'date': date(2025, 10, 24),
    },
    {
        'facture_no': 'SC251024812',
        'titre': 'Appovisionnement',
        'description': '',
        'montant_xof': 12087600.0,
        'montant_brut': 20146.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 10, 24),
    },
    {
        'facture_no': 'SC251024812',
        'titre': 'Appovisionnement',
        'description': '',
        'montant_xof': 12087600.0,
        'montant_brut': 20146.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 10, 24),
    },
    {
        'facture_no': 'SC251205561',
        'titre': 'Appovisionnement',
        'description': '',
        'montant_xof': 204000.0,
        'montant_brut': 340.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 10, 24),
    },
    {
        'facture_no': 'N° 0523271',
        'titre': 'IMPO',
        'description': '',
        'montant_xof': 90000.0,
        'montant_brut': 90000.0,
        'devise': 'XOF',
        'fournisseur': 'IMPO',
        'date': date(2025, 12, 5),
    },
    {
        'facture_no': 'YH20251206001',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 276000.0,
        'montant_brut': 460.0,
        'devise': 'USD',
        'fournisseur': 'TSINGTAO YIHENG',
        'date': date(2025, 12, 6),
    },
    {
        'facture_no': '1306264293190851',
        'titre': 'RESERVATION',
        'description': '',
        'montant_xof': 202800.0,
        'montant_brut': 338.0,
        'devise': 'USD',
        'fournisseur': 'C&P',
        'date': date(2025, 12, 7),
    },
    {
        'facture_no': 'CELECARE',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 25200.0,
        'montant_brut': 42.0,
        'devise': 'USD',
        'fournisseur': 'CELECARE',
        'date': date(2025, 12, 10),
    },
    {
        'facture_no': 'TPKUB202500630003',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 1380000.0,
        'montant_brut': 2300.0,
        'devise': 'USD',
        'fournisseur': 'LIANYUNGANG TUOPU',
        'date': date(2025, 12, 11),
    },
    {
        'facture_no': 'JZY2025120101',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 149220.0,
        'montant_brut': 248.7,
        'devise': 'USD',
        'fournisseur': 'JIANGSU JIANZHIYUAN MEDICAL',
        'date': date(2025, 12, 1),
    },
    {
        'facture_no': 'V231225',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 960000.0,
        'montant_brut': 1600.0,
        'devise': 'USD',
        'fournisseur': 'MEDITECH DEVICES',
        'date': date(2025, 12, 23),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': '',
        'montant_xof': 50000.0,
        'montant_brut': 50000.0,
        'devise': 'XOF',
        'fournisseur': 'IBRAHIMA',
        'date': date(2025, 12, 27),
    },
    {
        'facture_no': 'L2051W',
        'titre': 'APPROVISIONNEMENT',
        'description': '',
        'montant_xof': 262800.0,
        'montant_brut': 438.0,
        'devise': 'USD',
        'fournisseur': 'YANGZHOU SUSMED',
        'date': None,
    },
    {
        'facture_no': '0.00470',
        'titre': 'TRANSIT',
        'description': '',
        'montant_xof': 168000.0,
        'montant_brut': 168000.0,
        'devise': 'XOF',
        'fournisseur': 'TS CARGO',
        'date': date(2025, 12, 22),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'MERCEDES (S) SAINT -LOUIS',
        'montant_xof': 300000.0,
        'montant_brut': 300000.0,
        'devise': 'XOF',
        'fournisseur': 'IBRAHIMA MECANICIEN TOUBA',
        'date': date(2025, 12, 26),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'MERCEDES (S) SAINT -LOUIS',
        'montant_xof': 200000.0,
        'montant_brut': 200000.0,
        'devise': 'XOF',
        'fournisseur': 'IBRAHIMA MECANICIEN SAINT LOUIS',
        'date': date(2025, 9, 15),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'REMORQUES MERCEDES (E , S)',
        'montant_xof': 200000.0,
        'montant_brut': 200000.0,
        'devise': 'XOF',
        'fournisseur': 'MOR FREIN',
        'date': date(2025, 12, 26),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'TOYOTA  SAINT -LOUIS',
        'montant_xof': 220000.0,
        'montant_brut': 220000.0,
        'devise': 'XOF',
        'fournisseur': 'TOLIER',
        'date': date(2025, 9, 15),
    },
    {
        'facture_no': '',
        'titre': 'TRANSPORT',
        'description': 'Transport produit Dakar --> St- Louis',
        'montant_xof': 230000.0,
        'montant_brut': 230000.0,
        'devise': 'XOF',
        'fournisseur': 'TOLIER',
        'date': date(2025, 9, 15),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'ACHAT PNEU (4)',
        'montant_xof': 280000.0,
        'montant_brut': 280000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 12, 26),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'ACHAT BOITE DE VITESSE MERCEDES S + TRANSPORT',
        'montant_xof': 430000.0,
        'montant_brut': 430000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 15),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'ACHAT POMPE HUILE MERCEDES S + TRANSPORT',
        'montant_xof': 170000.0,
        'montant_brut': 170000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 15),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'ACHAT MOTEUR MERCEDES S',
        'montant_xof': 1500000.0,
        'montant_brut': 1500000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 15),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'ACHAT MOTEUR MERCEDES E',
        'montant_xof': 700000.0,
        'montant_brut': 700000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'TRANSPORT MOTEUR',
        'montant_xof': 300000.0,
        'montant_brut': 300000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'ACHAT POMPE HUILE MERCEDES S + TRANSPORT',
        'montant_xof': 170000.0,
        'montant_brut': 170000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': date(2025, 9, 18),
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'HUILE BOITE DE VITESSE.                 3X10L X 11000',
        'montant_xof': 33000.0,
        'montant_brut': 33000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'PEINTURE',
        'montant_xof': 150000.0,
        'montant_brut': 150000.0,
        'devise': 'XOF',
        'fournisseur': 'PEINTRE VEHICULE',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'VEHICULE',
        'description': 'ASSURANCE MERCEDESS',
        'montant_xof': 130000.0,
        'montant_brut': 130000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'VEHICULE',
        'description': 'ASSURANCE CAMION',
        'montant_xof': 200000.0,
        'montant_brut': 200000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'ENTRETIENT VEHICULE',
        'description': 'CLIMATISATION CAMION',
        'montant_xof': 100000.0,
        'montant_brut': 100000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'VEHICULE',
        'description': 'CARBURANT DIRECTEUR                    100000 X12',
        'montant_xof': 1200000.0,
        'montant_brut': 1200000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
    {
        'facture_no': '',
        'titre': 'TRANPORT DU PERSONNEL',
        'description': '50000X6',
        'montant_xof': 300000.0,
        'montant_brut': 300000.0,
        'devise': 'XOF',
        'fournisseur': '',
        'date': None,
    },
]


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text.upper()[:40] or "X"


def norm_text(titre: str) -> str:
    t = unicodedata.normalize("NFKD", titre or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().casefold()


def build_libelle(raw: dict) -> str:
    parts = []
    if raw.get("facture_no"):
        parts.append(f"[{raw['facture_no']}]")
    titre = (raw.get("titre") or "").strip()
    desc = (raw.get("description") or "").strip()
    if titre and desc:
        parts.append(f"{titre} — {desc}")
    elif titre or desc:
        parts.append(titre or desc)
    if raw.get("devise") and raw["devise"] != "XOF":
        parts.append(f"({raw['montant_brut']} {raw['devise']})")
    lib = " ".join(parts).strip() or "Dépense Excel"
    return lib[:255]


def _contains_any(text: str, *needles: str) -> bool:
    return any(n in text for n in needles)


def classify_categorie_target(raw: dict) -> tuple[str, str]:
    """Retourne (kind, key) : ('code', code_systeme) ou ('nom', nom_categorie).

    Règles métier alignées sur les catégories système Avalon existantes,
    en croisant titre Excel + description + fournisseur.
    """
    titre = norm_text(raw.get("titre") or "")
    desc = norm_text(raw.get("description") or "")
    fourn = norm_text(raw.get("fournisseur") or "")
    blob = f"{titre} {desc} {fourn}"

    # 1) Transport du personnel (RH)
    if _contains_any(titre, "personnel") or _contains_any(blob, "transport du personnel", "tranport du personnel"):
        return "code", "rh_transport_personnel"

    # 2) Impôt / droits de douane
    if titre == "impo" or _contains_any(blob, "impot douane", "impôt douane", "droits de douane"):
        return "code", "appro_impot_douane"

    # 3) Douane / transit / transitaires / MSC / formalités portuaires
    # Attention : ne pas matcher "port" dans "transport" / "tranport"
    frais_port = bool(re.search(r"(?:^|[^a-z])port(?:[^a-z]|$)", blob)) and not _contains_any(
        titre, "transport", "tranport"
    )
    if (
        _contains_any(titre, "transit", "douane", "seni")
        or _contains_any(
            blob,
            "transitaire",
            "co -transen",
            "co-transen",
            "cotransen",
            "msc",
            "orabank",
            "conteneur",
            "touba khaira",
            "ts cargo",
        )
        or (frais_port and _contains_any(titre, "transit", "douane"))
        or (titre in {"port", "douane"} or blob.strip() == "port")
        or (raw.get("facture_no") and norm_text(str(raw.get("facture_no"))) == "port")
    ):
        return "code", "appro_douane"

    # 4) Garanties bancaires / soumission (SONAC…)
    if _contains_any(blob, "garantie", "soumission", "sonac"):
        return "nom", "Frais bancaires & agios"

    # 5) Cahiers de charge / marchés publics (activité commerciale)
    if _contains_any(blob, "cahier de charge", "cahier des charges", "hogip"):
        return "code", "vente_liee"

    # 6) Maintenance véhicules / locaux / assurances véhicules
    if _contains_any(
        titre,
        "maintenance",
        "entretient",
        "entretien",
        "vehicule",
        "véhicule",
    ) or _contains_any(
        blob,
        "batterie",
        "frein",
        "pneu",
        "moteur",
        "mercedes",
        "toyota",
        "peinture",
        "mecanicien",
        "mécanicien",
        "assurance mercedes",
        "assurance camion",
        "climatisation camion",
        "huile boite",
        "baol poids",
        "elton",
        "entretient du local",
        "entretien du local",
        "keur songoma",
    ):
        return "nom", "Maintenance & réparations"

    # Carburant directeur (véhicule de direction) → maintenance
    if _contains_any(blob, "carburant directeur"):
        return "nom", "Maintenance & réparations"

    # 7) Réservation voyage / hôtel liée à un fournisseur d'appro (C&P…) → achats
    if _contains_any(titre, "reservation", "réservation"):
        if _contains_any(blob, "c&p", "suite loc", "maroc"):
            return "code", "appro_achats"
        return "code", "appro_achats"

    # 8) Approvisionnement / fournisseurs internationaux / fret marchandises
    if _contains_any(
        titre,
        "approvision",
        "appovision",
    ) or _contains_any(
        blob,
        "romson",
        "sinapi",
        "darwin",
        "fortune medical",
        "hebei",
        "modern india",
        "clarity",
        "sklar",
        "dds medical",
        "medical distribution",
        "tsing",
        "celecare",
        "meditech",
        "jiangsu",
        "lianyungang",
        "yangzhou",
        "afi",
        "inde",
        "chine",
        "pakistan",
        "afrique du sud",
    ):
        return "code", "appro_achats"

    # 9) Transport marchandises / logistique (pas personnel)
    if _contains_any(titre, "transport", "tranport") or _contains_any(
        blob,
        "expert cargo",
        "expet cargo",
        "dhl",
        "fret",
        "cartons",
        "produit chine",
        "produits chine",
        "dakar -->",
        "st louis",
        "st-louis",
        "aibd -->",
        "carburant camion",
    ):
        return "code", "appro_achats"

    # Fallback métier : charges d'exploitation liées à l'appro
    return "code", "appro_achats"


def resolve_categorie(raw: dict):
    """Résout la catégorie ORM à partir des codes/noms système existants."""
    from app.models.depense import CategorieDepense
    from app.utils.categorie_depense_registry import get_categorie_by_code

    kind, key = classify_categorie_target(raw)
    cat = None
    if kind == "code":
        cat = get_categorie_by_code(key)
    else:
        cat = CategorieDepense.query.filter(CategorieDepense.nom == key).first()
        if not cat:
            # tolérance accents / casse
            for c in CategorieDepense.query.all():
                if norm_text(c.nom) == norm_text(key):
                    cat = c
                    break

    if not cat:
        cat = get_categorie_by_code("appro_achats") or CategorieDepense.query.order_by(
            CategorieDepense.id.asc()
        ).first()
    return cat, kind, key


def find_existing_depense(Depense, raw: dict, libelle: str, montant: Decimal):
    d = raw.get("date")
    if d is None:
        return None
    candidates = Depense.query.filter(
        Depense.date_depense == d,
        Depense.montant_ttc == montant,
    ).all()
    for existing in candidates:
        if (existing.libelle or "")[:80] == libelle[:80]:
            return existing
        if raw.get("facture_no") and raw["facture_no"] in (existing.libelle or ""):
            return existing
    return None


def run(dry_run: bool = False, reclassify: bool = False):
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    from app import create_app
    from app.extensions import db
    from app.models.depense import Depense
    from app.models.fournisseur import Fournisseur
    from app.models.user import User
    from app.utils.depense_reference import prochaine_reference_depense
    from app.utils.seed_expense_categories import ensure_default_depense_categories

    app = create_app()
    with app.app_context():
        ensure_default_depense_categories()
        user = User.query.order_by(User.id.asc()).first()
        if not user:
            raise SystemExit("Aucun utilisateur — impossible de créer des dépenses.")

        created = skipped = created_f = reclassed = 0
        stats: dict[str, int] = {}

        print("\n— Classification (aperçu) —")
        for raw in DEPENSES:
            cat, kind, key = resolve_categorie(raw)
            label = cat.nom if cat else f"? {kind}:{key}"
            stats[label] = stats.get(label, 0) + 1
        for nom, n in sorted(stats.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {n:3d}  {nom}")
        print()

        for raw in DEPENSES:
            libelle = build_libelle(raw)
            montant = money(raw["montant_xof"])
            d = raw.get("date")
            cat, kind, key = resolve_categorie(raw)
            if not cat:
                raise SystemExit(f"Catégorie introuvable pour {kind}:{key} — {libelle[:60]}")

            type_dep = getattr(cat.type_depense, "value", cat.type_depense) or "variable"

            if d is None:
                print(f"  skip (sans date) [{cat.nom}] {libelle[:55]}")
                skipped += 1
                continue

            existing = find_existing_depense(Depense, raw, libelle, montant)
            if existing:
                if reclassify and existing.categorie_id != cat.id:
                    old = existing.categorie.nom if existing.categorie else "?"
                    existing.categorie_id = cat.id
                    existing.type_depense = type_dep
                    reclassed += 1
                    print(f"  ~ reclass {existing.reference}: {old} → {cat.nom} | {libelle[:45]}")
                else:
                    print(f"  skip doublon [{cat.nom}] {d} | {montant} | {libelle[:40]}")
                    skipped += 1
                continue

            if reclassify:
                # mode reclass uniquement : ne crée pas de nouvelles lignes
                skipped += 1
                continue

            fourn = None
            if raw.get("fournisseur"):
                nom_f = raw["fournisseur"].strip()
                fourn = Fournisseur.query.filter(
                    Fournisseur.raison_sociale.ilike(nom_f)
                ).first()
                if not fourn:
                    bn = norm_text(nom_f)
                    for f in Fournisseur.query.all():
                        a = norm_text(f.raison_sociale)
                        if a and bn and (a in bn or bn in a):
                            fourn = f
                            break
                if not fourn:
                    code = "FRN-" + slugify(nom_f)[:20]
                    base = code
                    n = 1
                    while Fournisseur.query.filter_by(code=code).first():
                        n += 1
                        code = f"{base}-{n}"
                    fourn = Fournisseur(
                        code=code,
                        raison_sociale=nom_f[:150],
                        est_actif=True,
                    )
                    db.session.add(fourn)
                    db.session.flush()
                    created_f += 1
                    print(f"  + fournisseur {nom_f}")

            ref = prochaine_reference_depense(d)
            dep = Depense(
                reference=ref,
                categorie_id=cat.id,
                type_depense=type_dep,
                libelle=libelle,
                montant_ht=montant,
                tva=Decimal("0"),
                montant_ttc=montant,
                date_depense=d,
                mode_paiement="virement",
                fournisseur_id=fourn.id if fourn else None,
                statut="valide",
                valide_par=user.id,
                created_by=user.id,
            )
            db.session.add(dep)
            created += 1
            print(f"  + [{cat.nom}] {ref} | {d} | {montant:,.0f} | {libelle[:45]}")

        if dry_run:
            db.session.rollback()
            print("\n[DRY-RUN] rollback — aucune écriture.")
        else:
            db.session.commit()
        print(
            f"\nRésumé : {created} créées, {reclassed} reclassées, "
            f"{created_f} fournisseurs, {skipped} ignorées"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--reclassify",
        action="store_true",
        help="Recatégorise les dépenses Excel déjà importées (sans en créer de nouvelles).",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run, reclassify=args.reclassify)


if __name__ == "__main__":
    main()
