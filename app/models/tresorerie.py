from datetime import datetime

from ..extensions import db


class TresorerieOperation(db.Model):
    __tablename__ = 'tresorerie_operations'
    id = db.Column(db.Integer, primary_key=True)
    type_compte = db.Column(db.Enum('caisse', 'banque', name='type_comptes'), nullable=False)
    type_operation = db.Column(db.Enum('entree', 'sortie', name='type_operations'), nullable=False)
    libelle = db.Column(db.String(255), nullable=False)
    montant = db.Column(db.Numeric(12, 2), nullable=False)
    reference_document = db.Column(db.String(100), nullable=True)
    date_operation = db.Column(db.Date, nullable=False)
    solde_apres = db.Column(db.Numeric(15, 2), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    createur = db.relationship('User')
