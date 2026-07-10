from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired

class OperationForm(FlaskForm):
    type_compte = SelectField('Compte', choices=[('caisse', 'Caisse'), ('banque', 'Banque')], validators=[DataRequired()])
    type_operation = SelectField('Type', choices=[('entree', 'Entrée (+)'), ('sortie', 'Sortie (-)')], validators=[DataRequired()])
    libelle = StringField('Libellé', validators=[DataRequired()])
    montant = DecimalField('Montant', places=2, validators=[DataRequired()])
    reference_document = StringField('Référence (Facture, Reçu, etc.)')
    date_operation = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Enregistrer')
