from datetime import datetime

from ..extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # "notification" (métier) | "message" (sécurité/info)
    kind = db.Column(db.String(20), nullable=False, default="notification", index=True)
    icon = db.Column(db.String(50), nullable=False, default="bi-info-circle")
    title = db.Column(db.String(160), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    source_key = db.Column(db.String(120), nullable=True, index=True)

    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship("User")
