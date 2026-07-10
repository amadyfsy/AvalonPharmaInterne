from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class BaseVenteForm(FlaskForm):
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    date_emission = DateField('Date d\'émission', validators=[DataRequired()])
    remise_globale = DecimalField('Remise Globale', places=2, default=0)
    notes = TextAreaField('Notes')
    submit = SubmitField('Enregistrer')
