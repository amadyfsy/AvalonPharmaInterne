from flask_wtf import FlaskForm
from wtforms import (DateField, DecimalField, FileField, SelectField,
                     StringField, SubmitField, TextAreaField)
from wtforms.validators import DataRequired, Length, Optional

# Icônes proposées à la création d’une catégorie (Bootstrap Icons)
CATEGORIE_DEPENSE_ICONES = [
    ('bi-patch-check', 'Impôt / Douane'),
    ('bi-person-badge', 'Badge / conformité'),
    ('bi-car-front', 'Auto & transport urbain'),
    ('bi-bus-front', 'Bus & transport collectif'),
    ('bi-truck', 'Camion / fret marchandises'),
    ('bi-building', 'Bâtiment / Douane'),
    ('bi-airplane', 'Avion / Fret aérien'),
    ('bi-fuel-pump', 'Carburant'),
    ('bi-tools', 'Outillage / Maintenance'),
    ('bi-receipt', 'Facture / Reçu'),
    ('bi-cart3', 'Achats'),
    ('bi-bag-check', 'Livraison'),
    ('bi-heart-pulse', 'Santé / Médical'),
    ('bi-hospital', 'Hôpital / Structure'),
    ('bi-wallet2', 'Portefeuille / salaires'),
    ('bi-cash-stack', 'Espèces / Paiement'),
    ('bi-bank', 'Banque'),
    ('bi-shield-check', 'Assurance / Conformité'),
    ('bi-globe', 'International'),
    ('bi-lightning', 'Urgent / Énergie'),
    ('bi-tag', 'Étiquette / Divers'),
    ('bi-three-dots', 'Autre'),
]


class CategorieDepenseForm(FlaskForm):
    nom = StringField('Nom de la catégorie', validators=[DataRequired(), Length(max=100)])
    type_depense = SelectField(
        'Type',
        choices=[('fixe', 'Fixe'), ('variable', 'Variable')],
        validators=[DataRequired()],
    )
    description = TextAreaField('Description', validators=[Optional()])
    icone = SelectField('Icône', choices=CATEGORIE_DEPENSE_ICONES, validators=[DataRequired()])
    submit = SubmitField('Enregistrer')


class DepenseForm(FlaskForm):
    categorie_id = SelectField('Catégorie', coerce=int, validators=[DataRequired()])
    # type_depense : dérivé de la catégorie (non saisi par l’utilisateur)
    libelle = StringField('Libellé', validators=[DataRequired()])
    montant_ht = DecimalField('Montant HT', places=2, validators=[DataRequired()])
    tva = DecimalField('TVA (%)', places=2, default=0)
    date_depense = DateField('Date', validators=[DataRequired()])
    mode_paiement = SelectField('Paiement', choices=[('espece', 'Espèce'), ('cheque', 'Chèque'), ('virement', 'Virement'), ('carte', 'Carte B.')], validators=[DataRequired()])
    # fournisseur : non saisi sur ce formulaire (lié automatiquement depuis commandes / autres flux si besoin)
    justificatif = FileField('Justificatif (PDF/Image)')
    submit = SubmitField('Enregistrer')
