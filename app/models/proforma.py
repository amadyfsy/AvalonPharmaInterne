from datetime import datetime

from ..extensions import db


class Proforma(db.Model):
    __tablename__ = 'proformas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date_emission = db.Column(db.Date, nullable=False)
    date_validite = db.Column(db.Date, nullable=False)
    remise_globale = db.Column(db.Numeric(10, 2), default=0.00)
    total_ht = db.Column(db.Numeric(12, 2), nullable=False)
    tva_montant = db.Column(db.Numeric(12, 2), nullable=False)
    total_ttc = db.Column(db.Numeric(12, 2), nullable=False)
    statut = db.Column(db.Enum('brouillon', 'envoye', 'accepte', 'refuse', 'converti', name='statut_proformas'), default='brouillon')
    notes = db.Column(db.Text, nullable=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lignes = db.relationship('LigneProforma', backref='proforma', lazy=True, cascade='all, delete-orphan')
    factures = db.relationship('Facture', backref='proforma_source', lazy=True)

class LigneProforma(db.Model):
    __tablename__ = 'lignes_proforma'
    id = db.Column(db.Integer, primary_key=True)
    proforma_id = db.Column(db.Integer, db.ForeignKey('proformas.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire_ht = db.Column(db.Numeric(10, 2), nullable=False)
    remise = db.Column(db.Numeric(10, 2), default=0.00)
    montant_ht = db.Column(db.Numeric(12, 2), nullable=False)

    produit = db.relationship('Produit')
