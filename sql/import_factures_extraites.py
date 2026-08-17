#!/usr/bin/env python3
"""
Import des données « factures_extraites » (dump SQLite) vers la base MySQL GestAvalon.

Lit par défaut : GestAvalon/sql/factures_extraites_liees_archive.sqlite.sql

Usage (depuis la racine du projet Flask, dossier contenant config.py) :
  PYTHONPATH=. python GestAvalon/sql/import_factures_extraites.py
  PYTHONPATH=. python GestAvalon/sql/import_factures_extraites.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ARCHIVE_DEFAULT = os.path.join(
    os.path.dirname(__file__), "factures_extraites_liees_archive.sqlite.sql"
)

INSERT_RE_TEMPLATE = r'^INSERT INTO "{table}" VALUES\((.*)\);\s*$'

TVA_DEFAULT_PCT = Decimal("18")


def split_sql_values(inner: str) -> list:
    """Découpe le contenu entre parenthèses d'un INSERT SQLite (chaînes quotées, NULL)."""
    out = []
    i = 0
    n = len(inner)
    while i < n:
        while i < n and inner[i] in " \t":
            i += 1
        if i >= n:
            break
        if inner[i] == "'":
            i += 1
            buf = []
            while i < n:
                if inner[i] == "'" and i + 1 < n and inner[i + 1] == "'":
                    buf.append("'")
                    i += 2
                    continue
                if inner[i] == "'":
                    i += 1
                    break
                buf.append(inner[i])
                i += 1
            out.append("".join(buf))
        else:
            start = i
            while i < n and inner[i] != ",":
                i += 1
            token = inner[start:i].strip()
            out.append(None if token.upper() == "NULL" else token)
        if i < n and inner[i] == ",":
            i += 1
    return out


def extract_inserts(sql_path: str, table: str) -> list[list]:
    pattern = re.compile(INSERT_RE_TEMPLATE.format(table=table))
    rows = []
    with open(sql_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            m = pattern.match(line)
            if m:
                rows.append(split_sql_values(m.group(1)))
    return rows


def dec_val(v, default: Decimal = Decimal("0")) -> Decimal:
    if v is None:
        return default
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_int_qty(v) -> int:
    if v is None:
        return 0
    d = Decimal(str(v))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_order_date(s: str | None) -> date:
    if not s:
        return date.today()
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            from datetime import datetime as dt

            return dt.strptime(s, fmt).date()
        except ValueError:
            continue
    return date.today()


def infer_type_client(name: str) -> str:
    n = name.lower()
    if "pharmacie" in n:
        return "pharmacie"
    if "distribution" in n or "lk group" in n:
        return "grossiste"
    if any(
        x in n
        for x in (
            "hopital",
            "hôpital",
            "chr ",
            "chn ",
            "centre hospitalier",
            "hospital",
        )
    ):
        return "hopital"
    if "centre de santé" in n or "centre de sante" in n:
        return "clinique"
    return "autre"


def load_extract(sql_file: str):
    """Charge et structure les lignes INSERT depuis le dump SQLite."""
    clients_rows = extract_inserts(sql_file, "clients")
    products_rows = extract_inserts(sql_file, "products")
    orders_rows = extract_inserts(sql_file, "orders")
    items_rows = extract_inserts(sql_file, "order_items")

    if not clients_rows or not products_rows or not orders_rows:
        return None

    items_by_order: dict[int, list] = {}
    for row in items_rows:
        oid = int(row[1])
        items_by_order.setdefault(oid, []).append(row)

    return clients_rows, products_rows, orders_rows, items_rows, items_by_order


def purge_all_sales_inventory(session) -> None:
    """Supprime les données métier liées ventes / stocks / achats pour réimporter proprement."""
    from sqlalchemy import text

    stmts = [
        "DELETE FROM lignes_facture",
        "DELETE FROM factures",
        "DELETE FROM lignes_proforma",
        "DELETE FROM proformas",
        "DELETE FROM lignes_bl",
        "DELETE FROM bons_livraison",
        "DELETE FROM mouvements_stock",
        "DELETE FROM lignes_commande_fournisseur",
        "DELETE FROM commandes_fournisseurs",
        "DELETE FROM stocks",
        "DELETE FROM lots",
        "DELETE FROM produits",
        "DELETE FROM clients",
    ]
    session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    for sql in stmts:
        session.execute(text(sql))
    session.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def run_import(
    clients_rows,
    products_rows,
    orders_rows,
    items_by_order,
    skip_purge: bool,
) -> None:
    from GestAvalon.app import create_app
    from GestAvalon.app.extensions import db
    from GestAvalon.app.models.client import Client
    from GestAvalon.app.models.facture import Facture, LigneFacture
    from GestAvalon.app.models.produit import CategorieProduit, Produit
    from GestAvalon.app.models.proforma import LigneProforma, Proforma
    from GestAvalon.app.utils.bl_from_facture import assurer_bl_pour_facture

    app = create_app("default")
    with app.app_context():
        if not skip_purge:
            purge_all_sales_inventory(db.session)
            db.session.commit()

        cat = CategorieProduit.query.filter_by(nom="Import factures extraites").first()
        if not cat:
            cat = CategorieProduit(
                nom="Import factures extraites",
                description="Créée automatiquement par import_factures_extraites.py",
            )
            db.session.add(cat)
            db.session.flush()

        client_map: dict[int, int] = {}
        for row in sorted(clients_rows, key=lambda r: int(r[0])):
            old_id = int(row[0])
            name = (row[1] or "").strip()[:150]
            code = f"IMP-CLI-{old_id:03d}"
            c = Client(
                code=code,
                raison_sociale=name or f"Client import {old_id}",
                type_client=infer_type_client(name),
                est_actif=True,
            )
            db.session.add(c)
            db.session.flush()
            client_map[old_id] = c.id

        product_map: dict[int, int] = {}
        for row in sorted(products_rows, key=lambda r: int(r[0])):
            old_id = int(row[0])
            designation = (row[1] or "Produit import").strip()[:200]
            p_ht = dec_val(row[2])
            p_ttc = (p_ht * (Decimal("1") + TVA_DEFAULT_PCT / Decimal("100"))).quantize(
                Decimal("0.01")
            )
            achat = (p_ht * Decimal("0.75")).quantize(Decimal("0.01"))
            p = Produit(
                reference=f"IMP-P-{old_id:05d}",
                designation=designation,
                categorie_id=cat.id,
                forme="dispositif",
                unite="unité",
                prix_achat_ht=achat,
                prix_vente_ht=p_ht,
                tva=TVA_DEFAULT_PCT,
                prix_vente_ttc=p_ttc,
                seuil_alerte_stock=10,
                est_actif=True,
            )
            db.session.add(p)
            db.session.flush()
            product_map[old_id] = p.id

        for ord_row in sorted(orders_rows, key=lambda r: int(r[0])):
            oid = int(ord_row[0])
            old_client_id = int(ord_row[1])
            invoice_number = ord_row[2] or ""
            doc_type = (ord_row[3] or "").strip().lower()
            order_date = parse_order_date(ord_row[4])
            source_file = ord_row[6] or ""

            lines = items_by_order.get(oid, [])
            client_id = client_map.get(old_client_id)
            if client_id is None:
                continue

            computed_ht = Decimal("0")
            tva_sum = Decimal("0")

            if doc_type == "proforma":
                pf = Proforma(
                    numero=f"PF-IMP-{oid:04d}",
                    client_id=client_id,
                    date_emission=order_date,
                    date_validite=order_date + timedelta(days=30),
                    remise_globale=Decimal("0"),
                    total_ht=Decimal("0"),
                    tva_montant=Decimal("0"),
                    total_ttc=Decimal("0"),
                    statut="envoye",
                    notes=f"Import extrait — fichier: {source_file[:500]} | N° document: {invoice_number}",
                )
                db.session.add(pf)
                db.session.flush()

                for item in sorted(lines, key=lambda x: int(x[3])):
                    old_pid = int(item[2])
                    pid = product_map.get(old_pid)
                    if pid is None:
                        continue
                    produit = db.session.get(Produit, pid)
                    if not produit:
                        continue
                    qty = to_int_qty(item[4])
                    pu_ht = dec_val(item[5])
                    montant_ht = (Decimal(qty) * pu_ht).quantize(Decimal("0.01"))
                    tva_ligne = (montant_ht * produit.tva / Decimal("100")).quantize(
                        Decimal("0.01")
                    )
                    computed_ht += montant_ht
                    tva_sum += tva_ligne
                    db.session.add(
                        LigneProforma(
                            proforma_id=pf.id,
                            produit_id=pid,
                            quantite=qty,
                            prix_unitaire_ht=pu_ht,
                            remise=Decimal("0"),
                            montant_ht=montant_ht,
                        )
                    )

                pf.total_ht = computed_ht
                pf.tva_montant = tva_sum
                pf.total_ttc = computed_ht + tva_sum

            elif doc_type == "facture":
                fa = Facture(
                    numero=f"FAC-IMP-{oid:04d}",
                    proforma_id=None,
                    client_id=client_id,
                    date_emission=order_date,
                    date_echeance=order_date + timedelta(days=30),
                    remise_globale=Decimal("0"),
                    total_ht=Decimal("0"),
                    tva_montant=Decimal("0"),
                    total_ttc=Decimal("0"),
                    statut="emise",
                    montant_paye=Decimal("0"),
                    reste_a_payer=Decimal("0"),
                )
                db.session.add(fa)
                db.session.flush()

                computed_ht = Decimal("0")
                tva_sum = Decimal("0")
                for item in sorted(lines, key=lambda x: int(x[3])):
                    old_pid = int(item[2])
                    pid = product_map.get(old_pid)
                    if pid is None:
                        continue
                    produit = db.session.get(Produit, pid)
                    if not produit:
                        continue
                    qty = to_int_qty(item[4])
                    pu_ht = dec_val(item[5])
                    montant_ht = (Decimal(qty) * pu_ht).quantize(Decimal("0.01"))
                    tva_ligne = (montant_ht * produit.tva / Decimal("100")).quantize(
                        Decimal("0.01")
                    )
                    computed_ht += montant_ht
                    tva_sum += tva_ligne
                    db.session.add(
                        LigneFacture(
                            facture_id=fa.id,
                            produit_id=pid,
                            lot_id=None,
                            quantite=qty,
                            prix_unitaire_ht=pu_ht,
                            remise=Decimal("0"),
                            montant_ht=montant_ht,
                        )
                    )

                total_ttc = computed_ht + tva_sum
                fa.total_ht = computed_ht
                fa.tva_montant = tva_sum
                fa.total_ttc = total_ttc
                fa.reste_a_payer = total_ttc
                db.session.flush()
                assurer_bl_pour_facture(fa, statut="livre")
            else:
                continue

        db.session.commit()
        print(
            f"Import terminé : {len(client_map)} clients, {len(product_map)} produits, "
            f"{len(orders_rows)} documents vente."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import extract SQLite → GestAvalon MySQL")
    parser.add_argument(
        "--sqlite-file",
        default=ARCHIVE_DEFAULT,
        help="Fichier dump SQLite source (INSERT …)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse uniquement, aucune écriture en base",
    )
    parser.add_argument(
        "--no-purge",
        action="store_true",
        help="Ne pas supprimer les données existantes avant import (risque de doublons)",
    )
    args = parser.parse_args()
    path = os.path.abspath(args.sqlite_file)
    if not os.path.isfile(path):
        print(f"Fichier introuvable : {path}", file=sys.stderr)
        sys.exit(1)

    loaded = load_extract(path)
    if loaded is None:
        print("Échec parse : vérifiez le fichier SQL source.", file=sys.stderr)
        sys.exit(1)

    clients_rows, products_rows, orders_rows, items_rows, items_by_order = loaded

    if args.dry_run:
        print(
            f"[dry-run] clients={len(clients_rows)} produits={len(products_rows)} "
            f"commandes={len(orders_rows)} lignes_order_items={len(items_rows)}"
        )
        return

    run_import(
        clients_rows,
        products_rows,
        orders_rows,
        items_by_order,
        skip_purge=args.no_purge,
    )


if __name__ == "__main__":
    main()
