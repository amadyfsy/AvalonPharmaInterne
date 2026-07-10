from datetime import date
import os

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models.bon_livraison import BonLivraison
from ...models.bon_livraison import LigneBL
from ...models.commande import CommandeFournisseur, LigneCommandeFournisseur
from ...models.fournisseur import Fournisseur
from ...models.produit import CategorieProduit, Lot, Produit, ProduitPhoto
from ...models.stock import MouvementStock, Stock
from ...utils.decorators import permission_required, role_required, user_has_permission
from ...utils.produit_photos import (
    MAX_GALERIE_PHOTOS,
    photo_abs_path,
    remove_produit_photo_file,
    upload_produit_photo,
)
from ...utils.produit_photos_api import photos_galerie_triees, produit_photos_payload
from flask_login import current_user, login_required

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for

from ...utils.produit_metier import (
    DM_SPECIALITES,
    EQ_SPECIALITES,
    MED_SPECIALITES,
    apply_donnees_metier_to_form,
    bucket_produit_categorie,
    build_donnees_metier,
    CATEGORIES_ENUM,
    CODE_DISPOSITIFS,
    CODE_EQUIPEMENT,
    CODE_MEDICAMENTS,
    effective_metier_code,
    specialite_choices_for_wtforms,
    specialites_allowed_from_form,
    specialites_form_grouped,
    specialites_list_for_category,
)

from . import stock_bp
from .forms import MouvementStockForm, ProduitCreateForm, ProduitEditForm


def _generate_produit_reference() -> str:
    """Génère une référence produit unique du type PRD-YYYYMMDD-XXX."""
    day = date.today().strftime('%Y%m%d')
    prefix = f'PRD-{day}-'
    last = (
        Produit.query.filter(Produit.reference.like(f'{prefix}%'))
        .order_by(Produit.reference.desc())
        .first()
    )
    seq = 1
    if last and last.reference:
        try:
            seq = int(last.reference.rsplit('-', 1)[-1]) + 1
        except (TypeError, ValueError):
            seq = 1
    return f'{prefix}{seq:03d}'


def _sync_stock_from_lots(produit_id: int) -> Stock:
    """Recalcule le stock produit = somme des quantités disponibles des lots."""
    total_lots = (
        db.session.query(func.coalesce(func.sum(Lot.quantite_disponible), 0))
        .filter(Lot.produit_id == produit_id)
        .scalar()
    )
    total = int(total_lots or 0)
    stock = Stock.query.filter_by(produit_id=produit_id).first()
    if not stock:
        stock = Stock(produit_id=produit_id, quantite_disponible=0, quantite_reservee=0)
        db.session.add(stock)
    stock.quantite_disponible = total
    stock.dernier_mouvement = db.func.now()
    return stock


def _categories_metier_map():
    """id -> code métier effectif pour le JS (nom + code en base)."""
    rows = CategorieProduit.query.order_by(CategorieProduit.nom).all()
    return {str(c.id): effective_metier_code(c) for c in rows}


def _flatten_select_choices(choices):
    """Aplatit les choix WTForms (liste plate, dict optgroups) en [(id, libellé), ...]."""
    if choices is None:
        return []
    if isinstance(choices, dict):
        out = []
        for sub in choices.values():
            out.extend(sub)
        return out
    out = []
    for item in choices:
        if not item:
            continue
        second = item[1]
        if isinstance(second, (list, tuple)):
            out.extend(second)
        else:
            out.append(item)
    return out


def _has_real_categorie_in_choices(choices) -> bool:
    """Au moins une catégorie réelle (id > 0), hors lignes « vides » désactivées."""
    flat = _flatten_select_choices(choices)
    return any(len(p) >= 1 and p[0] > 0 for p in flat)


_ENUM_CODE_FORMULAIRE_MAP = {
    'medicament': CODE_MEDICAMENTS,
    'consommable': CODE_MEDICAMENTS,
    'implant': CODE_DISPOSITIFS,
    'equipement': CODE_EQUIPEMENT,
}

# Aide courte sous le select « Catégorie » (formulaire produit), par clé d’énumération métier.
_CATEGORIE_ENUM_USER_HINTS = {
    'medicament': (
        'Produits pharmaceutiques : médicaments, solutions injectables ou perfusables, etc.'
    ),
    'consommable': (
        'Consommables et petit matériel médical à usage courant ou à usage unique.'
    ),
    'implant': (
        'Dispositifs médicaux : implants, prothèses, stents, matériel de chirurgie ou de bloc.'
    ),
    'equipement': (
        'Équipements lourds ou biomédicaux : imagerie, réanimation, fauteuils, mobilier technique.'
    ),
}


def _categorie_produit_hints_by_id() -> dict[str, str]:
    """id de catégorie (str) → courte description du type de produit (aligné sur l’énumération du select)."""
    by_bucket = _ensure_enum_categories()
    out: dict[str, str] = {}
    for key, _label in CATEGORIES_ENUM:
        cat = by_bucket.get(key)
        if not cat:
            continue
        hint = _CATEGORIE_ENUM_USER_HINTS.get(key)
        if hint:
            out[str(cat.id)] = hint
    return out


def _ensure_enum_categories():
    """
    Garantit l'existence d'une catégorie DB pour chaque valeur d'énumération.
    Retourne {enum_key: CategorieProduit}.
    """
    rows = CategorieProduit.query.order_by(CategorieProduit.nom).all()
    by_bucket = {}
    for c in rows:
        b = bucket_produit_categorie(c.code_formulaire, c.nom)
        n = (c.nom or '').strip().lower()
        if 'consomm' in n:
            key = 'consommable'
        elif b == 'dispositifs' or any(k in n for k in ('implant', 'stent', 'prothese')):
            key = 'implant'
        elif b == 'equipement':
            key = 'equipement'
        elif b == 'medicaments':
            key = 'medicament'
        else:
            key = None
        if key and key not in by_bucket:
            by_bucket[key] = c

    created = False
    for key, label in CATEGORIES_ENUM:
        if key in by_bucket:
            continue
        cat = CategorieProduit(
            nom=label,
            description=f'Catégorie enum auto-créée: {label}',
            code_formulaire=_ENUM_CODE_FORMULAIRE_MAP.get(key),
        )
        db.session.add(cat)
        db.session.flush()
        by_bucket[key] = cat
        created = True

    if created:
        db.session.commit()
    return by_bucket


def _categorie_produit_choices_enum(include_placeholder=False):
    """
    Catégories pour le select produit, basées sur l'énumération métier.
    Le champ affiche UNIQUEMENT les catégories enum:
    Médicament, Consommable, Implant, Équipement.
    Chaque libellé est lié à la première catégorie DB trouvée dans le bucket.
    """
    by_bucket = _ensure_enum_categories()

    choices = []
    if include_placeholder:
        choices.append((0, '— Sélectionnez une catégorie —', {'disabled': True}))
    for key, label in CATEGORIES_ENUM:
        cat = by_bucket.get(key)
        if cat:
            choices.append((cat.id, label))
    return choices


def _inject_select_if_missing(form, field_name, value):
    """Évite une erreur de validation si une valeur stockée n’est plus dans la liste."""
    if not value:
        return
    field = getattr(form, field_name, None)
    if field is None:
        return
    ch = field.choices
    flat = _flatten_select_choices(ch)
    keys = [p[0] for p in flat]
    if value not in keys:
        if isinstance(ch, dict):
            return
        if ch and isinstance(ch[0], (list, tuple)) and len(ch[0]) >= 2 and isinstance(
            ch[0][1], (list, tuple)
        ):
            field.choices = list(ch) + [('Hors liste', [(value, str(value))])]
            return
        field.choices = list(ch) + [(value, str(value))]


def _merge_conditionnement_general(form, donnees_metier):
    """Conserve un champ conditionnement transversal dans donnees_metier."""
    out = dict(donnees_metier or {})
    cg = (form.conditionnement_general.data or '').strip()
    if cg:
        out['conditionnement_general'] = cg
    return out or None


def _set_form_specialite_choices(form, categorie_id: int | None) -> None:
    """Même logique que le filtre Spécialité de la liste produits (optgroups / liste plate)."""
    cid = int(categorie_id or 0)
    cat = db.session.get(CategorieProduit, cid) if cid else None
    form.specialite.choices = specialite_choices_for_wtforms(cat)


def _specialite_catalog_for_js() -> dict:
    """Données pour reconstruire le select côté client (changement de catégorie)."""
    return {
        'flat': {
            'medicaments': list(MED_SPECIALITES),
            'dispositifs': list(DM_SPECIALITES),
            'equipement': list(EQ_SPECIALITES),
        },
        'grouped': [[label, list(lst)] for label, lst in specialites_form_grouped()],
    }


@stock_bp.route('/')
@login_required
@permission_required('stock', 'read')
def index():
    q = (request.args.get('q') or '').strip()
    categorie_id = request.args.get('categorie_id', type=int)
    specialites_codes = specialites_allowed_from_form()
    specialite_raw = (request.args.get('specialite') or '').strip()

    cat_filtre = (
        db.session.get(CategorieProduit, categorie_id) if categorie_id else None
    )
    spec_list_cat = (
        specialites_list_for_category(cat_filtre) if cat_filtre is not None else None
    )

    specialite = ''
    if specialite_raw in specialites_codes:
        if cat_filtre is None:
            specialite = specialite_raw
        elif spec_list_cat and specialite_raw in spec_list_cat:
            specialite = specialite_raw

    if cat_filtre is None:
        specialites_filtre_grouped = list(specialites_form_grouped())
        specialites_filtre_flat = None
    elif spec_list_cat:
        specialites_filtre_flat = [(s, s) for s in spec_list_cat]
        specialites_filtre_grouped = None
    else:
        specialites_filtre_flat = []
        specialites_filtre_grouped = None

    query = Produit.query.options(
        joinedload(Produit.categorie),
        joinedload(Produit.stock),
    ).outerjoin(CategorieProduit, Produit.categorie_id == CategorieProduit.id)

    if categorie_id:
        query = query.filter(Produit.categorie_id == categorie_id)
    if specialite:
        spec_json = func.json_unquote(
            func.json_extract(Produit.donnees_metier, '$.specialite')
        )
        query = query.filter(spec_json == specialite)

    if q:
        like = f'%{q}%'
        q_lo = f'%{q.lower()}%'
        spec_for_q = func.json_unquote(
            func.json_extract(Produit.donnees_metier, '$.specialite')
        )
        query = query.filter(
            or_(
                Produit.reference.ilike(like),
                Produit.designation.ilike(like),
                Produit.description.ilike(like),
                Produit.unite.ilike(like),
                CategorieProduit.nom.ilike(like),
                func.lower(func.coalesce(spec_for_q, '')).like(q_lo),
            )
        )

    produits = query.order_by(Produit.reference).all()
    categories = CategorieProduit.query.order_by(CategorieProduit.nom).all()
    has_filters = bool(q or categorie_id or specialite)

    return render_template(
        'stock/index.html',
        produits=produits,
        q=q,
        categorie_id=categorie_id or 0,
        specialite=specialite,
        categories=categories,
        specialites_filtre_flat=specialites_filtre_flat,
        specialites_filtre_grouped=specialites_filtre_grouped,
        has_filters=has_filters,
    )

@stock_bp.route('/produit/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('stock', 'create')
def nouveau_produit():
    form = ProduitCreateForm()
    form.categorie_id.choices = _categorie_produit_choices_enum(include_placeholder=True)
    if request.method == 'GET':
        form.categorie_id.data = 0
        form.reference.data = _generate_produit_reference()
    cid_bind = (
        (request.form.get('categorie_id', type=int) or 0)
        if request.method == 'POST'
        else int(form.categorie_id.data or 0)
    )
    _set_form_specialite_choices(form, cid_bind if cid_bind else None)
    form.fournisseur_lot_id.choices = [(0, '— Sélectionnez un fournisseur —')] + [
        (f.id, f.raison_sociale)
        for f in Fournisseur.query.filter_by(est_actif=True).order_by(Fournisseur.raison_sociale)
    ]
    if not _has_real_categorie_in_choices(form.categorie_id.choices):
        flash("Veuillez d'abord créer au moins une catégorie de produit.", "warning")
        return redirect(url_for('stock.index'))

    if form.validate_on_submit():
        prix_vente_ht = form.prix_vente_ht.data
        tva = form.tva.data
        prix_vente_ttc = prix_vente_ht * (1 + (tva / 100))
        lot_num = (form.numero_lot.data or '').strip()[:100]
        qte_lot_initiale = int(form.quantite_lot_initiale.data or 0)
        fid = int(form.fournisseur_lot_id.data or 0)
        if fid and not Fournisseur.query.get(fid):
            flash('Fournisseur du lot invalide.', 'danger')
            return render_template(
                'stock/form_produit.html',
                form=form,
                title='Nouveau Produit',
                categories_metier_map=_categories_metier_map(),
                specialite_catalog=_specialite_catalog_for_js(),
                categorie_produit_hints=_categorie_produit_hints_by_id(),
            )

        cat = CategorieProduit.query.get(form.categorie_id.data)
        code_f = effective_metier_code(cat) if cat else ''
        donnees_metier = _merge_conditionnement_general(
            form, build_donnees_metier(code_f, form)
        )
        reference_auto = _generate_produit_reference()

        try:
            produit = Produit(
                reference=reference_auto,
                designation=(form.designation.data or '').strip(),
                description=(form.description.data or '').strip() or None,
                categorie_id=form.categorie_id.data,
                forme=form.forme.data,
                unite=(form.unite.data or '').strip(),
                prix_achat_ht=form.prix_achat_ht.data,
                prix_vente_ht=prix_vente_ht,
                tva=tva,
                prix_vente_ttc=prix_vente_ttc,
                seuil_alerte_stock=form.seuil_alerte_stock.data,
                est_actif=form.est_actif.data,
                donnees_metier=donnees_metier,
            )
            db.session.add(produit)
            db.session.flush()

            stock = Stock(
                produit_id=produit.id, quantite_disponible=0, quantite_reservee=0
            )
            db.session.add(stock)

            if lot_num:
                lot = Lot(
                    produit_id=produit.id,
                    numero_lot=lot_num,
                    date_fabrication=form.date_fabrication.data,
                    date_peremption=form.date_peremption.data,
                    fournisseur_id=fid if fid else None,
                    quantite_initiale=qte_lot_initiale,
                    quantite_disponible=qte_lot_initiale,
                )
                db.session.add(lot)
                _sync_stock_from_lots(produit.id)
            db.session.commit()
            if lot_num:
                flash(
                    f'Produit créé avec succès (lot « {lot_num} » enregistré, stock lot: {qte_lot_initiale}).',
                    'success',
                )
            else:
                flash(
                    'Produit créé avec succès (sans lot initial — vous pourrez en ajouter via réceptions ou mouvements).',
                    'success',
                )
            return redirect(url_for('stock.detail_produit', id=produit.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création : {str(e)}', 'danger')

    return render_template(
        'stock/form_produit.html',
        form=form,
        title='Nouveau Produit',
        categories_metier_map=_categories_metier_map(),
        specialite_catalog=_specialite_catalog_for_js(),
        categorie_produit_hints=_categorie_produit_hints_by_id(),
    )


@stock_bp.route('/produit/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@permission_required('stock', 'update')
def modifier_produit(id):
    produit = Produit.query.get_or_404(id)
    form = ProduitEditForm(obj=produit)
    form.categorie_id.choices = _categorie_produit_choices_enum(include_placeholder=False)
    if not _has_real_categorie_in_choices(form.categorie_id.choices):
        flash("Veuillez d'abord créer au moins une catégorie de produit.", 'warning')
        return redirect(url_for('stock.detail_produit', id=id))

    cat0 = produit.categorie
    code0 = effective_metier_code(cat0) if cat0 else ''
    dm0 = produit.donnees_metier if isinstance(produit.donnees_metier, dict) else {}
    if request.method == 'GET':
        apply_donnees_metier_to_form(form, code0, produit.donnees_metier)
    if hasattr(form, 'conditionnement_general'):
        form.conditionnement_general.data = dm0.get('conditionnement_general') or ''
    cid_bind = (
        (request.form.get('categorie_id', type=int) or produit.categorie_id)
        if request.method == 'POST'
        else produit.categorie_id
    )
    _set_form_specialite_choices(form, cid_bind)
    cat_bind = db.session.get(CategorieProduit, cid_bind) if cid_bind else None
    code_bind = effective_metier_code(cat_bind) if cat_bind else ''
    if request.method == 'POST':
        sp = (request.form.get('specialite') or '').strip() or None
    else:
        sp = (dm0.get('specialite') if dm0 else None) or None
    if code_bind in ('medicaments', 'dispositifs', 'equipement'):
        _inject_select_if_missing(form, 'specialite', sp)

    if form.validate_on_submit():
        produit.designation = (form.designation.data or '').strip()
        produit.description = (form.description.data or '').strip() or None
        produit.categorie_id = form.categorie_id.data
        produit.forme = form.forme.data
        produit.unite = (form.unite.data or '').strip()
        produit.prix_achat_ht = form.prix_achat_ht.data
        produit.prix_vente_ht = form.prix_vente_ht.data
        produit.tva = form.tva.data
        produit.prix_vente_ttc = form.prix_vente_ht.data * (1 + form.tva.data / 100)
        produit.seuil_alerte_stock = form.seuil_alerte_stock.data
        produit.est_actif = bool(form.est_actif.data)
        cat = CategorieProduit.query.get(form.categorie_id.data)
        code_f = effective_metier_code(cat) if cat else ''
        produit.donnees_metier = _merge_conditionnement_general(
            form, build_donnees_metier(code_f, form)
        )

        try:
            db.session.commit()
            flash('Produit mis à jour.', 'success')
            return redirect(url_for('stock.detail_produit', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour : {str(e)}', 'danger')

    return render_template(
        'stock/form_produit.html',
        form=form,
        title=f'Modifier — {produit.reference}',
        produit=produit,
        edit_mode=True,
        categories_metier_map=_categories_metier_map(),
        specialite_catalog=_specialite_catalog_for_js(),
        categorie_produit_hints=_categorie_produit_hints_by_id(),
    )


@stock_bp.route('/produit/<int:id>')
@login_required
@permission_required('stock', 'read')
def detail_produit(id):
    produit = (
        Produit.query.options(
            joinedload(Produit.categorie),
            joinedload(Produit.stock),
            joinedload(Produit.lots).joinedload(Lot.fournisseur),
            joinedload(Produit.photos_galerie),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    # Tri par péremption (date) puis id ; éviter de mélanger date et datetime dans la clé
    def _lot_sort_key(lot):
        end = lot.date_peremption
        if end is None and lot.created_at is not None:
            end = lot.created_at.date()
        return (end or date.min, lot.id)

    lots = sorted(produit.lots, key=_lot_sort_key)
    stock_dispo_total = (
        db.session.query(func.coalesce(func.sum(Lot.quantite_disponible), 0))
        .filter(Lot.produit_id == produit.id)
        .scalar()
        or 0
    )
    stock_reserve = produit.stock.quantite_reservee if produit.stock else 0
    # Historique des achats : lignes de commandes fournisseur (tous statuts)
    lignes_achats = (
        LigneCommandeFournisseur.query.filter_by(produit_id=id)
        .join(CommandeFournisseur, LigneCommandeFournisseur.commande_id == CommandeFournisseur.id)
        .options(
            joinedload(LigneCommandeFournisseur.commande).joinedload(
                CommandeFournisseur.fournisseur
            ),
        )
        .order_by(CommandeFournisseur.date_commande.desc(), CommandeFournisseur.id.desc())
        .all()
    )
    return render_template(
        'stock/produit_detail.html',
        produit=produit,
        lots=lots,
        stock_dispo_total=int(stock_dispo_total),
        stock_reserve=int(stock_reserve or 0),
        lignes_achats=lignes_achats,
        metier_code_effectif=effective_metier_code(produit.categorie),
        photos_galerie=photos_galerie_triees(produit),
        max_galerie_photos=MAX_GALERIE_PHOTOS,
        peut_gerer_photos=user_has_permission(current_user, 'stock', 'update'),
    )


@stock_bp.route('/mouvements')
@login_required
@permission_required('stock', 'read')
def mouvements():
    mouvements_list = MouvementStock.query.order_by(MouvementStock.created_at.desc()).limit(100).all()
    lignes_entrees_prevues = (
        LigneCommandeFournisseur.query.join(
            CommandeFournisseur, LigneCommandeFournisseur.commande_id == CommandeFournisseur.id
        )
        .options(
            joinedload(LigneCommandeFournisseur.commande).joinedload(CommandeFournisseur.fournisseur),
            joinedload(LigneCommandeFournisseur.produit),
        )
        .filter(CommandeFournisseur.statut.in_(['envoyee', 'partiellement_recue']))
        .order_by(CommandeFournisseur.date_livraison_prevue.asc(), CommandeFournisseur.id.asc())
        .all()
    )
    lignes_entrees_prevues = [
        l for l in lignes_entrees_prevues if (int(l.quantite_commandee or 0) - int(l.quantite_recue or 0)) > 0
    ]

    lignes_sorties_prevues = (
        LigneBL.query.join(BonLivraison, LigneBL.bl_id == BonLivraison.id)
        .options(
            joinedload(LigneBL.bon_livraison).joinedload(BonLivraison.client),
            joinedload(LigneBL.produit),
            joinedload(LigneBL.lot),
        )
        .filter(BonLivraison.statut.in_(['prepare', 'partiellement_livre']))
        .order_by(BonLivraison.date_livraison.asc(), BonLivraison.id.asc())
        .all()
    )
    lignes_sorties_prevues = [
        l for l in lignes_sorties_prevues if (int(l.quantite_commandee or 0) - int(l.quantite_livree or 0)) > 0
    ]

    return render_template(
        'stock/mouvements.html',
        mouvements=mouvements_list,
        lignes_entrees_prevues=lignes_entrees_prevues,
        lignes_sorties_prevues=lignes_sorties_prevues,
    )

@stock_bp.route('/mouvements/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('stock', 'create')
def nouveau_mouvement():
    form = MouvementStockForm()
    
    # Populate choices
    form.produit_id.choices = [(p.id, f"{p.reference} - {p.designation}") for p in Produit.query.filter_by(est_actif=True).all()]
    form.lot_id.choices = [(0, '— Sélectionnez un lot —')] + [
        (l.id, f"{l.numero_lot} (stock: {int(l.quantite_disponible or 0)})") for l in Lot.query.all()
    ]
    
    # Optional shortcut for entree or sortie buttons from the index
    pre_selected_type = request.args.get('type')
    if pre_selected_type and request.method == 'GET':
        if pre_selected_type in ['entree', 'sortie']:
            form.type_mouvement.data = pre_selected_type

    if form.validate_on_submit():
        try:
            produit_id = form.produit_id.data
            lot_id = form.lot_id.data if form.lot_id.data != 0 else None
            type_mouvement = form.type_mouvement.data
            quantite = form.quantite.data
            
            if not lot_id:
                flash("Veuillez sélectionner un lot pour enregistrer le mouvement.", "danger")
                return render_template('stock/form_mouvement.html', form=form, title="Nouveau Mouvement")

            lot = Lot.query.filter_by(id=lot_id, produit_id=produit_id).first()
            if not lot:
                flash("Lot invalide pour ce produit.", "danger")
                return render_template('stock/form_mouvement.html', form=form, title="Nouveau Mouvement")

            if type_mouvement in ['entree', 'retour']:
                lot.quantite_disponible = int(lot.quantite_disponible or 0) + quantite
            elif type_mouvement in ['sortie', 'ajustement']:
                current = int(lot.quantite_disponible or 0)
                if current < quantite:
                    flash("Stock insuffisant sur ce lot pour cette sortie.", "danger")
                    return render_template('stock/form_mouvement.html', form=form, title="Nouveau Mouvement")
                lot.quantite_disponible = current - quantite

            _sync_stock_from_lots(produit_id)
            
            # Record Mouvement
            mvt = MouvementStock(
                produit_id=produit_id,
                lot_id=lot_id,
                type_mouvement=type_mouvement,
                quantite=quantite,
                motif=form.motif.data,
                reference_document=form.reference_document.data,
                utilisateur_id=current_user.id
            )
            db.session.add(mvt)
            
            db.session.commit()
            flash("Mouvement de stock enregistré avec succès.", "success")
            return redirect(url_for('stock.mouvements'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")

    return render_template('stock/form_mouvement.html', form=form, title="Nouveau Mouvement")

@stock_bp.route('/lots')
@login_required
@permission_required('stock', 'read')
def lots():
    lots_list = Lot.query.order_by(Lot.date_peremption.asc()).all()
    return render_template('stock/lots.html', lots=lots_list)

@stock_bp.route('/export')
@login_required
@permission_required('stock', 'read')
def export_stock():
    import datetime

    from ...utils.excel_generator import generate_excel

    from flask import send_file
    produits = Produit.query.all()
    headers = ['Référence', 'Désignation', 'Catégorie', 'PU HT', 'TVA(%)', 'Stock Dispo', 'Stock Réservé', 'Périmé?']
    data = []
    
    for p in produits:
        dispo = (
            db.session.query(func.coalesce(func.sum(Lot.quantite_disponible), 0))
            .filter(Lot.produit_id == p.id)
            .scalar()
            or 0
        )
        stock = Stock.query.filter_by(produit_id=p.id).first()
        res = stock.quantite_reservee if stock else 0
        
        # Check lots for expiration
        is_perime = "Non"
        for lot in p.lots:
             if lot.date_peremption and lot.date_peremption < datetime.date.today():
                 is_perime = "Oui"
                 break
        
        data.append([
            p.reference,
            p.designation,
            p.categorie.nom if p.categorie else '',
            float(p.prix_vente_ht),
            float(p.tva),
            dispo,
            res,
            is_perime
        ])
        
    excel_io = generate_excel(headers, data, sheet_title="Inventaire Stock")
    
    filename = f"Export_Stock_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(excel_io, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@stock_bp.route('/produit/photo/<path:stored_name>')
@login_required
@permission_required('stock', 'read')
def produit_photo_fichier(stored_name):
    """Affichage d'une photo produit (principale ou galerie)."""
    safe = stored_name.replace('\\', '/').lstrip('/')
    if not safe.startswith('produits/') or '..' in safe:
        flash('Image introuvable.', 'danger')
        return redirect(url_for('stock.index'))
    path = photo_abs_path(safe)
    if not path or not os.path.isfile(path):
        flash('Image introuvable.', 'danger')
        return redirect(url_for('stock.index'))
    return send_file(path, as_attachment=False, download_name=os.path.basename(path))


@stock_bp.route('/produit/<int:id>/photo-principale', methods=['POST'])
@login_required
@permission_required('stock', 'update')
def produit_photo_principale(id):
    produit = Produit.query.get_or_404(id)
    fichier = request.files.get('photo_principale')
    supprimer = request.form.get('supprimer_photo_principale') == '1'

    try:
        if supprimer:
            if produit.photo_principale:
                remove_produit_photo_file(produit.photo_principale)
                produit.photo_principale = None
                db.session.commit()
                flash('Photo principale supprimée.', 'success')
            return redirect(url_for('stock.detail_produit', id=id))

        if not fichier or not fichier.filename:
            flash('Choisissez une image (JPEG, PNG ou WebP).', 'warning')
            return redirect(url_for('stock.detail_produit', id=id))

        if produit.photo_principale:
            remove_produit_photo_file(produit.photo_principale)
        produit.photo_principale = upload_produit_photo(
            fichier, produit.reference, suffix='main'
        )
        db.session.commit()
        flash('Photo principale enregistrée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')

    return redirect(url_for('stock.detail_produit', id=id))


@stock_bp.route('/produit/<int:id>/galerie', methods=['POST'])
@login_required
@permission_required('stock', 'update')
def produit_galerie_ajouter(id):
    produit = Produit.query.options(joinedload(Produit.photos_galerie)).get_or_404(id)
    fichiers = request.files.getlist('photos_galerie') or []
    legende = (request.form.get('legende_galerie') or '').strip()[:255]

    nb_actuel = len(produit.photos_galerie or [])
    places = MAX_GALERIE_PHOTOS - nb_actuel
    if places <= 0:
        flash(f'Galerie pleine (maximum {MAX_GALERIE_PHOTOS} photos).', 'warning')
        return redirect(url_for('stock.detail_produit', id=id))

    ajoutes = 0
    try:
        ordre_base = max((p.ordre for p in produit.photos_galerie), default=-1) + 1
        for i, f in enumerate(fichiers):
            if ajoutes >= places:
                break
            if not f or not f.filename:
                continue
            stored = upload_produit_photo(f, produit.reference, suffix=f'gal{ordre_base + i}')
            db.session.add(
                ProduitPhoto(
                    produit_id=produit.id,
                    fichier=stored,
                    ordre=ordre_base + ajoutes,
                    legende=legende or None,
                )
            )
            ajoutes += 1
        if ajoutes:
            db.session.commit()
            flash(f'{ajoutes} photo(s) ajoutée(s) à la galerie.', 'success')
        else:
            flash('Aucune image valide sélectionnée.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')

    return redirect(url_for('stock.detail_produit', id=id))


@stock_bp.route('/produit/<int:id>/galerie/<int:photo_id>/supprimer', methods=['POST'])
@login_required
@permission_required('stock', 'update')
def produit_galerie_supprimer(id, photo_id):
    photo = ProduitPhoto.query.filter_by(id=photo_id, produit_id=id).first_or_404()
    try:
        remove_produit_photo_file(photo.fichier)
        db.session.delete(photo)
        db.session.commit()
        flash('Photo retirée de la galerie.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('stock.detail_produit', id=id))


@stock_bp.route('/api/produit/<int:id>')
@login_required
@permission_required('stock', 'read')
def api_produit_json(id):
    """Données produit + photos (préparation sync site public)."""
    produit = (
        Produit.query.options(
            joinedload(Produit.categorie),
            joinedload(Produit.photos_galerie),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    dm = produit.donnees_metier if isinstance(produit.donnees_metier, dict) else {}
    return jsonify(
        {
            'id': produit.id,
            'reference': produit.reference,
            'designation': produit.designation,
            'description': produit.description,
            'categorie': produit.categorie.nom if produit.categorie else None,
            'prix_vente_ht': float(produit.prix_vente_ht or 0),
            'prix_vente_ttc': float(produit.prix_vente_ttc or 0),
            'est_actif': bool(produit.est_actif),
            'donnees_metier': dm,
            'photos': produit_photos_payload(produit, external_urls=True),
        }
    )
