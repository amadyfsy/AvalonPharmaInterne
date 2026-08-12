#!/usr/bin/env python3
"""
Migre les numéros facture/BL vers le format YYYY/MM/NN (ex. 2026/06/02).
Le BL lié reprend le même numéro que sa facture.

Usage :
  python sql/migrate_numeros_yyyy_mm_nn.py           # simulation
  python sql/migrate_numeros_yyyy_mm_nn.py --apply   # écriture
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Appliquer les changements")
    args = parser.parse_args()

    from app import create_app
    from app.utils.document_numero import migrer_numeros_vers_yyyy_mm_nn

    app = create_app()
    with app.app_context():
        changes = migrer_numeros_vers_yyyy_mm_nn(dry_run=not args.apply)
        if not changes:
            print("Aucun numéro à migrer (déjà au format YYYY/MM/NN).")
            return
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"{mode} — {len(changes)} changement(s) :\n")
        for kind, old, new in changes:
            print(f"  {kind:8} {old!r:30} → {new}")
        if not args.apply:
            print("\nRelancez avec --apply pour enregistrer.")


if __name__ == "__main__":
    main()
