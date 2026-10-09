from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional


class ParametresDocumentsForm(FlaskForm):
    raison_sociale = StringField("Raison sociale", validators=[Optional(), Length(max=255)])
    lieu_signature = StringField("Lieu (ville pour « …, le … »)", validators=[Optional(), Length(max=120)])
    adresse_ligne = StringField("Adresse / localisation", validators=[Optional(), Length(max=500)])
    telephone = StringField("Téléphone", validators=[Optional(), Length(max=120)])
    rc = StringField("RC", validators=[Optional(), Length(max=120)])
    ninea = StringField("NINEA", validators=[Optional(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Length(max=255)])
    compte_bancaire = StringField("Compte bancaire (ex. CBAO)", validators=[Optional(), Length(max=255)])
    devise_libelle = StringField("Libellé devise en lettres", validators=[Optional(), Length(max=80)])
    slogan = StringField("Slogan (à droite du logo sur les factures)", validators=[Optional(), Length(max=255)])
    site_web = StringField("Site web (QR code facture)", validators=[Optional(), Length(max=255)])
    pied_de_page = TextAreaField("Pied de page (PDF)", validators=[Optional()])
    logo = FileField(
        "Logo (en-tête PDF)",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif"], "Images uniquement")],
    )
    supprimer_logo = BooleanField("Supprimer le logo actuel")
    cachet = FileField(
        "Cachet / tampon (sous la date)",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif"], "Images uniquement")],
    )
    supprimer_cachet = BooleanField("Supprimer le cachet actuel")
    submit = SubmitField("Enregistrer")
