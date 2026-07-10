from datetime import datetime

from ..extensions import db


class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    raison_sociale = db.Column(db.String(150), nullable=False)
    type_client = db.Column(db.Enum('hopital', 'clinique', 'pharmacie', 'grossiste', 'autre', name='type_clients'), nullable=False)
    contact = db.Column(db.String(100), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    adresse = db.Column(db.Text, nullable=True)
    ville = db.Column(db.String(100), nullable=True)
    nif_stat = db.Column(db.String(100), nullable=True)
    plafond_credit = db.Column(db.Numeric(12, 2), default=0.00)
    solde_encours = db.Column(db.Numeric(12, 2), default=0.00)
    remise_habituelle = db.Column(db.Numeric(5, 2), default=0.00)
    est_actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relations
    proformas = db.relationship('Proforma', backref='client', lazy=True)
    factures = db.relationship('Facture', backref='client', lazy=True)
    bons_livraison = db.relationship('BonLivraison', backref='client', lazy=True)
