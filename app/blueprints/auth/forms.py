from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError


def _validate_login_identifier(form, field):
    value = (field.data or '').strip()
    if not value:
        raise ValidationError('Indiquez votre email ou numéro de téléphone.')
    if '@' in value:
        local, _, domain = value.partition('@')
        if not local or not domain or '.' not in domain:
            raise ValidationError('Adresse email invalide.')
    else:
        digits = ''.join(c for c in value if c.isdigit())
        if len(digits) < 8:
            raise ValidationError('Numéro de téléphone invalide.')


class LoginForm(FlaskForm):
    email = StringField(
        'Email ou téléphone',
        validators=[DataRequired(), Length(min=3, max=255), _validate_login_identifier],
    )
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Ancien mot de passe', validators=[DataRequired()])
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(), 
        Length(min=10, message="Le mot de passe doit faire au moins 10 caractères."),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$',
               message="Le mot de passe doit contenir au moins 1 majuscule, 1 minuscule, 1 chiffre et 1 caractère spécial.")
    ])
    confirm_password = PasswordField('Confirmer nouveau mot de passe', validators=[
        DataRequired(), EqualTo('new_password', message="Les mots de passe ne correspondent pas.")
    ])
    submit = SubmitField('Changer le mot de passe')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Envoyer le lien de réinitialisation')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(), 
        Length(min=10, message="Le mot de passe doit faire au moins 10 caractères."),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$',
               message="Le mot de passe doit contenir au moins 1 majuscule, 1 minuscule, 1 chiffre et 1 caractère spécial.")
    ])
    confirm_password = PasswordField('Confirmer nouveau mot de passe', validators=[
        DataRequired(), EqualTo('new_password', message="Les mots de passe ne correspondent pas.")
    ])
    submit = SubmitField('Réinitialiser le mot de passe')
