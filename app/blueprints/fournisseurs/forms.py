from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional

class FournisseurForm(FlaskForm):
    code = StringField('Code Fournisseur', validators=[DataRequired()])
    raison_sociale = StringField('Raison Sociale', validators=[DataRequired()])
    contact = StringField('Contact Principal', validators=[DataRequired()])
    telephone = StringField('Téléphone', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    adresse = TextAreaField('Adresse', validators=[Optional()])
    ville = StringField('Ville', validators=[Optional()])
    pays = StringField('Pays', validators=[Optional()])
    rib = StringField('RIB', validators=[Optional()])
    conditions_paiement = TextAreaField('Conditions de Paiement', validators=[Optional()])
    est_actif = BooleanField('Actif', default=True)
    submit = SubmitField('Enregistrer')
