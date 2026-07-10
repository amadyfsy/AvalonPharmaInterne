from datetime import datetime

from ..extensions import db


class Stock(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    quantite_disponible = db.Column(db.Integer, default=0)
    quantite_reservee = db.Column(db.Integer, default=0)
    dernier_mouvement = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    produit_parent = db.relationship('Produit', back_populates='stock')

class MouvementStock(db.Model):
    __tablename__ = 'mouvements_stock'
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots.id'), nullable=True)
    type_mouvement = db.Column(db.Enum('entree', 'sortie', 'ajustement', 'retour', name='type_mouvements'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    motif = db.Column(db.String(255), nullable=True)
    reference_document = db.Column(db.String(100), nullable=True) # Facture, BL, Commande refs
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    produit = db.relationship('Produit')
    lot = db.relationship('Lot')
    utilisateur = db.relationship('User')
