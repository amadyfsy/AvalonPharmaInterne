#!/usr/bin/env python3
"""
Ajoute les colonnes manquantes pour les fiches métier produit (MySQL).

Usage (depuis le dossier parent contenant GestAvalon et config.py) :
  python GestAvalon/migrate_produit_metier_db.py

Idempotent : ne fait rien si les colonnes existent déjà.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sqlalchemy import inspect, text  # noqa: E402

from GestAvalon.app import create_app  # noqa: E402
from GestAvalon.app.extensions import db  # noqa: E402


def _has_column(engine, table: str, column: str) -> bool:
    insp = inspect(engine)
    try:
        return any(c['name'] == column for c in insp.get_columns(table))
    except Exception:
        return False


def _has_index(engine, table: str, name: str) -> bool:
    insp = inspect(engine)
    try:
        for ix in insp.get_indexes(table):
            if ix.get('name') == name:
                return True
    except Exception:
        pass
    return False


def main() -> int:
    app = create_app()
    with app.app_context():
        engine = db.engine
        dialect = engine.dialect.name

        if dialect != 'mysql':
            print(f'Base détectée : {dialect} — ce script cible MySQL (pymysql).')
            print('Pour SQLite, exécutez manuellement les ALTER adaptés (TEXT à la place de JSON).')

        with engine.begin() as conn:
            if not _has_column(engine, 'lots', 'quantite_disponible'):
                conn.execute(text('ALTER TABLE lots ADD COLUMN quantite_disponible INT NOT NULL DEFAULT 0'))
                print('OK : colonne lots.quantite_disponible ajoutée.')
                conn.execute(
                    text(
                        """
                        UPDATE lots l
                        LEFT JOIN (
                          SELECT lot_id,
                                 SUM(
                                   CASE
                                     WHEN type_mouvement IN ('entree', 'retour') THEN quantite
                                     WHEN type_mouvement IN ('sortie', 'ajustement') THEN -quantite
                                     ELSE 0
                                   END
                                 ) AS qte
                          FROM mouvements_stock
                          WHERE lot_id IS NOT NULL
                          GROUP BY lot_id
                        ) m ON m.lot_id = l.id
                        SET l.quantite_disponible = GREATEST(0, COALESCE(m.qte, l.quantite_initiale, 0))
                        """
                    )
                )
                print('OK : lots.quantite_disponible initialisé (mouvements/quantité initiale).')
            else:
                print('Déjà présent : lots.quantite_disponible')

            if not _has_column(engine, 'produits', 'donnees_metier'):
                conn.execute(text('ALTER TABLE produits ADD COLUMN donnees_metier JSON NULL'))
                print('OK : colonne produits.donnees_metier ajoutée.')
            else:
                print('Déjà présent : produits.donnees_metier')

            if not _has_column(engine, 'employes', 'date_fin_contrat'):
                conn.execute(text('ALTER TABLE employes ADD COLUMN date_fin_contrat DATE NULL'))
                print('OK : colonne employes.date_fin_contrat ajoutée.')
            else:
                print('Déjà présent : employes.date_fin_contrat')

            if not _has_column(engine, 'categories_produits', 'code_formulaire'):
                conn.execute(
                    text(
                        'ALTER TABLE categories_produits ADD COLUMN code_formulaire VARCHAR(50) NULL'
                    )
                )
                print('OK : colonne categories_produits.code_formulaire ajoutée.')
            else:
                print('Déjà présent : categories_produits.code_formulaire')

            if not _has_index(engine, 'categories_produits', 'ix_categories_produits_code_formulaire'):
                try:
                    conn.execute(
                        text(
                            'CREATE INDEX ix_categories_produits_code_formulaire '
                            'ON categories_produits (code_formulaire)'
                        )
                    )
                    print('OK : index ix_categories_produits_code_formulaire créé.')
                except Exception as e:
                    print(f'Index (ignoré si doublon) : {e}')
            else:
                print('Déjà présent : index ix_categories_produits_code_formulaire')

    print('Migration terminée.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
