from ...extensions import db
from ...models.fournisseur import Fournisseur
from ...utils.decorators import permission_required
from flask_login import login_required

from flask import flash, redirect, render_template, request, url_for

from . import fournisseurs_bp
from .forms import FournisseurForm


@fournisseurs_bp.route('/')
@login_required
@permission_required('achats', 'read')
def index():
    fournisseurs = Fournisseur.query.all()
    return render_template('fournisseurs/index.html', fournisseurs=fournisseurs)

@fournisseurs_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('achats', 'create')
def nouveau():
    form = FournisseurForm()
    if form.validate_on_submit():
        fournisseur = Fournisseur(
            code=form.code.data,
            raison_sociale=form.raison_sociale.data,
            contact=form.contact.data,
            telephone=form.telephone.data,
            email=form.email.data,
            adresse=form.adresse.data,
            ville=form.ville.data,
            pays=form.pays.data,
            rib=form.rib.data,
            conditions_paiement=form.conditions_paiement.data,
            est_actif=form.est_actif.data
        )
        db.session.add(fournisseur)
        db.session.commit()
        flash('Fournisseur ajouté avec succès.', 'success')
        return redirect(url_for('fournisseurs.index'))
    return render_template('fournisseurs/form.html', form=form, title="Nouveau Fournisseur")
