from datetime import datetime

from ..extensions import db


class PaiementClient(db.Model):
    """Encaissement client affecté à une facture."""

    __tablename__ = "paiements_clients"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)
    facture_id = db.Column(db.Integer, db.ForeignKey("factures.id"), nullable=True, index=True)
    reference = db.Column(db.String(50), nullable=False, index=True)
    montant = db.Column(db.Numeric(12, 2), nullable=False)
    mode_paiement = db.Column(db.String(50), nullable=False)
    date_paiement = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("Client", backref=db.backref("paiements", lazy="dynamic"))
    facture = db.relationship("Facture", backref=db.backref("paiements", lazy="dynamic"))
    createur = db.relationship("User")
