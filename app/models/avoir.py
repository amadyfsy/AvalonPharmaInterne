from datetime import datetime

from ..extensions import db


class Avoir(db.Model):
    """Avoir client : quantités facturées qui n'ont pas pu être livrées."""

    __tablename__ = "avoirs"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False, index=True)
    facture_id = db.Column(db.Integer, db.ForeignKey("factures.id"), nullable=False, index=True)
    bl_id = db.Column(db.Integer, db.ForeignKey("bons_livraison.id"), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    date_emission = db.Column(db.Date, nullable=False)
    motif = db.Column(db.Text, nullable=True)
    total_ht = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tva_montant = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_ttc = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    facture = db.relationship("Facture", backref=db.backref("avoirs", lazy="dynamic"))
    bon_livraison = db.relationship("BonLivraison", backref=db.backref("avoirs", lazy="dynamic"))
    client = db.relationship("Client")
    createur = db.relationship("User")
    lignes = db.relationship(
        "LigneAvoir",
        backref="avoir",
        lazy=True,
        cascade="all, delete-orphan",
    )


class LigneAvoir(db.Model):
    __tablename__ = "lignes_avoir"

    id = db.Column(db.Integer, primary_key=True)
    avoir_id = db.Column(db.Integer, db.ForeignKey("avoirs.id"), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey("produits.id"), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire_ht = db.Column(db.Numeric(10, 2), nullable=False)
    montant_ht = db.Column(db.Numeric(12, 2), nullable=False)
    tva_montant = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    produit = db.relationship("Produit")
