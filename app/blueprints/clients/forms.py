from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length

class ClientForm(FlaskForm):
    code = StringField('Code Client', validators=[DataRequired()])
    raison_sociale = StringField('Raison Sociale', validators=[DataRequired()])
    type_client = SelectField('Type', choices=[('hopital', 'Hôpital'), ('clinique', 'Clinique'), ('pharmacie', 'Pharmacie'), ('grossiste', 'Grossiste'), ('autre', 'Autre')], validators=[DataRequired()])
    contact = StringField('Contact', validators=[Optional()])
    telephone = StringField('Téléphone', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    adresse = TextAreaField('Adresse', validators=[Optional()])
    ville = StringField('Ville', validators=[Optional()])
    nif_stat = StringField('NIF/STAT', validators=[Optional()])
    plafond_credit = DecimalField('Plafond Crédit', places=2, default=0.0)
    remise_habituelle = DecimalField('Remise Habituelle (%)', places=2, default=0.0)
    est_actif = BooleanField('Actif', default=True)
    submit = SubmitField('Enregistrer')
