from datetime import datetime

from ..extensions import db


class CategorieProduit(db.Model):
    __tablename__ = 'categories_produits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # medicaments | dispositifs | equipement | NULL = formulaire catalogue générique uniquement
    code_formulaire = db.Column(db.String(50), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    produits = db.relationship('Produit', backref='categorie', lazy=True)

class Produit(db.Model):
    __tablename__ = 'produits'
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    designation = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categories_produits.id'), nullable=False)
    forme = db.Column(db.Enum('comprime', 'sirop', 'injectable', 'dispositif', 'autre', name='forme_produit'), nullable=False)
    unite = db.Column(db.String(50), nullable=False)
    prix_achat_ht = db.Column(db.Numeric(10, 2), nullable=False)
    prix_vente_ht = db.Column(db.Numeric(10, 2), nullable=False)
    tva = db.Column(db.Numeric(5, 2), nullable=False) # percentage
    prix_vente_ttc = db.Column(db.Numeric(10, 2), nullable=False)
    seuil_alerte_stock = db.Column(db.Integer, nullable=False)
    est_actif = db.Column(db.Boolean, default=True)
    # Champs spécifiques selon categorie.code_formulaire (JSON)
    donnees_metier = db.Column(db.JSON, nullable=True)
    # Photo principale (catalogue / futur site public) — chemin relatif uploads/produits/…
    photo_principale = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lots = db.relationship('Lot', backref='produit_parent', lazy=True)
    stock = db.relationship('Stock', back_populates='produit_parent', uselist=False)
    photos_galerie = db.relationship(
        'ProduitPhoto',
        backref='produit',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ProduitPhoto.ordre',
    )


class ProduitPhoto(db.Model):
    """Photos secondaires (galerie) — site public / catalogue."""
    __tablename__ = 'produit_photos'
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    fichier = db.Column(db.String(255), nullable=False)
    ordre = db.Column(db.Integer, nullable=False, default=0)
    legende = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Lot(db.Model):
    __tablename__ = 'lots'
    id = db.Column(db.Integer, primary_key=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False)
    numero_lot = db.Column(db.String(100), nullable=False)
    date_fabrication = db.Column(db.Date, nullable=True)
    date_peremption = db.Column(db.Date, nullable=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=True)
    quantite_initiale = db.Column(db.Integer, nullable=False)
    # Stock disponible courant du lot (source de vérité pour le stock produit agrégé)
    quantite_disponible = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fournisseur = db.relationship('Fournisseur', foreign_keys=[fournisseur_id], lazy='joined')
