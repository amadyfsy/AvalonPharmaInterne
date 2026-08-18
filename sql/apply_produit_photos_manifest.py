#!/usr/bin/env python3
"""
Applique le manifeste local instance/produit_photos_manifest.json aux produits en base.

Prérequis : les fichiers doivent exister sous instance/uploads/ (ex. produits/xxx.jpg).

Usage :
  python sql/apply_produit_photos_manifest.py
  python sql/apply_produit_photos_manifest.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "instance" / "produit_photos_manifest.json"
UPLOAD_ROOT = ROOT / "instance" / "uploads"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not MANIFEST.is_file():
        print(f"Manifeste introuvable : {MANIFEST}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    from app import create_app
    from app.extensions import db
    from app.models.produit import Produit

    app = create_app()
    linked = missing_file = not_found = 0
    with app.app_context():
        for designation, info in manifest.items():
            if not info.get("ok"):
                continue
            stored = info.get("stored")
            if not stored:
                continue
            path = UPLOAD_ROOT / stored.replace("\\", "/").lstrip("/")
            if not path.is_file():
                print(f"⚠ fichier absent : {stored} ({designation})")
                missing_file += 1
                continue
            produit = Produit.query.filter_by(designation=designation).first()
            if not produit:
                print(f"⚠ produit introuvable en base : {designation}")
                not_found += 1
                continue
            if args.dry_run:
                print(f"→ {produit.reference} : {stored}")
                linked += 1
                continue
            produit.photo_principale = stored
            linked += 1
        if not args.dry_run:
            db.session.commit()

    print(f"Terminé : {linked} liés, {missing_file} fichiers absents, {not_found} produits introuvables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
