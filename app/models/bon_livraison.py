from datetime import datetime

from ..extensions import db


class BonLivraison(db.Model):
    __tablename__ = 'bons_livraison'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date_livraison = db.Column(db.Date, nullable=False)
    adresse_livraison = db.Column(db.Text, nullable=False)
    livreur = db.Column(db.String(100), nullable=True)
    statut = db.Column(db.Enum('prepare', 'livre', 'partiellement_livre', 'retourne', name='statut_bl'), default='prepare')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lignes = db.relationship('LigneBL', backref='bon_livraison', lazy=True, cascade='all, delete-orphan')

class LigneBL(db.Model):
    __tablename__ = 'lignes_bl'
    id = db.Column(db.Integer, primary_key=True)
    bl_id = db.Column(db.Integer, db.ForeignKey('bons_livraison.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots.id'), nullable=True)
    quantite_commandee = db.Column(db.Integer, nullable=False)
    quantite_livree = db.Column(db.Integer, default=0)

    produit = db.relationship('Produit')
    lot = db.relationship('Lot')
