from datetime import datetime

from ..extensions import db


class Fournisseur(db.Model):
    __tablename__ = 'fournisseurs'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    raison_sociale = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(100), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    adresse = db.Column(db.Text, nullable=True)
    ville = db.Column(db.String(100), nullable=True)
    pays = db.Column(db.String(100), nullable=True)
    rib = db.Column(db.String(255), nullable=True) # Encrypted
    conditions_paiement = db.Column(db.Text, nullable=True)
    est_actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # NOTE: Commandes relation will be configured in commande.py to avoid circular imports? No, it's fine via string.
    # We will declare relations in their respective file if they are big or just string reference
    commandes = db.relationship('CommandeFournisseur', backref='fournisseur', lazy=True)
