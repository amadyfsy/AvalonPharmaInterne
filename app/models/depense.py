from datetime import datetime

from ..extensions import db


class CategorieDepense(db.Model):
    __tablename__ = 'categories_depenses'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type_depense = db.Column(db.Enum('fixe', 'variable', name='type_depenses'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Classe Bootstrap Icons, ex. "bi-truck" (affichée telle quelle dans class="...")
    icone = db.Column(db.String(80), nullable=True, default='bi-tag')
    # Code réservé pour liaisons automatiques (achats, ventes…) — NULL = catégorie libre
    code_systeme = db.Column(db.String(50), nullable=True, index=True)

class Depense(db.Model):
    __tablename__ = 'depenses'
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(50), unique=True, nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories_depenses.id'), nullable=False)
    type_depense = db.Column(db.Enum('fixe', 'variable', name='type_depenses'), nullable=False)
    libelle = db.Column(db.String(255), nullable=False)
    montant_ht = db.Column(db.Numeric(12, 2), nullable=False)
    tva = db.Column(db.Numeric(5, 2), default=0.00)
    montant_ttc = db.Column(db.Numeric(12, 2), nullable=False)
    date_depense = db.Column(db.Date, nullable=False)
    mode_paiement = db.Column(db.Enum('espece', 'cheque', 'virement', 'carte', name='mode_paiements'), nullable=False)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=True)
    justificatif = db.Column(db.String(255), nullable=True) # file path
    statut = db.Column(db.Enum('en_attente', 'valide', 'rejete', name='statut_depenses'), default='en_attente')
    valide_par = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    categorie = db.relationship('CategorieDepense')
    fournisseur = db.relationship('Fournisseur')
    validateur = db.relationship('User', foreign_keys=[valide_par])
    createur = db.relationship('User', foreign_keys=[created_by])
