"""Paramètres d'impression (factures, BL, proformas) — ligne unique."""

from datetime import datetime

from sqlalchemy.exc import OperationalError, ProgrammingError

from ..extensions import db


def _is_missing_table_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if hasattr(exc, "orig") and exc.orig is not None:
        msg += " " + str(exc.orig).lower()
    return (
        "doesn't exist" in msg
        or "1146" in msg
        or "no such table" in msg
        or "sqlite3.operationalerror" in msg.replace(" ", "")
    )


class ParametresDocuments(db.Model):
    __tablename__ = "parametres_documents"

    id = db.Column(db.Integer, primary_key=True)
    raison_sociale = db.Column(db.String(255), nullable=False, default="")
    lieu_signature = db.Column(db.String(120), nullable=False, default="St Louis")
    adresse_ligne = db.Column(db.String(500), nullable=False, default="")
    telephone = db.Column(db.String(120), nullable=False, default="77 444 14 01 - 77 764 87 28")
    rc = db.Column(db.String(120), nullable=False, default="SN STL 2008B1250")
    ninea = db.Column(db.String(120), nullable=False, default="30835902K2")
    email = db.Column(db.String(255), nullable=False, default="avalonpharmasenegal@gmail.com")
    compte_bancaire = db.Column(
        db.String(255),
        nullable=False,
        default="CBAO : SN012 08274 036182246001 48",
    )
    logo_filename = db.Column(db.String(255), nullable=True)
    cachet_filename = db.Column(db.String(255), nullable=True)
    slogan = db.Column(db.String(255), nullable=False, default="Serving those who care for others")
    site_web = db.Column(db.String(255), nullable=False, default="https://avalonpharmasenegal.com")
    pied_de_page = db.Column(db.Text, nullable=True)
    devise_libelle = db.Column(db.String(80), nullable=False, default="francs")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_singleton(cls):
        """Retourne la ligne id=1 ; crée la table si elle n’existe pas encore (sans migration manuelle)."""

        defaults = {
            "telephone": "77 444 14 01 - 77 764 87 28",
            "email": "avalonpharmasenegal@gmail.com",
            "rc": "SN STL 2008B1250",
            "ninea": "30835902K2",
            "compte_bancaire": "CBAO : SN012 08274 036182246001 48",
        }

        def _ensure_cachet_column():
            """Ajoute cachet_filename si la colonne n’existe pas encore."""
            from sqlalchemy import inspect, text

            try:
                cols = {c["name"] for c in inspect(db.engine).get_columns("parametres_documents")}
            except Exception:
                return
            if "cachet_filename" in cols:
                return
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE parametres_documents "
                        "ADD COLUMN cachet_filename VARCHAR(255)"
                    )
                )
                db.session.commit()
            except Exception:
                db.session.rollback()

        def _ensure_company_coords(row):
            """Complète les coordonnées Avalon si absentes (facture = BL)."""
            changed = False
            for key, value in defaults.items():
                current = (getattr(row, key, None) or "").strip()
                if not current:
                    setattr(row, key, value)
                    changed = True
            if changed:
                db.session.commit()
            return row

        def _load_or_create():
            _ensure_cachet_column()
            row = db.session.get(cls, 1)
            if row is None:
                row = cls(id=1, **defaults)
                db.session.add(row)
                db.session.commit()
                return row
            return _ensure_company_coords(row)

        try:
            return _load_or_create()
        except (ProgrammingError, OperationalError) as e:
            if not _is_missing_table_error(e):
                db.session.rollback()
                raise
            db.session.rollback()
            db.create_all()
            return _load_or_create()
