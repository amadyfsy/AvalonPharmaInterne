from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class CommandeForm(FlaskForm):
    fournisseur_id = SelectField('Fournisseur', coerce=int, validators=[DataRequired()])
    date_commande = DateField('Date de commande', validators=[DataRequired()])
    date_livraison_prevue = DateField('Date de livraison prévue', validators=[DataRequired()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Créer Commande')
