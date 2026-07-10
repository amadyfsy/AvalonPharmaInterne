from datetime import datetime

from ..extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.Enum('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'EXPORT', 'PRINT', name='audit_actions'), nullable=False)
    module = db.Column(db.String(100), nullable=False)
    entite = db.Column(db.String(100), nullable=False)
    entite_id = db.Column(db.Integer, nullable=True)
    anciennes_valeurs = db.Column(db.JSON, nullable=True)
    nouvelles_valeurs = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')
