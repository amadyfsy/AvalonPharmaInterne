from datetime import datetime

from ...extensions import db
from ...models.tresorerie import TresorerieOperation
from ...utils.decorators import permission_required
from flask_login import current_user, login_required

from flask import flash, redirect, render_template, url_for

from . import tresorerie_bp
from .forms import OperationForm


@tresorerie_bp.route('/')
@login_required
@permission_required('tresorerie', 'read')
def index():
    operations = TresorerieOperation.query.order_by(TresorerieOperation.created_at.desc()).all()
    # Need to calculate current solde... we will just query it dynamically in template or pass it
    solde_caisse = sum([op.montant if op.type_operation == 'entree' else -op.montant for op in TresorerieOperation.query.filter_by(type_compte='caisse').all()])
    solde_banque = sum([op.montant if op.type_operation == 'entree' else -op.montant for op in TresorerieOperation.query.filter_by(type_compte='banque').all()])
    return render_template('tresorerie/index.html', operations=operations, solde_caisse=solde_caisse, solde_banque=solde_banque)

@tresorerie_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
@permission_required('tresorerie', 'saisir')
def nouvelle_operation():
    form = OperationForm()
    if form.validate_on_submit():
        ops_avant = TresorerieOperation.query.filter_by(type_compte=form.type_compte.data).all()
        solde_avant = sum([op.montant if op.type_operation == 'entree' else -op.montant for op in ops_avant])
        nouveau_solde = solde_avant + form.montant.data if form.type_operation.data == 'entree' else solde_avant - form.montant.data

        operation = TresorerieOperation(
            type_compte=form.type_compte.data,
            type_operation=form.type_operation.data,
            libelle=form.libelle.data,
            montant=form.montant.data,
            reference_document=form.reference_document.data,
            date_operation=form.date_operation.data,
            solde_apres=nouveau_solde,
            created_by=current_user.id
        )
        db.session.add(operation)
        db.session.commit()
        flash('Opération enregistrée.', 'success')
        return redirect(url_for('tresorerie.index'))
    return render_template('tresorerie/form.html', form=form, title='Saisir Mouvement')
