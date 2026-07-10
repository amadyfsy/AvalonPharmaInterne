from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from ...models.rappel import RAPPEL_CATEGORIES, RAPPEL_FREQUENCES, RAPPEL_IMPORTANCES


class RappelForm(FlaskForm):
    titre = StringField('Titre', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    categorie = SelectField(
        'Catégorie',
        choices=RAPPEL_CATEGORIES,
        validators=[DataRequired()],
    )
    importance = SelectField(
        'Importance',
        choices=RAPPEL_IMPORTANCES,
        validators=[DataRequired()],
    )
    date_prevue = DateField('Date prévue', validators=[DataRequired()], format='%Y-%m-%d')
    date_limite = DateField('Date limite', validators=[DataRequired()], format='%Y-%m-%d')
    est_recurrent = BooleanField('Rappel récurrent (génération automatique)')
    frequence = SelectField(
        'Fréquence',
        choices=RAPPEL_FREQUENCES,
        validators=[Optional()],
        default='mensuelle',
    )
    submit = SubmitField('Enregistrer')


class RappelReporterForm(FlaskForm):
    date_prevue = DateField('Nouvelle date prévue', validators=[DataRequired()], format='%Y-%m-%d')
    date_limite = DateField('Nouvelle date limite', validators=[DataRequired()], format='%Y-%m-%d')
    notes_report = StringField('Motif (optionnel)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Reporter')
