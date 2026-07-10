from datetime import date, datetime

from sqlalchemy import case, or_

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...extensions import db
from ...models.rappel import (
    RAPPEL_CATEGORIES,
    RAPPEL_FREQUENCES,
    RAPPEL_IMPORTANCES,
    RAPPEL_STATUTS,
    Rappel,
    RappelRecurrence,
)
from ...utils.decorators import permission_required, user_has_permission
from ...utils.rappel_recurrence import generer_prochain_rappel, synchroniser_rappels_recurrents
from . import rappels_bp
from .forms import RappelForm, RappelReporterForm

RAPPELS_PAR_PAGE = 20


@rappels_bp.route('/')
@login_required
@permission_required('rappels', 'read')
def index():
    synchroniser_rappels_recurrents()

    statut = (request.args.get('statut') or 'en_cours').strip()
    categorie = (request.args.get('categorie') or '').strip()
    importance = (request.args.get('importance') or '').strip()
    recurrent = (request.args.get('recurrent') or '').strip()
    q = (request.args.get('q') or '').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    allowed_statuts = {s[0] for s in RAPPEL_STATUTS} | {'tous'}
    if statut not in allowed_statuts:
        statut = 'en_cours'

    query = Rappel.query
    if statut != 'tous':
        query = query.filter(Rappel.statut == statut)
    if categorie:
        query = query.filter(Rappel.categorie == categorie)
    if importance:
        query = query.filter(Rappel.importance == importance)
    if recurrent == 'oui':
        query = query.filter(Rappel.recurrence_id.isnot(None))
    elif recurrent == 'non':
        query = query.filter(Rappel.recurrence_id.is_(None))
    if q:
        pattern = f'%{q}%'
        query = query.filter(
            or_(Rappel.titre.ilike(pattern), Rappel.description.ilike(pattern))
        )

    today = date.today()
    pagination = (
        query.order_by(
            case((Rappel.statut == 'valide', 1), else_=0),
            Rappel.date_limite.asc(),
            Rappel.id.desc(),
        )
        .paginate(page=page, per_page=RAPPELS_PAR_PAGE, error_out=False)
    )

    nb_en_cours = Rappel.query.filter_by(statut='en_cours').count()
    nb_retard = (
        Rappel.query.filter(
            Rappel.statut != 'valide',
            Rappel.date_limite < today,
        ).count()
    )
    nb_important = (
        Rappel.query.filter(
            Rappel.statut != 'valide',
            Rappel.importance == 'importante',
        ).count()
    )
    modeles_recurrents = (
        RappelRecurrence.query.order_by(RappelRecurrence.actif.desc(), RappelRecurrence.titre.asc())
        .all()
    )

    filtres_url = {}
    if statut != 'en_cours':
        filtres_url['statut'] = statut
    if categorie:
        filtres_url['categorie'] = categorie
    if importance:
        filtres_url['importance'] = importance
    if recurrent:
        filtres_url['recurrent'] = recurrent
    if q:
        filtres_url['q'] = q

    form = RappelForm()
    if not form.date_prevue.data:
        form.date_prevue.data = today
    if not form.date_limite.data:
        form.date_limite.data = today

    return render_template(
        'rappels/index.html',
        rappels=pagination.items,
        pagination=pagination,
        form=form,
        reporter_form=RappelReporterForm(),
        statut_filtre=statut,
        categorie_filtre=categorie,
        importance_filtre=importance,
        recurrent_filtre=recurrent,
        q=q,
        filtres_url=filtres_url,
        categories=RAPPEL_CATEGORIES,
        importances=RAPPEL_IMPORTANCES,
        frequences=RAPPEL_FREQUENCES,
        statuts=RAPPEL_STATUTS,
        modeles_recurrents=modeles_recurrents,
        nb_en_cours=nb_en_cours,
        nb_retard=nb_retard,
        nb_important=nb_important,
        today=today,
        peut_creer=user_has_permission(current_user, 'rappels', 'create'),
        peut_valider=user_has_permission(current_user, 'rappels', 'valider'),
        peut_supprimer=user_has_permission(current_user, 'rappels', 'delete'),
    )


@rappels_bp.route('/nouveau', methods=['POST'])
@login_required
@permission_required('rappels', 'create')
def nouveau():
    form = RappelForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for err in errors:
                flash(f'{field}: {err}', 'danger')
        return redirect(url_for('rappels.index'))

    if form.date_limite.data < form.date_prevue.data:
        flash('La date limite doit être postérieure ou égale à la date prévue.', 'danger')
        return redirect(url_for('rappels.index'))

    delai_jours = (form.date_limite.data - form.date_prevue.data).days
    recurrence_id = None

    if form.est_recurrent.data:
        modele = RappelRecurrence(
            titre=form.titre.data.strip(),
            description=(form.description.data or '').strip() or None,
            categorie=form.categorie.data,
            importance=form.importance.data,
            frequence=form.frequence.data or 'mensuelle',
            delai_limite_jours=delai_jours,
            date_reference=form.date_prevue.data,
            actif=True,
            created_by=current_user.id,
        )
        db.session.add(modele)
        db.session.flush()
        recurrence_id = modele.id

    r = Rappel(
        titre=form.titre.data.strip(),
        description=(form.description.data or '').strip() or None,
        categorie=form.categorie.data,
        importance=form.importance.data,
        date_prevue=form.date_prevue.data,
        date_limite=form.date_limite.data,
        statut='en_cours',
        recurrence_id=recurrence_id,
        created_by=current_user.id,
    )
    db.session.add(r)
    db.session.commit()

    if recurrence_id:
        flash('Rappel récurrent enregistré — les prochaines échéances seront créées automatiquement.', 'success')
    else:
        flash('Rappel enregistré.', 'success')
    return redirect(url_for('rappels.index'))


@rappels_bp.route('/<int:id>/valider', methods=['POST'])
@login_required
@permission_required('rappels', 'valider')
def valider(id):
    r = Rappel.query.get_or_404(id)
    if r.statut == 'valide':
        flash('Ce rappel est déjà validé.', 'info')
        return redirect(url_for('rappels.index', statut=request.args.get('statut', 'en_cours')))

    r.statut = 'valide'
    r.valide_par = current_user.id
    r.valide_le = datetime.utcnow()

    prochain = None
    if r.recurrence_id and r.recurrence and r.recurrence.actif:
        prochain = generer_prochain_rappel(
            r.recurrence,
            apres_date=r.date_prevue,
            created_by=current_user.id,
        )

    db.session.commit()

    if prochain:
        flash(
            f'Rappel « {r.titre} » traité. Prochaine échéance : '
            f'{prochain.date_prevue.strftime("%d/%m/%Y")}.',
            'success',
        )
    else:
        flash(f'Rappel « {r.titre} » marqué comme traité.', 'success')
    return redirect(request.referrer or url_for('rappels.index'))


@rappels_bp.route('/<int:id>/reporter', methods=['POST'])
@login_required
@permission_required('rappels', 'create')
def reporter(id):
    r = Rappel.query.get_or_404(id)
    if r.statut == 'valide':
        flash('Un rappel validé ne peut pas être reporté.', 'warning')
        return redirect(url_for('rappels.index'))

    form = RappelReporterForm()
    if not form.validate_on_submit():
        flash('Dates invalides pour le report.', 'danger')
        return redirect(url_for('rappels.index'))

    if form.date_limite.data < form.date_prevue.data:
        flash('La date limite doit être postérieure ou égale à la date prévue.', 'danger')
        return redirect(url_for('rappels.index'))

    r.date_prevue = form.date_prevue.data
    r.date_limite = form.date_limite.data
    r.date_report = date.today()
    r.notes_report = (form.notes_report.data or '').strip() or None
    r.statut = 'en_cours'

    if r.recurrence:
        r.recurrence.delai_limite_jours = (form.date_limite.data - form.date_prevue.data).days

    db.session.commit()
    flash(f'Rappel « {r.titre} » reporté au {form.date_prevue.data.strftime("%d/%m/%Y")}.', 'success')
    return redirect(request.referrer or url_for('rappels.index'))


@rappels_bp.route('/recurrence/<int:id>/activer', methods=['POST'])
@login_required
@permission_required('rappels', 'create')
def activer_recurrence(id):
    modele = RappelRecurrence.query.get_or_404(id)
    modele.actif = True
    generer_prochain_rappel(modele, created_by=current_user.id)
    db.session.commit()
    flash(f'Modèle récurrent « {modele.titre} » réactivé.', 'success')
    return redirect(request.referrer or url_for('rappels.index'))


@rappels_bp.route('/recurrence/<int:id>/desactiver', methods=['POST'])
@login_required
@permission_required('rappels', 'create')
def desactiver_recurrence(id):
    modele = RappelRecurrence.query.get_or_404(id)
    modele.actif = False
    db.session.commit()
    flash(f'Modèle récurrent « {modele.titre} » désactivé.', 'info')
    return redirect(request.referrer or url_for('rappels.index'))


@rappels_bp.route('/recurrence/<int:id>/supprimer', methods=['POST'])
@login_required
@permission_required('rappels', 'delete')
def supprimer_recurrence(id):
    modele = RappelRecurrence.query.get_or_404(id)
    titre = modele.titre
    for r in Rappel.query.filter_by(recurrence_id=modele.id, statut='en_cours').all():
        db.session.delete(r)
    db.session.delete(modele)
    db.session.commit()
    flash(f'Modèle récurrent « {titre} » supprimé.', 'info')
    return redirect(url_for('rappels.index'))


@rappels_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
@permission_required('rappels', 'delete')
def supprimer(id):
    r = Rappel.query.get_or_404(id)
    titre = r.titre
    db.session.delete(r)
    db.session.commit()
    flash(f'Rappel « {titre} » supprimé.', 'info')
    return redirect(url_for('rappels.index'))
