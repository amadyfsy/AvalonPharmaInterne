import os
import uuid

from werkzeug.utils import secure_filename

from ...extensions import db
from ...models.parametres_documents import ParametresDocuments
from ...utils.parametres_pdf import DEFAULT_COMPANY_EMAIL
from ...utils.decorators import role_required
from flask_login import login_required

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)

from . import parametres_bp
from .forms import ParametresDocumentsForm


def _parametres_upload_dir():
    base = current_app.config["UPLOAD_FOLDER"]
    d = os.path.join(base, "parametres")
    os.makedirs(d, exist_ok=True)
    return d


def _save_image_file(storage, prefix: str = "") -> str | None:
    if not storage or not storage.filename:
        return None
    ext = storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "gif"):
        raise ValueError("Format d’image non autorisé (png, jpg, gif).")
    name = f"{prefix}{uuid.uuid4().hex}.{ext}" if prefix else f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(_parametres_upload_dir(), name)
    storage.save(path)
    return name


def _save_logo_file(storage) -> str | None:
    return _save_image_file(storage)


def _remove_param_file(filename: str | None) -> None:
    if not filename:
        return
    old = os.path.join(_parametres_upload_dir(), filename)
    if os.path.isfile(old):
        try:
            os.remove(old)
        except OSError:
            pass


@parametres_bp.route("/documents", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def documents():
    row = ParametresDocuments.get_singleton()
    form = ParametresDocumentsForm(obj=row)

    if form.validate_on_submit():
        row.raison_sociale = form.raison_sociale.data or ""
        row.lieu_signature = form.lieu_signature.data or "St Louis"
        row.adresse_ligne = form.adresse_ligne.data or ""
        row.telephone = form.telephone.data or ""
        row.rc = form.rc.data or ""
        row.ninea = form.ninea.data or ""
        row.email = (form.email.data or "").strip() or DEFAULT_COMPANY_EMAIL
        row.compte_bancaire = form.compte_bancaire.data or ""
        dev = (form.devise_libelle.data or "").strip()
        row.devise_libelle = dev if dev else "francs"
        row.slogan = form.slogan.data or ""
        site = (form.site_web.data or "").strip()
        row.site_web = site if site else "https://avalonpharmasenegal.com"
        row.pied_de_page = form.pied_de_page.data or None

        if form.supprimer_logo.data and row.logo_filename:
            _remove_param_file(row.logo_filename)
            row.logo_filename = None

        if form.logo.data and form.logo.data.filename:
            try:
                new_name = _save_logo_file(form.logo.data)
                if new_name:
                    _remove_param_file(row.logo_filename)
                    row.logo_filename = new_name
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("parametres/documents.html", form=form, row=row)

        if form.supprimer_cachet.data and getattr(row, "cachet_filename", None):
            _remove_param_file(row.cachet_filename)
            row.cachet_filename = None

        if form.cachet.data and form.cachet.data.filename:
            try:
                new_name = _save_image_file(form.cachet.data, prefix="cachet_")
                if new_name:
                    _remove_param_file(getattr(row, "cachet_filename", None))
                    row.cachet_filename = new_name
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("parametres/documents.html", form=form, row=row)

        db.session.add(row)
        db.session.commit()
        flash("Paramètres documents enregistrés.", "success")
        return redirect(url_for("parametres.documents"))

    return render_template("parametres/documents.html", form=form, row=row)


@parametres_bp.route("/documents/logo/<path:filename>")
@login_required
def logo_file(filename):
    """Aperçu du logo ou du cachet (navigateur)."""
    safe = secure_filename(filename)
    if safe != filename or ".." in filename:
        abort(404)
    return send_from_directory(_parametres_upload_dir(), safe)
