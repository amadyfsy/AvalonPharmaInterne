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
    rc = db.Column(db.String(120), nullable=False, default="")
    ninea = db.Column(db.String(120), nullable=False, default="")
    email = db.Column(db.String(255), nullable=False, default="avalonpharmasenegal@gmail.com")
    compte_bancaire = db.Column(db.String(255), nullable=False, default="")
    logo_filename = db.Column(db.String(255), nullable=True)
    slogan = db.Column(db.String(255), nullable=False, default="Serving those who care for others")
    site_web = db.Column(db.String(255), nullable=False, default="https://avalonpharmasenegal.com")
    pied_de_page = db.Column(db.Text, nullable=True)
    devise_libelle = db.Column(db.String(80), nullable=False, default="francs")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_singleton(cls):
        """Retourne la ligne id=1 ; crée la table si elle n’existe pas encore (sans migration manuelle)."""

        def _load_or_create():
            row = db.session.get(cls, 1)
            if row is None:
                row = cls(id=1)
                db.session.add(row)
                db.session.commit()
            return row

        try:
            return _load_or_create()
        except (ProgrammingError, OperationalError) as e:
            if not _is_missing_table_error(e):
                db.session.rollback()
                raise
            db.session.rollback()
            db.create_all()
            return _load_or_create()
