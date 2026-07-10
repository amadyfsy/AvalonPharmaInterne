from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (DateField, DecimalField, SelectField, StringField,
                     SubmitField)
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError

from ...models.employe import MOTIFS_SORTIE
from ...utils.paie_calcul import (
    DEFAULT_SEUIL_IRPP,
    DEFAULT_TAUX_CSS_PATRONAL,
    DEFAULT_TAUX_CSS_SALARIAL,
    DEFAULT_TAUX_IPRES_PATRONAL,
    DEFAULT_TAUX_IPRES_SALARIAL,
    DEFAULT_TAUX_IRPP,
)

_PCT_VALIDATORS = [Optional(), NumberRange(min=0, max=100)]


class EmployeForm(FlaskForm):
    matricule = StringField('Matricule', validators=[DataRequired()])
    nom = StringField('Nom', validators=[DataRequired()])
    prenom = StringField('Prénom', validators=[DataRequired()])
    date_naissance = DateField('Date Naissance', validators=[DataRequired()])
    cin = StringField('CIN', validators=[DataRequired()])
    telephone = StringField('Téléphone')
    email = StringField('Email')
    adresse = StringField('Adresse')
    poste = StringField('Poste', validators=[DataRequired()])
    departement = StringField('Département', validators=[DataRequired()])
    date_embauche = DateField('Date d\'embauche', validators=[DataRequired()])
    type_contrat = SelectField('Type', choices=[('CDI', 'CDI'), ('CDD', 'CDD'), ('Stage', 'Stage')], validators=[DataRequired()])
    date_fin_contrat = DateField('Date fin contrat', validators=[Optional()])
    salaire_base = DecimalField('Salaire de base', places=2, validators=[DataRequired()])
    taux_ipres_salarial = DecimalField(
        'IPRES salarial (%)',
        places=3,
        default=DEFAULT_TAUX_IPRES_SALARIAL,
        validators=_PCT_VALIDATORS,
    )
    taux_css_salarial = DecimalField(
        'CSS salariale (%)',
        places=3,
        default=DEFAULT_TAUX_CSS_SALARIAL,
        validators=_PCT_VALIDATORS,
    )
    taux_ipres_patronal = DecimalField(
        'IPRES patronale (%)',
        places=3,
        default=DEFAULT_TAUX_IPRES_PATRONAL,
        validators=_PCT_VALIDATORS,
    )
    taux_css_patronal = DecimalField(
        'CSS patronale (%)',
        places=3,
        default=DEFAULT_TAUX_CSS_PATRONAL,
        validators=_PCT_VALIDATORS,
    )
    seuil_irpp = DecimalField(
        'Seuil IRPP (FCFA)',
        places=2,
        default=DEFAULT_SEUIL_IRPP,
        validators=[Optional(), NumberRange(min=0)],
    )
    taux_irpp = DecimalField(
        'Taux IRPP (%)',
        places=3,
        default=DEFAULT_TAUX_IRPP,
        validators=_PCT_VALIDATORS,
    )
    rib_bancaire = StringField('RIB')
    document_cin = FileField('Copie CIN (PDF/Image)', validators=[FileAllowed(['jpg', 'png', 'pdf'], 'Images et PDF uniquement.')])
    document_contrat = FileField('Contrat signé (PDF/Image)', validators=[FileAllowed(['jpg', 'png', 'pdf'], 'Images et PDF uniquement.')])
    submit = SubmitField('Enregistrer')

    def validate_date_fin_contrat(self, field):
        tc = self.type_contrat.data
        if tc in ('CDD', 'Stage'):
            if not field.data:
                raise ValidationError("La date de fin de contrat est obligatoire pour un CDD ou un Stage.")
            if self.date_embauche.data and field.data < self.date_embauche.data:
                raise ValidationError("La date de fin de contrat doit être postérieure ou égale à la date d'embauche.")

class CongeForm(FlaskForm):
    employe_id = SelectField('Employé', coerce=int, validators=[DataRequired()])
    type_conge = SelectField('Type', choices=[('annuel', 'Annuel'), ('maladie', 'Maladie'), ('maternite', 'Maternité'), ('sans_solde', 'Sans Solde')], validators=[DataRequired()])
    date_debut = DateField('Date début', validators=[DataRequired()])
    date_fin = DateField('Date fin', validators=[DataRequired()])
    motif = StringField('Motif')
    submit = SubmitField('Demander Congé')


class EmployeSortieForm(FlaskForm):
    motif_sortie = SelectField(
        'Motif de sortie',
        choices=MOTIFS_SORTIE,
        validators=[DataRequired()],
    )
    date_sortie = DateField('Date de sortie', validators=[DataRequired()], format='%Y-%m-%d')
    notes_sortie = StringField('Commentaire (optionnel)', validators=[Optional()])
    submit = SubmitField('Confirmer la sortie')
