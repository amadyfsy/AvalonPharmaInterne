import datetime

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models.employe import MOTIFS_SORTIE, Conge, Employe, Paie
from ...models.user import User
from ...utils.decorators import permission_required, user_has_permission
from ...utils.depense_paie import creer_depense_paie
from ...utils.paie_calcul import calculer_bulletin_paie, libelle_periode_paie
from ...utils.parametres_pdf import merge_browser_print_logo, pdf_company_context
from ...utils.pdf_generator import generate_pdf
from ...utils.auth_identifiant import format_phone_storage
from ...utils.security import decrypt_data, encrypt_data, secure_upload
from flask_login import current_user, login_required

from flask import flash, redirect, render_template, request, send_file, url_for

from . import rh_bp
from .forms import CongeForm, EmployeForm, EmployeSortieForm

PAIES_PAR_PAGE = 15
EMPLOYES_PAR_PAGE = 15
CONGES_PAR_PAGE = 15


def _decrypt_field(value: str | None) -> str:
    if not value:
        return ''
    try:
        return decrypt_data(value) or ''
    except ValueError:
        return ''


def _resume_paie_employe(employe_id: int) -> dict:
    paies = (
        Paie.query.filter_by(employe_id=employe_id)
        .order_by(Paie.annee.desc(), Paie.mois.desc(), Paie.id.desc())
        .all()
    )
    total_genere = sum(float(p.net_a_payer or 0) for p in paies if p.statut != 'paye')
    total_paye = sum(float(p.net_a_payer or 0) for p in paies if p.statut == 'paye')
    return {
        'paies': paies,
        'paies_impayees': [p for p in paies if p.statut != 'paye'],
        'solde_a_payer': max(total_genere, 0.0),
        'total_paye': total_paye,
        'nb_impayes': sum(1 for p in paies if p.statut != 'paye'),
    }


def _soldes_par_employe() -> dict[int, float]:
    paies = Paie.query.filter(Paie.statut != 'paye').all()
    soldes: dict[int, float] = {}
    for p in paies:
        soldes[p.employe_id] = soldes.get(p.employe_id, 0.0) + float(p.net_a_payer or 0)
    return soldes


def _populate_employe_form(form: EmployeForm, employe: Employe) -> None:
    form.matricule.data = employe.matricule
    form.nom.data = employe.nom
    form.prenom.data = employe.prenom
    form.date_naissance.data = employe.date_naissance
    form.cin.data = _decrypt_field(employe.cin)
    form.telephone.data = employe.telephone
    form.email.data = employe.email
    form.adresse.data = employe.adresse
    form.poste.data = employe.poste
    form.departement.data = employe.departement
    form.date_embauche.data = employe.date_embauche
    form.type_contrat.data = employe.type_contrat
    form.date_fin_contrat.data = employe.date_fin_contrat
    form.salaire_base.data = employe.salaire_base
    form.taux_ipres_salarial.data = employe.taux_ipres_salarial
    form.taux_css_salarial.data = employe.taux_css_salarial
    form.taux_ipres_patronal.data = employe.taux_ipres_patronal
    form.taux_css_patronal.data = employe.taux_css_patronal
    form.seuil_irpp.data = employe.seuil_irpp
    form.taux_irpp.data = employe.taux_irpp
    form.rib_bancaire.data = _decrypt_field(employe.rib_bancaire)


def _apply_employe_form(employe: Employe, form: EmployeForm, *, is_new: bool) -> str | None:
    """Applique le formulaire sur l'employé. Retourne un message d'erreur ou None."""
    matricule = (form.matricule.data or '').strip()
    email = (form.email.data or '').strip() or None

    q_mat = Employe.query.filter(Employe.matricule == matricule)
    if not is_new:
        q_mat = q_mat.filter(Employe.id != employe.id)
    if q_mat.first():
        return 'Ce matricule est déjà utilisé.'

    if email:
        q_email = Employe.query.filter(Employe.email == email)
        if not is_new:
            q_email = q_email.filter(Employe.id != employe.id)
        if q_email.first():
            return 'Cet e-mail est déjà utilisé par un autre employé.'

    try:
        enc_cin = encrypt_data(form.cin.data) if form.cin.data else None
        enc_rib = encrypt_data(form.rib_bancaire.data) if form.rib_bancaire.data else None
    except ValueError:
        return "ENCRYPTION_KEY n'est pas définie. Configurez-la avant d'enregistrer."

    employe.matricule = matricule
    employe.nom = form.nom.data.strip()
    employe.prenom = form.prenom.data.strip()
    employe.date_naissance = form.date_naissance.data
    employe.cin = enc_cin
    employe.telephone = (form.telephone.data or '').strip() or None
    employe.email = email
    employe.adresse = (form.adresse.data or '').strip() or None
    employe.poste = form.poste.data.strip()
    employe.departement = form.departement.data.strip()
    employe.date_embauche = form.date_embauche.data
    employe.type_contrat = form.type_contrat.data
    employe.date_fin_contrat = form.date_fin_contrat.data
    employe.salaire_base = form.salaire_base.data
    employe.taux_ipres_salarial = form.taux_ipres_salarial.data if form.taux_ipres_salarial.data is not None else 5.6
    employe.taux_css_salarial = form.taux_css_salarial.data if form.taux_css_salarial.data is not None else 7.0
    employe.taux_ipres_patronal = form.taux_ipres_patronal.data if form.taux_ipres_patronal.data is not None else 8.4
    employe.taux_css_patronal = form.taux_css_patronal.data if form.taux_css_patronal.data is not None else 14.0
    employe.seuil_irpp = form.seuil_irpp.data if form.seuil_irpp.data is not None else 30000
    employe.taux_irpp = form.taux_irpp.data if form.taux_irpp.data is not None else 10.0
    employe.rib_bancaire = enc_rib
    if employe.user_id:
        linked_user = User.query.get(employe.user_id)
        if linked_user:
            linked_user.telephone = format_phone_storage(employe.telephone)
    return None


@rh_bp.route('/')
@login_required
@permission_required('rh', 'read')
def index():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    statut = (request.args.get('statut') or 'actif').strip()
    allowed = {'actif', 'inactif', 'suspendu', 'tous'}
    if statut not in allowed:
        statut = 'actif'

    query = Employe.query
    if statut != 'tous':
        query = query.filter(Employe.statut == statut)

    pagination = (
        query.order_by(Employe.nom.asc(), Employe.prenom.asc())
        .paginate(page=page, per_page=EMPLOYES_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if statut != 'actif':
        filtres_url['statut'] = statut

    soldes = _soldes_par_employe()
    peut_modifier = user_has_permission(current_user, 'rh', 'update')
    return render_template(
        'rh/employes.html',
        employes=pagination.items,
        pagination=pagination,
        filtres_url=filtres_url,
        soldes=soldes,
        statut_filtre=statut,
        peut_modifier=peut_modifier,
    )

@rh_bp.route('/employes/<int:id>')
@login_required
@permission_required('rh', 'read')
def detail_employe(id):
    employe = Employe.query.get_or_404(id)
    try:
        cin = decrypt_data(employe.cin) if employe.cin else None
        rib = decrypt_data(employe.rib_bancaire) if employe.rib_bancaire else None
    except ValueError:
        cin = '***'
        rib = '***'
        flash(
            "ENCRYPTION_KEY n'est pas configurée : données sensibles masquées.",
            "warning",
        )
    # Congés annuels: synthèse des 5 dernières années depuis la date d'embauche
    today = datetime.date.today()
    year_start = today.year - 4
    if employe.date_embauche:
        year_start = max(year_start, employe.date_embauche.year)
    years = [y for y in range(year_start, today.year + 1)]
    conges_annuels = (
        Conge.query.filter_by(
            employe_id=employe.id,
            type_conge='annuel',
            statut='approuve',
        ).all()
    )
    pris_par_annee = {}
    for c in conges_annuels:
        if not c.date_debut:
            continue
        y = c.date_debut.year
        pris_par_annee[y] = float(pris_par_annee.get(y, 0)) + float(c.nb_jours or 0)

    quota_annuel = 30.0
    recap_conges = []
    for y in years:
        if not employe.date_embauche or y < employe.date_embauche.year:
            acquis = 0.0
        elif y > employe.date_embauche.year:
            acquis = quota_annuel
        else:
            # Prorata sur l'année d'embauche (du jour d'embauche au 31/12)
            debut = employe.date_embauche
            fin = datetime.date(y, 12, 31)
            jours_restants = (fin - debut).days + 1
            jours_annee = 366 if ((y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)) else 365
            acquis = round((quota_annuel * jours_restants) / jours_annee, 1)
        pris = float(pris_par_annee.get(y, 0.0))
        restant = acquis - pris
        recap_conges.append(
            {
                'annee': y,
                'acquis': acquis,
                'pris': pris,
                'restant': restant,
            }
        )
    demandes_conges = (
        Conge.query.filter_by(employe_id=employe.id)
        .order_by(Conge.date_debut.desc(), Conge.created_at.desc())
        .all()
    )
    resume_paie = _resume_paie_employe(employe.id)
    peut_modifier = user_has_permission(current_user, 'rh', 'update')
    sortie_form = EmployeSortieForm()
    if not sortie_form.date_sortie.data:
        sortie_form.date_sortie.data = today
    return render_template(
        'rh/employe_detail.html',
        employe=employe,
        cin=cin,
        rib=rib,
        recap_conges=recap_conges,
        quota_annuel=quota_annuel,
        demandes_conges=demandes_conges,
        paies_employe=resume_paie['paies'],
        paies_impayees=resume_paie['paies_impayees'],
        somme_a_payer=resume_paie['solde_a_payer'],
        solde_paie=resume_paie['solde_a_payer'],
        total_paye=resume_paie['total_paye'],
        nb_paies_impayees=resume_paie['nb_impayes'],
        motifs_sortie=MOTIFS_SORTIE,
        sortie_form=sortie_form,
        peut_modifier=peut_modifier,
    )

@rh_bp.route('/employes/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('rh', 'create')
def nouvel_employe():
    form = EmployeForm()
    if form.validate_on_submit():
        employe = Employe()
        err = _apply_employe_form(employe, form, is_new=True)
        if err:
            flash(err, 'danger')
            return render_template('rh/form_employe.html', form=form, title='Nouvel Employé')

        try:
            if form.document_cin.data and form.document_cin.data.filename:
                employe.document_cin = secure_upload(form.document_cin.data)
            if form.document_contrat.data and form.document_contrat.data.filename:
                employe.document_contrat = secure_upload(form.document_contrat.data)
        except Exception as e:
            flash(f"Erreur lors de l'upload des documents : {str(e)}", "danger")
            return render_template('rh/form_employe.html', form=form, title='Nouvel Employé')

        db.session.add(employe)
        db.session.commit()
        flash('Employé enregistré avec succès.', 'success')
        return redirect(url_for('rh.detail_employe', id=employe.id))
    return render_template('rh/form_employe.html', form=form, title='Nouvel Employé')


@rh_bp.route('/employes/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@permission_required('rh', 'update')
def modifier_employe(id):
    employe = Employe.query.get_or_404(id)
    form = EmployeForm()
    form.submit.label.text = 'Enregistrer les modifications'

    if request.method == 'GET':
        _populate_employe_form(form, employe)

    if form.validate_on_submit():
        err = _apply_employe_form(employe, form, is_new=False)
        if err:
            flash(err, 'danger')
            return render_template(
                'rh/form_employe.html',
                form=form,
                title=f'Modifier — {employe.nom} {employe.prenom}',
                employe=employe,
            )

        try:
            if form.document_cin.data and form.document_cin.data.filename:
                employe.document_cin = secure_upload(form.document_cin.data)
            if form.document_contrat.data and form.document_contrat.data.filename:
                employe.document_contrat = secure_upload(form.document_contrat.data)
        except Exception as e:
            flash(f"Erreur lors de l'upload des documents : {str(e)}", "danger")
            return render_template(
                'rh/form_employe.html',
                form=form,
                title=f'Modifier — {employe.nom} {employe.prenom}',
                employe=employe,
            )

        db.session.commit()
        flash('Informations employé mises à jour.', 'success')
        return redirect(url_for('rh.detail_employe', id=employe.id))

    return render_template(
        'rh/form_employe.html',
        form=form,
        title=f'Modifier — {employe.nom} {employe.prenom}',
        employe=employe,
    )


@rh_bp.route('/employes/<int:id>/sortie', methods=['POST'])
@login_required
@permission_required('rh', 'update')
def sortie_employe(id):
    employe = Employe.query.get_or_404(id)
    if employe.statut == 'inactif':
        flash('Cet employé est déjà sorti.', 'info')
        return redirect(url_for('rh.detail_employe', id=employe.id))

    form = EmployeSortieForm()
    if not form.validate_on_submit():
        flash('Formulaire de sortie invalide.', 'danger')
        return redirect(url_for('rh.detail_employe', id=employe.id))

    if employe.date_embauche and form.date_sortie.data < employe.date_embauche:
        flash('La date de sortie ne peut pas être antérieure à la date d\'embauche.', 'danger')
        return redirect(url_for('rh.detail_employe', id=employe.id))

    employe.statut = 'inactif'
    employe.date_sortie = form.date_sortie.data
    employe.motif_sortie = form.motif_sortie.data
    employe.notes_sortie = (form.notes_sortie.data or '').strip() or None
    if form.motif_sortie.data == 'fin_contrat':
        employe.date_fin_contrat = form.date_sortie.data

    db.session.commit()
    flash(
        f'Sortie enregistrée pour {employe.nom} {employe.prenom} '
        f'({dict(MOTIFS_SORTIE).get(form.motif_sortie.data, form.motif_sortie.data)}).',
        'success',
    )
    return redirect(url_for('rh.detail_employe', id=employe.id))


@rh_bp.route('/employes/<int:id>/reactiver', methods=['POST'])
@login_required
@permission_required('rh', 'update')
def reactiver_employe(id):
    employe = Employe.query.get_or_404(id)
    if employe.statut == 'actif':
        flash('Cet employé est déjà actif.', 'info')
        return redirect(url_for('rh.detail_employe', id=employe.id))

    employe.statut = 'actif'
    employe.date_sortie = None
    employe.motif_sortie = None
    employe.notes_sortie = None
    db.session.commit()
    flash(f'{employe.nom} {employe.prenom} a été réactivé.', 'success')
    return redirect(url_for('rh.detail_employe', id=employe.id))


@rh_bp.route('/employes/<int:id>/suspendre', methods=['POST'])
@login_required
@permission_required('rh', 'update')
def suspendre_employe(id):
    employe = Employe.query.get_or_404(id)
    if employe.statut != 'actif':
        flash('Seul un employé actif peut être suspendu.', 'warning')
        return redirect(url_for('rh.detail_employe', id=employe.id))
    employe.statut = 'suspendu'
    db.session.commit()
    flash(f'{employe.nom} {employe.prenom} est suspendu.', 'info')
    return redirect(url_for('rh.detail_employe', id=employe.id))

@rh_bp.route('/conges')
@login_required
@permission_required('rh', 'read')
def conges():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    pagination = (
        Conge.query.options(joinedload(Conge.employe))
        .order_by(Conge.created_at.desc())
        .paginate(page=page, per_page=CONGES_PAR_PAGE, error_out=False)
    )
    return render_template(
        'rh/conges.html',
        conges=pagination.items,
        pagination=pagination,
        filtres_url={},
    )

@rh_bp.route('/conges/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('rh', 'create')
def nouveau_conge():
    form = CongeForm()
    form.employe_id.choices = [(e.id, f"{e.nom} {e.prenom}") for e in Employe.query.filter_by(statut='actif').all()]
    if form.validate_on_submit():
        nb_jours = (form.date_fin.data - form.date_debut.data).days + 1
        if nb_jours <= 0:
            flash("La date de fin doit être postérieure à la date de début.", "danger")
            return render_template('rh/form_conge.html', form=form, title='Demander un Congé')
            
        conge = Conge(
            employe_id=form.employe_id.data,
            type_conge=form.type_conge.data,
            date_debut=form.date_debut.data,
            date_fin=form.date_fin.data,
            nb_jours=nb_jours,
            motif=form.motif.data
        )
        db.session.add(conge)
        db.session.commit()
        flash("Demande de congé enregistrée.", "success")
        return redirect(url_for('rh.conges'))
    return render_template('rh/form_conge.html', form=form, title='Demander un Congé')

@rh_bp.route('/conges/<int:id>/approuver', methods=['POST'])
@login_required
@permission_required('rh', 'update')
def approuver_conge(id):
    c = Conge.query.get_or_404(id)
    c.statut = 'approuve'
    c.approuve_par = current_user.id
    db.session.commit()
    flash("Le congé a été approuvé.", "success")
    return redirect(url_for('rh.conges'))

@rh_bp.route('/conges/<int:id>/refuser', methods=['POST'])
@login_required
@permission_required('rh', 'update')
def refuser_conge(id):
    c = Conge.query.get_or_404(id)
    c.statut = 'refuse'
    c.approuve_par = current_user.id
    db.session.commit()
    flash("Le congé a été refusé.", "info")
    return redirect(url_for('rh.conges'))

@rh_bp.route('/paies')
@login_required
@permission_required('rh', 'read')
def paies():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    statut = (request.args.get('statut') or '').strip()
    employe_id = request.args.get('employe_id', type=int)
    mois = request.args.get('mois', type=int)
    annee = request.args.get('annee', type=int)
    q = (request.args.get('q') or '').strip()

    query = Paie.query.options(joinedload(Paie.employe), joinedload(Paie.depense))

    if statut in ('genere', 'paye'):
        query = query.filter(Paie.statut == statut)
    if employe_id:
        query = query.filter(Paie.employe_id == employe_id)
    if mois and 1 <= mois <= 12:
        query = query.filter(Paie.mois == mois)
    if annee and 2000 <= annee <= 2100:
        query = query.filter(Paie.annee == annee)
    if q:
        pattern = f'%{q}%'
        query = query.join(Employe, Paie.employe_id == Employe.id).filter(
            or_(
                Employe.nom.ilike(pattern),
                Employe.prenom.ilike(pattern),
                Employe.matricule.ilike(pattern),
            )
        )

    pagination = (
        query.order_by(Paie.annee.desc(), Paie.mois.desc(), Paie.id.desc())
        .paginate(page=page, per_page=PAIES_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if statut:
        filtres_url['statut'] = statut
    if employe_id:
        filtres_url['employe_id'] = employe_id
    if mois and 1 <= mois <= 12:
        filtres_url['mois'] = mois
    if annee and 2000 <= annee <= 2100:
        filtres_url['annee'] = annee
    if q:
        filtres_url['q'] = q

    employes = Employe.query.order_by(Employe.nom.asc(), Employe.prenom.asc()).all()
    annees_disponibles = [
        row[0]
        for row in db.session.query(Paie.annee)
        .distinct()
        .order_by(Paie.annee.desc())
        .all()
    ]
    peut_payer = user_has_permission(current_user, 'rh', 'update')
    return render_template(
        'rh/paies.html',
        paies=pagination.items,
        pagination=pagination,
        employes=employes,
        statut_filtre=statut,
        employe_filtre=employe_id,
        mois_filtre=mois if mois and 1 <= mois <= 12 else None,
        annee_filtre=annee if annee and 2000 <= annee <= 2100 else None,
        annees_disponibles=annees_disponibles,
        q=q,
        filtres_url=filtres_url,
        peut_payer=peut_payer,
        today=datetime.date.today(),
    )

def _context_fiche_paie(paie: Paie) -> dict:
    ctx = pdf_company_context()
    merge_browser_print_logo(ctx)
    params = paie.employe.parametres_paie() if paie.employe else {}
    ctx.update(
        paie=paie,
        periode_label=libelle_periode_paie(paie.mois, paie.annee),
        date_jour=datetime.date.today(),
        taux_paie=params,
    )
    return ctx


@rh_bp.route('/paies/generer', methods=['GET', 'POST'])
@login_required
@permission_required('rh', 'create')
def generer_paie():
    employes = Employe.query.filter_by(statut='actif').all()
    if request.method == 'POST':
        mois = int(request.form.get('mois'))
        annee = int(request.form.get('annee'))
        employe_id = int(request.form.get('employe_id'))
        primes = float(request.form.get('primes') or 0.0)
        heures_sup = float(request.form.get('heures_sup') or 0.0)
        deductions = float(request.form.get('deductions') or 0.0)
        
        employe = Employe.query.get_or_404(employe_id)
        
        # Check if already generated
        exist = Paie.query.filter_by(employe_id=employe.id, mois=mois, annee=annee).first()
        if exist:
            flash(f"Un bulletin existe déjà pour {employe.nom} {employe.prenom} pour {mois}/{annee}.", "warning")
            return redirect(request.url)
            
        # Calcul bulletin (brut, cotisations salariales, charges patronales, IRPP, net)
        salaire_base = float(employe.salaire_base)
        calc = calculer_bulletin_paie(
            salaire_base,
            primes=primes,
            heures_sup=heures_sup,
            deductions=deductions,
            **employe.parametres_paie(),
        )

        paie = Paie(
            employe_id=employe.id,
            mois=mois,
            annee=annee,
            salaire_base=salaire_base,
            primes=primes,
            heures_sup=heures_sup,
            deductions=deductions,
            montant_brut=float(calc['montant_brut']),
            ipres_salarial=float(calc['ipres_salarial']),
            css_salarial=float(calc['css_salarial']),
            cotisations_sociales=float(calc['cotisations_sociales']),
            ipres_patronal=float(calc['ipres_patronal']),
            css_patronal=float(calc['css_patronal']),
            charges_patronales=float(calc['charges_patronales']),
            irpp=float(calc['irpp']),
            net_a_payer=float(calc['net_a_payer']),
            statut='genere'
        )
        db.session.add(paie)
        db.session.commit()
        
        flash(f"Bulletin de paie généré pour {employe.nom} {employe.prenom}.", "success")
        return redirect(url_for('rh.paies'))
        
    return render_template(
        'rh/form_paie.html',
        employes=employes,
        title='Générer Paie',
        today_month=datetime.datetime.now().month,
        today_year=datetime.datetime.now().year,
    )

@rh_bp.route('/paies/<int:id>/payer', methods=['POST'])
@login_required
@permission_required('rh', 'update')
def payer_paie(id):
    paie = Paie.query.options(joinedload(Paie.employe)).get_or_404(id)
    if paie.statut == 'paye':
        flash('Ce bulletin est déjà marqué comme payé.', 'info')
        return redirect(url_for('rh.paies'))

    mode = (request.form.get('mode_paiement') or 'virement').strip().lower()
    date_str = (request.form.get('date_paiement') or '').strip()
    if not date_str:
        date_paiement = datetime.date.today()
    else:
        try:
            date_paiement = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Date de paiement invalide.', 'danger')
            return redirect(url_for('rh.paies'))

    try:
        depense = creer_depense_paie(
            paie,
            mode_paiement=mode,
            date_paiement=date_paiement,
            created_by=current_user.id,
        )
        paie.statut = 'paye'
        paie.date_paiement = date_paiement
        paie.mode_paiement = mode
        db.session.commit()
        flash(
            f'Paiement enregistré — dépense {depense.reference} créée (catégorie Salaires, en attente de validation).',
            'success',
        )
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    except Exception as exc:
        db.session.rollback()
        flash(f'Erreur lors du paiement : {exc}', 'danger')

    return redirect(url_for('rh.paies'))


@rh_bp.route('/paies/<int:id>')
@login_required
@permission_required('rh', 'read')
def paie_detail(id):
    p = Paie.query.options(joinedload(Paie.employe)).get_or_404(id)
    return render_template('rh/fiche_paie.html', **_context_fiche_paie(p), mode='apercu')


@rh_bp.route('/paies/<int:id>/pdf')
@login_required
@permission_required('rh', 'read')
def paie_pdf(id):
    p = Paie.query.options(joinedload(Paie.employe)).get_or_404(id)
    html = render_template('rh/fiche_paie.html', **_context_fiche_paie(p), mode='pdf')
    try:
        pdf_io = generate_pdf(html)
        return send_file(pdf_io, download_name=f"Fiche_Paie_{p.employe.matricule}_{p.mois}_{p.annee}.pdf", as_attachment=False, mimetype='application/pdf')
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for('rh.paies'))
