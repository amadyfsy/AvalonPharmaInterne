from datetime import date, datetime
import os

from sqlalchemy import extract, func, or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models.depense import CategorieDepense, Depense
from ...models.tresorerie import TresorerieOperation
from ...utils.categorie_depense_registry import build_category_groups
from ...utils.depense_justificatif import justificatif_abs_path, upload_depense_justificatif
from ...utils.depense_reference import prochaine_reference_depense
from ...utils.decorators import permission_required, user_has_permission
from ...utils.depenses_tableau_export import (
    build_depense_rows,
    build_depense_sections_by_month,
    compute_totaux as compute_totaux_depenses,
    export_filename as depenses_export_filename,
    generate_depenses_tableau_excel,
    titre_general_export as titre_general_depenses,
    titre_periode_mois as titre_periode_depenses,
)
from ...utils.nombre_lettres import format_montant_espace
from ...utils.parametres_pdf import get_logo_filepath, get_parametres_documents, logo_data_uri
from ...utils.pdf_generator import generate_pdf
from flask_login import current_user, login_required

from flask import current_app, flash, redirect, render_template, request, send_file, url_for

from . import depenses_bp
from .forms import CategorieDepenseForm, DepenseForm

_MOIS_FILTRE = (
    (1, "Janvier"),
    (2, "Février"),
    (3, "Mars"),
    (4, "Avril"),
    (5, "Mai"),
    (6, "Juin"),
    (7, "Juillet"),
    (8, "Août"),
    (9, "Septembre"),
    (10, "Octobre"),
    (11, "Novembre"),
    (12, "Décembre"),
)


def _type_depense_str(value) -> str:
    """Normalise la valeur enum SQLAlchemy en 'fixe' | 'variable'."""
    if value is None:
        return 'variable'
    return getattr(value, 'value', value)


_MOIS_FR = (
    '',
    'janvier',
    'février',
    'mars',
    'avril',
    'mai',
    'juin',
    'juillet',
    'août',
    'septembre',
    'octobre',
    'novembre',
    'décembre',
)


def _mois_annee_fr(year: int, month: int) -> str:
    return f'{_MOIS_FR[month]} {year}'


def _prev_calendar_month(year: int, month: int) -> tuple[int, int]:
    if month <= 1:
        return year - 1, 12
    return year, month - 1


def _sums_depenses_valide_par_type(year: int, month: int) -> dict[str, float]:
    """Sommes TTC des dépenses validées, par type (fixe / variable)."""
    rows = (
        db.session.query(Depense.type_depense, func.coalesce(func.sum(Depense.montant_ttc), 0))
        .filter(
            extract('year', Depense.date_depense) == year,
            extract('month', Depense.date_depense) == month,
            Depense.statut == 'valide',
        )
        .group_by(Depense.type_depense)
        .all()
    )
    out: dict[str, float] = {'fixe': 0.0, 'variable': 0.0}
    for t, msum in rows:
        k = _type_depense_str(t)
        if k in out:
            out[k] = float(msum or 0)
    return out


def _depenses_kpi_mois():
    """KPI mois en cours + mois précédent pour cartes fixes / variables."""
    today = date.today()
    curr = _sums_depenses_valide_par_type(today.year, today.month)
    py, pm = _prev_calendar_month(today.year, today.month)
    prev = _sums_depenses_valide_par_type(py, pm)
    return {
        'total_fixe_mois': curr['fixe'],
        'total_variable_mois': curr['variable'],
        'total_fixe_prev': prev['fixe'],
        'total_variable_prev': prev['variable'],
        'libelle_mois_cours': _mois_annee_fr(today.year, today.month),
        'libelle_mois_prec': _mois_annee_fr(py, pm),
        'total_valide_mois': curr['fixe'] + curr['variable'],
    }


DEPENSES_PAR_PAGE = 15


@depenses_bp.route('/')
@login_required
@permission_required('depenses', 'read')
def index():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    statut = (request.args.get('statut') or '').strip()
    categorie_id = request.args.get('categorie_id', type=int)
    type_filtre = (request.args.get('type') or '').strip()
    q = (request.args.get('q') or '').strip()

    query = Depense.query.options(
        joinedload(Depense.categorie),
        joinedload(Depense.fournisseur),
    )

    if statut in ('en_attente', 'valide', 'rejete'):
        query = query.filter(Depense.statut == statut)
    if categorie_id:
        query = query.filter(Depense.categorie_id == categorie_id)
    if type_filtre in ('fixe', 'variable'):
        query = query.filter(Depense.type_depense == type_filtre)
    if q:
        pattern = f'%{q}%'
        query = query.filter(
            or_(Depense.libelle.ilike(pattern), Depense.reference.ilike(pattern))
        )

    pagination = (
        query.order_by(
            Depense.date_depense.desc(),
            Depense.created_at.desc(),
            Depense.id.desc(),
        )
        .paginate(page=page, per_page=DEPENSES_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if statut:
        filtres_url['statut'] = statut
    if categorie_id:
        filtres_url['categorie_id'] = categorie_id
    if type_filtre:
        filtres_url['type'] = type_filtre
    if q:
        filtres_url['q'] = q

    categories = CategorieDepense.query.order_by(CategorieDepense.nom).all()
    kpi = _depenses_kpi_mois()
    nb_en_attente = Depense.query.filter_by(statut='en_attente').count()
    peut_valider = current_user.role in ('admin', 'manager')
    year_col = extract('year', Depense.date_depense)
    annees_dispo = [
        int(y)
        for (y,) in (
            db.session.query(year_col)
            .filter(Depense.date_depense.isnot(None))
            .distinct()
            .order_by(year_col.desc())
            .all()
        )
        if y
    ]
    return render_template(
        'depenses/index.html',
        depenses=pagination.items,
        pagination=pagination,
        categories=categories,
        statut_filtre=statut,
        categorie_filtre=categorie_id,
        type_filtre=type_filtre,
        q=q,
        filtres_url=filtres_url,
        nb_en_attente=nb_en_attente,
        peut_valider=peut_valider,
        annees_dispo=annees_dispo,
        mois_dispo=_MOIS_FILTRE,
        annee_filtre=None,
        mois_filtre=None,
        **kpi,
    )


def _filtre_label_export_depenses(annee, mois, categorie) -> str:
    parts = []
    if annee:
        parts.append(f"année {annee}")
    if mois:
        parts.append(dict(_MOIS_FILTRE).get(mois, str(mois)))
    if categorie:
        parts.append(categorie.nom)
    if not parts:
        return f"Toutes les dépenses · export du {date.today().strftime('%d/%m/%Y')}"
    return " · ".join(parts) + f" · export du {date.today().strftime('%d/%m/%Y')}"


@depenses_bp.route('/export-tableau')
@login_required
@permission_required('depenses', 'read')
def export_tableau_depenses():
    """Télécharge le tableau des dépenses (Excel ou PDF), style feuille DEPENSES.xlsx."""
    annee = request.args.get('annee', type=int)
    mois = request.args.get('mois', type=int)
    categorie_id = request.args.get('categorie_id', type=int)
    fmt = (request.args.get('format') or 'xlsx').strip().lower()
    if fmt not in ('xlsx', 'pdf'):
        fmt = 'xlsx'
    if mois is not None and (mois < 1 or mois > 12):
        mois = None

    categorie = db.session.get(CategorieDepense, categorie_id) if categorie_id else None

    query = Depense.query.options(
        joinedload(Depense.categorie),
        joinedload(Depense.fournisseur),
    ).filter(Depense.statut != 'rejete')

    if annee:
        query = query.filter(extract('year', Depense.date_depense) == annee)
    if mois:
        query = query.filter(extract('month', Depense.date_depense) == mois)
    if categorie:
        query = query.filter(Depense.categorie_id == categorie.id)

    depenses = query.order_by(
        Depense.date_depense.asc(),
        Depense.reference.asc(),
        Depense.id.asc(),
    ).all()

    filtre_label = _filtre_label_export_depenses(annee, mois, categorie)
    split_by_month = mois is None
    filename = depenses_export_filename(annee, mois, ext=fmt)

    doc_params = get_parametres_documents()
    company_name = (
        (getattr(doc_params, "raison_sociale", None) or "").strip()
        or current_app.config.get("COMPANY_NAME")
        or "Avalon Pharma"
    )
    logo_path = get_logo_filepath()
    titre_general = titre_general_depenses(
        company_name=company_name,
        annee=annee,
        mois=mois if not split_by_month else None,
    )
    titre_periode = titre_periode_depenses(mois, annee) if mois else None

    if fmt == 'pdf':
        if split_by_month:
            sections, totaux_global = build_depense_sections_by_month(
                depenses, annee=annee
            )
            rows = []
            totaux = None
        else:
            sections = None
            totaux_global = None
            rows = build_depense_rows(depenses)
            totaux = compute_totaux_depenses(depenses)
        html = render_template(
            'depenses/export_depenses_tableau_pdf.html',
            rows=rows,
            sections=sections,
            totaux=totaux,
            totaux_global=totaux_global,
            split_by_month=split_by_month,
            titre_general=titre_general,
            titre_periode=titre_periode,
            filtre_label=filtre_label,
            format_fcfa=format_montant_espace,
            genere_le=datetime.now(),
            logo_data_uri=logo_data_uri(),
            company_name=company_name,
        )
        pdf_io = generate_pdf(html)
        return send_file(
            pdf_io,
            download_name=filename,
            as_attachment=True,
            mimetype='application/pdf',
        )

    sheet_title = "Depenses"
    if mois:
        sheet_title = dict(_MOIS_FILTRE).get(mois, f"Mois {mois}")
    elif annee:
        sheet_title = str(annee)

    excel_io = generate_depenses_tableau_excel(
        depenses,
        sheet_title=sheet_title,
        filtre_label=filtre_label,
        logo_path=logo_path,
        company_name=company_name,
        split_by_month=split_by_month,
        annee=annee,
        mois=mois,
    )
    return send_file(
        excel_io,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )

@depenses_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
@permission_required('depenses', 'saisir')
def nouvelle_depense():
    form = DepenseForm()
    categories = CategorieDepense.query.order_by(CategorieDepense.nom).all()
    form.categorie_id.choices = [(c.id, c.nom) for c in categories]
    types_par_categorie = {str(c.id): _type_depense_str(c.type_depense) for c in categories}

    def render_depense_form():
        ref_date = form.date_depense.data or date.today()
        return render_template(
            'depenses/form.html',
            form=form,
            title='Saisir une Dépense',
            types_par_categorie=types_par_categorie,
            reference_preview=prochaine_reference_depense(ref_date),
        )

    if request.method == 'GET' and not form.date_depense.data:
        form.date_depense.data = date.today()

    if form.validate_on_submit():
        cat = db.session.get(CategorieDepense, form.categorie_id.data)
        if not cat:
            flash('Catégorie introuvable.', 'danger')
            return render_depense_form()

        reference = prochaine_reference_depense(form.date_depense.data)
        justif_filename = None
        if form.justificatif.data and form.justificatif.data.filename:
            try:
                justif_filename = upload_depense_justificatif(
                    form.justificatif.data,
                    cat.nom,
                    reference,
                )
            except Exception as e:
                flash(str(e), 'danger')
                return render_depense_form()
        
        m_ht = form.montant_ht.data
        t_tva = form.tva.data
        m_ttc = m_ht * (1 + (t_tva / 100))

        type_depense = _type_depense_str(cat.type_depense)
        depense = Depense(
            reference=reference,
            categorie_id=form.categorie_id.data,
            type_depense=type_depense,
            libelle=form.libelle.data,
            montant_ht=m_ht,
            tva=t_tva,
            montant_ttc=m_ttc,
            date_depense=form.date_depense.data,
            mode_paiement=form.mode_paiement.data,
            fournisseur_id=None,
            justificatif=justif_filename,
            created_by=current_user.id
        )
        db.session.add(depense)
        db.session.commit()
        flash('Dépense enregistrée (en attente de validation).', 'success')
        return redirect(url_for('depenses.index'))
        
    return render_depense_form()

@depenses_bp.route('/<int:id>/valider', methods=['POST'])
@login_required
@permission_required('depenses', 'valider')
def valider_depense(id):
    d = Depense.query.get_or_404(id)
    if d.statut != 'en_attente':
        flash("Seulement les dépenses en attente peuvent être validées.", "warning")
        return redirect(url_for('depenses.index'))
        
    try:
        d.statut = 'valide'
        d.valide_par = current_user.id
        
        # Rapprochement avec Trésorerie automatiquement 
        type_cpt = 'caisse' if d.mode_paiement == 'espece' else 'banque'
        ops_avant = TresorerieOperation.query.filter_by(type_compte=type_cpt).all()
        solde_avant = sum([op.montant if op.type_operation == 'entree' else -op.montant for op in ops_avant])
        nouveau_solde = solde_avant - d.montant_ttc
        
        op = TresorerieOperation(
            type_compte=type_cpt,
            type_operation='sortie',
            libelle=f"Paiement Dépense {d.reference} - {d.libelle}",
            montant=d.montant_ttc,
            reference_document=d.reference,
            date_operation=datetime.utcnow().date(),
            solde_apres=nouveau_solde,
            created_by=current_user.id
        )
        db.session.add(op)
        db.session.commit()
        flash(f'La dépense {d.reference} a été validée. La trésorerie a été mise à jour.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la validation: {str(e)}', 'danger')
        
    return redirect(url_for('depenses.index'))

@depenses_bp.route('/<int:id>/rejeter', methods=['POST'])
@login_required
@permission_required('depenses', 'valider')
def rejeter_depense(id):
    d = Depense.query.get_or_404(id)
    if d.statut != 'en_attente':
        flash("Action impossible.", "warning")
        return redirect(url_for('depenses.index'))
        
    d.statut = 'rejete'
    d.valide_par = current_user.id
    db.session.commit()
    flash(f'La dépense {d.reference} a été rejetée.', 'info')
    return redirect(url_for('depenses.index'))


@depenses_bp.route('/justificatif/<path:stored_name>')
@login_required
@permission_required('depenses', 'read')
def justificatif_fichier(stored_name):
    """Téléchargement / affichage d'un justificatif de dépense."""
    safe = stored_name.replace('\\', '/').lstrip('/')
    if not safe.startswith('depenses/') or '..' in safe:
        flash('Fichier introuvable.', 'danger')
        return redirect(url_for('depenses.index'))
    path = justificatif_abs_path(safe)
    if not path or not os.path.isfile(path):
        flash('Justificatif introuvable.', 'danger')
        return redirect(url_for('depenses.index'))
    return send_file(path, as_attachment=False, download_name=os.path.basename(path))


@depenses_bp.route('/categories')
@login_required
@permission_required('depenses', 'read')
def categories_depenses_index():
    categories = CategorieDepense.query.order_by(CategorieDepense.nom).all()
    kpi = _depenses_kpi_mois()
    nb_categories = len(categories)
    nb_fixe_cat = sum(1 for c in categories if _type_depense_str(c.type_depense) == 'fixe')
    nb_variable_cat = sum(1 for c in categories if _type_depense_str(c.type_depense) == 'variable')

    counts_rows = (
        db.session.query(Depense.categorie_id, func.count(Depense.id))
        .group_by(Depense.categorie_id)
        .all()
    )
    nb_depenses_par_cat = {int(cid): int(n) for cid, n in counts_rows if cid is not None}

    category_groups = build_category_groups(
        categories,
        nb_depenses_par_cat,
        lambda c: _type_depense_str(c.type_depense),
    )

    return render_template(
        'depenses/categories/index.html',
        category_groups=category_groups,
        nb_categories=nb_categories,
        nb_fixe_cat=nb_fixe_cat,
        nb_variable_cat=nb_variable_cat,
        peut_creer_categorie_depense=user_has_permission(current_user, 'depenses', 'saisir'),
        **kpi,
    )


@depenses_bp.route('/categories/nouvelle', methods=['GET', 'POST'])
@login_required
@permission_required('depenses', 'saisir')
def categorie_depense_nouvelle():
    form = CategorieDepenseForm()
    if form.validate_on_submit():
        cat = CategorieDepense(
            nom=form.nom.data.strip(),
            type_depense=form.type_depense.data,
            description=(form.description.data or '').strip() or None,
            icone=form.icone.data or 'bi-tag',
        )
        db.session.add(cat)
        db.session.commit()
        flash('Catégorie de dépense créée.', 'success')
        return redirect(url_for('depenses.categories_depenses_index'))
    return render_template('depenses/categories/form.html', form=form, title='Nouvelle catégorie')
