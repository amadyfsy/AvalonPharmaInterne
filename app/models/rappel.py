"""Rappels & échéances administratives (marché, impôts, etc.)."""

from datetime import date, datetime

from ..extensions import db

RAPPEL_CATEGORIES = (
    ('marche', 'Marché / appel d\'offres'),
    ('impot', 'Impôts & fiscalité'),
    ('administratif', 'Administratif'),
    ('fournisseur', 'Fournisseur'),
    ('client', 'Client'),
    ('rh', 'Ressources humaines'),
    ('reglementaire', 'Réglementaire / ARP'),
    ('autre', 'Autre'),
)

RAPPEL_IMPORTANCES = (
    ('importante', 'Importante'),
    ('normale', 'Normale'),
    ('faible', 'Faible'),
)

RAPPEL_STATUTS = (
    ('en_cours', 'En cours'),
    ('valide', 'Validé'),
    ('reporte', 'Reporté'),
)

RAPPEL_FREQUENCES = (
    ('mensuelle', 'Mensuelle'),
    ('trimestrielle', 'Trimestrielle'),
    ('semestrielle', 'Semestrielle'),
    ('annuelle', 'Annuelle'),
)


class RappelRecurrence(db.Model):
    """Modèle enregistré pour générer automatiquement les échéances récurrentes."""

    __tablename__ = 'rappels_recurrence'

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    categorie = db.Column(db.String(40), nullable=False, default='autre', index=True)
    importance = db.Column(db.String(20), nullable=False, default='normale', index=True)
    frequence = db.Column(db.String(20), nullable=False, default='mensuelle')
    delai_limite_jours = db.Column(db.Integer, nullable=False, default=0)
    date_reference = db.Column(db.Date, nullable=False)
    actif = db.Column(db.Boolean, nullable=False, default=True, index=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    createur = db.relationship('User', foreign_keys=[created_by])
    occurrences = db.relationship('Rappel', back_populates='recurrence', lazy='dynamic')

    @property
    def categorie_label(self) -> str:
        return dict(RAPPEL_CATEGORIES).get(self.categorie, self.categorie)

    @property
    def importance_label(self) -> str:
        return dict(RAPPEL_IMPORTANCES).get(self.importance, self.importance)

    @property
    def frequence_label(self) -> str:
        return dict(RAPPEL_FREQUENCES).get(self.frequence, self.frequence)


class Rappel(db.Model):
    __tablename__ = 'rappels'

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    categorie = db.Column(db.String(40), nullable=False, default='autre', index=True)
    importance = db.Column(db.String(20), nullable=False, default='normale', index=True)
    date_prevue = db.Column(db.Date, nullable=False, index=True)
    date_limite = db.Column(db.Date, nullable=False, index=True)
    statut = db.Column(db.String(20), nullable=False, default='en_cours', index=True)
    recurrence_id = db.Column(
        db.Integer, db.ForeignKey('rappels_recurrence.id'), nullable=True, index=True
    )
    date_report = db.Column(db.Date, nullable=True)
    notes_report = db.Column(db.String(500), nullable=True)

    valide_par = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    valide_le = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    validateur = db.relationship('User', foreign_keys=[valide_par])
    createur = db.relationship('User', foreign_keys=[created_by])
    recurrence = db.relationship('RappelRecurrence', back_populates='occurrences')

    @property
    def est_recurrent(self) -> bool:
        return self.recurrence_id is not None

    @property
    def categorie_label(self) -> str:
        return dict(RAPPEL_CATEGORIES).get(self.categorie, self.categorie)

    @property
    def importance_label(self) -> str:
        return dict(RAPPEL_IMPORTANCES).get(self.importance, self.importance)

    @property
    def est_en_retard(self) -> bool:
        if self.statut == 'valide':
            return False
        lim = self.date_limite
        return bool(lim and lim < date.today())

    @property
    def est_a_traiter(self) -> bool:
        if self.statut == 'valide':
            return False
        prev = self.date_prevue
        return bool(prev and prev <= date.today())

    @property
    def priorite_affichage(self) -> str:
        if self.statut == 'valide':
            return 'valide'
        if self.est_en_retard:
            return 'retard'
        if self.est_a_traiter:
            return 'urgent'
        return 'planifie'
