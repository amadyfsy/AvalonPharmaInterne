from datetime import datetime

from ..extensions import db


class CommandeFournisseur(db.Model):
    __tablename__ = 'commandes_fournisseurs'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False)
    date_commande = db.Column(db.Date, nullable=False)
    date_livraison_prevue = db.Column(db.Date, nullable=True)
    total_ht = db.Column(db.Numeric(12, 2), nullable=False)
    tva_montant = db.Column(db.Numeric(12, 2), nullable=False)
    total_ttc = db.Column(db.Numeric(12, 2), nullable=False)
    statut = db.Column(db.Enum('brouillon', 'envoyee', 'partiellement_recue', 'recue', 'annulee', name='statut_commandes'), default='brouillon')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lignes = db.relationship('LigneCommandeFournisseur', backref='commande', lazy=True, cascade='all, delete-orphan')

class LigneCommandeFournisseur(db.Model):
    __tablename__ = 'lignes_commande_fournisseur'
    id = db.Column(db.Integer, primary_key=True)
    commande_id = db.Column(db.Integer, db.ForeignKey('commandes_fournisseurs.id'), nullable=False)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    quantite_commandee = db.Column(db.Integer, nullable=False)
    quantite_recue = db.Column(db.Integer, default=0)
    prix_achat_ht = db.Column(db.Numeric(10, 2), nullable=False)

    produit = db.relationship('Produit')
