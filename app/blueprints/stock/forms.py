from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError

class TvaPercentField(DecimalField):
    """
    TVA en % : chaîne vide ou absente → 0 %.
    Ne pas utiliser DataRequired() : Decimal('0') est « falsy » en Python et échouerait la validation.
    """

    def process_formdata(self, valuelist):
        if not valuelist or valuelist[0] in (None, ''):
            self.data = Decimal('0')
            return
        if isinstance(valuelist[0], str) and not valuelist[0].strip():
            self.data = Decimal('0')
            return
        super().process_formdata(valuelist)


class ProduitBaseForm(FlaskForm):
    """Champs communs création / édition produit."""

    reference = StringField('Référence', validators=[DataRequired()])
    designation = StringField('Nom commercial', validators=[DataRequired()])
    conditionnement_general = StringField('Conditionnement', validators=[Optional()])
    description = TextAreaField('Description')
    categorie_id = SelectField(
        'Catégorie',
        coerce=int,
        validators=[
            DataRequired(),
            NumberRange(
                min=1,
                message='Sélectionnez une catégorie réelle (pas une ligne vide du groupe).',
            ),
        ],
    )
    forme = SelectField(
        'Forme',
        choices=[
            ('comprime', 'Comprimé'),
            ('sirop', 'Sirop'),
            ('injectable', 'Injectable'),
            ('dispositif', 'Dispositif Médical'),
            ('autre', 'Autre'),
        ],
        validators=[DataRequired()],
    )
    unite = StringField('Unité', validators=[Optional()], default='unité')
    prix_achat_ht = DecimalField(
        'Prix Achat HT',
        places=2,
        default=Decimal('0'),
        validators=[Optional(), NumberRange(min=0)],
    )
    prix_vente_ht = DecimalField(
        'Prix Vente HT',
        places=2,
        default=Decimal('0'),
        validators=[Optional(), NumberRange(min=0)],
    )
    tva = TvaPercentField(
        'TVA (%)',
        places=2,
        default=Decimal('0'),
        validators=[NumberRange(min=0, max=100)],
    )
    seuil_alerte_stock = IntegerField(
        'Seuil Alerte Stock',
        default=0,
        validators=[Optional(), NumberRange(min=0)],
    )
    est_actif = BooleanField('Actif', default=True)

    # Liste remplie côté vue (identique au filtre catalogue produits : optgroups ou liste plate).
    specialite = SelectField(
        'Spécialité',
        choices=[('', '—')],
        coerce=str,
        validators=[Optional()],
    )

    # —— Médicaments & solutions (catégorie code medicaments) ——
    med_nom_commercial_dci = StringField('Nom commercial & DCI', validators=[Optional()])
    med_indication_therapeutique = StringField(
        'Indication thérapeutique', validators=[Optional()]
    )
    med_code_ucd_cip = StringField('Code UCD / CIP', validators=[Optional()])
    med_mode_administration = StringField('Mode d’administration', validators=[Optional()])

    # —— Dispositifs médicaux (code dispositifs) ——
    dm_type_dispositif = StringField('Type de dispositif', validators=[Optional()])
    dm_reference_sku = StringField('Référence (SKU)', validators=[Optional()])
    dm_taille_caracteristique = StringField(
        'Taille / caractéristique technique', validators=[Optional()]
    )
    dm_conditionnement = StringField('Conditionnement', validators=[Optional()])

    # —— Équipement biomédical (code equipement) ——
    eq_fonction_principale = StringField('Fonction principale', validators=[Optional()])
    eq_garantie_maintenance = StringField('Garantie & maintenance', validators=[Optional()])
    eq_formation_requise = StringField('Formation requise', validators=[Optional()])


class ProduitCreateForm(ProduitBaseForm):
    """Création : lot initial facultatif (n°, dates, fournisseur)."""

    numero_lot = StringField('N° de lot', validators=[Optional()])
    date_fabrication = DateField(
        'Date de production',
        validators=[Optional()],
        format='%Y-%m-%d',
    )
    date_peremption = DateField(
        'Date de péremption',
        validators=[Optional()],
        format='%Y-%m-%d',
    )
    fournisseur_lot_id = SelectField(
        'Fournisseur du lot',
        coerce=int,
    )
    quantite_lot_initiale = IntegerField(
        'Stock initial du lot',
        validators=[Optional(), NumberRange(min=0)],
        default=0,
    )

    def validate_numero_lot(self, field):
        raw = (field.data or '').strip()
        has_other = (
            self.date_fabrication.data
            or self.date_peremption.data
            or (self.fournisseur_lot_id.data is not None and int(self.fournisseur_lot_id.data) > 0)
            or ((self.quantite_lot_initiale.data or 0) > 0)
        )
        if has_other and not raw:
            raise ValidationError(
                'Indiquez un n° de lot si vous renseignez des dates ou un fournisseur, '
                'ou laissez toute la section lot vide.'
            )

    def validate_date_peremption(self, field):
        if self.date_fabrication.data and field.data:
            if field.data < self.date_fabrication.data:
                raise ValidationError(
                    'La date de péremption doit être postérieure ou égale à la date de production.'
                )

    submit = SubmitField('Enregistrer')


class ProduitEditForm(ProduitBaseForm):
    """Édition : pas de champs lot (lots gérés par réceptions / mouvements)."""

    submit = SubmitField('Enregistrer')


class MouvementStockForm(FlaskForm):
    produit_id = SelectField('Produit', coerce=int, validators=[DataRequired()])
    lot_id = SelectField('Lot', coerce=int, choices=[(0, '— Sélectionnez un lot —')])
    type_mouvement = SelectField(
        'Type de Mouvement',
        choices=[
            ('entree', 'Entrée Manuelle'),
            ('sortie', 'Sortie Manuelle'),
            ('ajustement', 'Ajustement (Inventaire)'),
            ('retour', 'Retour Produit'),
        ],
        validators=[DataRequired()],
    )
    quantite = IntegerField(
        'Quantité (en valeur absolue)',
        validators=[DataRequired(), NumberRange(min=1)],
    )
    motif = StringField('Motif')
    reference_document = StringField('Référence Document')
    submit = SubmitField('Enregistrer Mouvement')
