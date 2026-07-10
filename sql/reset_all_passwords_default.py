#!/usr/bin/env python3
"""
Remet le mot de passe de tous les utilisateurs à la valeur par défaut de l’app : passer123
(même règle que la création utilisateur sans mot de passe et l’action « activer par défaut »).

Usage (racine du projet, dossier contenant config.py) :
  PYTHONPATH=. python GestAvalon/sql/reset_all_passwords_default.py
  PYTHONPATH=. python GestAvalon/sql/reset_all_passwords_default.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_PASSWORD = "passer123"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les emails concernés sans modifier la base",
    )
    args = parser.parse_args()

    from GestAvalon.app import create_app
    from GestAvalon.app.extensions import bcrypt, db
    from GestAvalon.app.models.user import PasswordHistory, User

    app = create_app("default")
    with app.app_context():
        users = User.query.order_by(User.id).all()
        if args.dry_run:
            print(f"[dry-run] {len(users)} utilisateur(s) seraient mis à « {DEFAULT_PASSWORD} » :")
            for u in users:
                print(f"  id={u.id} email={u.email!r} role={u.role}")
            return

        count = 0
        for u in users:
            old_hash = u.password_hash
            u.password_hash = bcrypt.generate_password_hash(DEFAULT_PASSWORD, rounds=12).decode(
                "utf-8"
            )
            if old_hash:
                db.session.add(PasswordHistory(user_id=u.id, password_hash=old_hash))
            count += 1
        db.session.commit()
        print(f"{count} utilisateur(s) : mot de passe défini sur « {DEFAULT_PASSWORD} ».")
        print("Anciens hash enregistrés dans password_history.")


if __name__ == "__main__":
    main()
