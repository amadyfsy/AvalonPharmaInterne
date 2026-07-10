from datetime import datetime

from ..extensions import db


class Facture(db.Model):
    __tablename__ = 'factures'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    proforma_id = db.Column(db.Integer, db.ForeignKey('proformas.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date_emission = db.Column(db.Date, nullable=False)
    date_echeance = db.Column(db.Date, nullable=False)
    remise_globale = db.Column(db.Numeric(10, 2), default=0.00)
    total_ht = db.Column(db.Numeric(12, 2), nullable=False)
    tva_montant = db.Column(db.Numeric(12, 2), nullable=False)
    total_ttc = db.Column(db.Numeric(12, 2), nullable=False)
    statut = db.Column(db.Enum('brouillon', 'emise', 'partiellement_payee', 'payee', 'annulee', name='statut_factures'), default='brouillon')
    mode_paiement = db.Column(db.String(50), nullable=True)
    bc = db.Column(db.String(80), nullable=True)
    montant_paye = db.Column(db.Numeric(12, 2), default=0.00)
    reste_a_payer = db.Column(db.Numeric(12, 2), nullable=False)
    commercial_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lignes = db.relationship('LigneFacture', backref='facture', lazy=True, cascade='all, delete-orphan')

class LigneFacture(db.Model):
    __tablename__ = 'lignes_facture'
    id = db.Column(db.Integer, primary_key=True)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots.id'), nullable=True)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire_ht = db.Column(db.Numeric(10, 2), nullable=False)
    remise = db.Column(db.Numeric(10, 2), default=0.00)
    montant_ht = db.Column(db.Numeric(12, 2), nullable=False)

    produit = db.relationship('Produit')
    lot = db.relationship('Lot')
