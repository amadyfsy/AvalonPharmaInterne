import datetime as dt
from datetime import datetime

from sqlalchemy import extract, func, or_
from ...extensions import db
from ...models.bon_livraison import BonLivraison, LigneBL
from ...models.client import Client
from ...models.depense import CategorieDepense, Depense
from ...models.facture import Facture, LigneFacture
from ...models.produit import Lot, Produit
from ...models.proforma import LigneProforma, Proforma
from ...models.parametres_documents import ParametresDocuments
from ...models.stock import MouvementStock, Stock
from ...utils.categorie_depense_registry import CODE_VENTE_LIEE, get_categorie_by_code
from ...utils.decorators import permission_required, user_has_permission
from ...utils.depense_justificatif import remove_justificatif_file, upload_depense_justificatif
from ...utils.depense_reference import prochaine_reference_depense
from ...utils.document_numero import (
    download_name_document,
    numero_bl_pour_facture,
    prochain_numero_document,
)
from ...utils.nombre_lettres import format_montant_espace
from ...utils.parametres_pdf import get_logo_filepath, merge_browser_print_logo, pdf_company_context
from ...utils.ventes_totaux import document_affiche_tva, montant_document_lettres
from ...utils.pdf_documents_reportlab import (
    build_bl_pdf_bytesio,
    build_facture_pdf_bytesio,
    build_proforma_pdf_bytesio,
)
from ...utils.pdf_generator import generate_pdf
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from . import ventes_bp


def _adresse_livraison_client(client: Client, override: str | None) -> str:
    txt = (override or '').strip() or (client.adresse or '').strip()
    return txt if txt else 'Adresse non renseignée'


def _categorie_depense_vente() -> CategorieDepense:
    cat = get_categorie_by_code(CODE_VENTE_LIEE)
    if cat:
        return cat
    cat = CategorieDepense.query.filter_by(nom='Dépenses liées aux ventes').first()
    if cat:
        if not (getattr(cat, 'code_systeme', None) or '').strip():
            cat.code_systeme = CODE_VENTE_LIEE
            db.session.flush()
        return cat
    cat = CategorieDepense(
        nom='Dépenses liées aux ventes',
        type_depense='variable',
        description='Transport, manutention et autres coûts associés à une vente.',
        icone='bi-cart-check',
        code_systeme=CODE_VENTE_LIEE,
    )
    db.session.add(cat)
    db.session.flush()
    return cat


def _creer_depense_liee_facture(
    *,
    facture: Facture,
    categorie: CategorieDepense,
    libelle_base: str,
    montant_ht: float,
    mode_paiement: str,
    justificatif_file,
    date_depense=None,
) -> Depense:
    d = date_depense or facture.date_emission or dt.date.today()
    reference = prochaine_reference_depense(d)
    justificatif = upload_depense_justificatif(
        justificatif_file, categorie.nom, reference
    )
    type_depense = getattr(categorie.type_depense, "value", categorie.type_depense) or "variable"
    dep = Depense(
        reference=reference,
        categorie_id=categorie.id,
        type_depense=type_depense,
        libelle=f"{libelle_base} (vente {facture.numero})",
        montant_ht=montant_ht,
        tva=0,
        montant_ttc=montant_ht,
        date_depense=d,
        mode_paiement=mode_paiement,
        fournisseur_id=None,
        justificatif=justificatif,
        statut="en_attente",
        created_by=current_user.id,
    )
    db.session.add(dep)
    db.session.flush()
    return dep


def _libelle_base_depense_vente(libelle: str, facture_numero: str) -> str:
    suffix = f" (vente {facture_numero})"
    txt = (libelle or "").strip()
    if txt.endswith(suffix):
        return txt[: -len(suffix)].strip()
    return txt


def _depense_liee_a_facture(depense: Depense, facture: Facture) -> bool:
    marker = f"(vente {facture.numero})"
    return marker in (depense.libelle or "")


def _get_depense_liee_facture(facture_id: int, depense_id: int) -> tuple[Facture, Depense]:
    from flask import abort

    facture = Facture.query.filter_by(id=facture_id).first_or_404()
    depense = (
        Depense.query.options(joinedload(Depense.categorie))
        .filter_by(id=depense_id)
        .first_or_404()
    )
    if not _depense_liee_a_facture(depense, facture):
        abort(404)
    return facture, depense


def _parse_depense_vente_form(facture: Facture, *, justificatif_required: bool):
    """Champs communs ajout / modification d'une dépense liée à une facture."""
    try:
        cat_id = int(request.form.get("categorie_id") or 0)
    except (TypeError, ValueError):
        cat_id = 0
    categorie = CategorieDepense.query.get(cat_id)
    if not categorie:
        raise ValueError("Catégorie de dépense invalide.")

    description = (request.form.get("description") or "").strip()
    libelle_base = description or (categorie.nom or "Dépense")
    try:
        montant_ht = float(request.form.get("montant_ht") or 0)
    except (TypeError, ValueError):
        montant_ht = 0.0
    if montant_ht <= 0:
        raise ValueError("Montant HT invalide.")

    mode = (request.form.get("mode_paiement") or "espece").strip()
    if mode not in ("espece", "cheque", "virement", "carte"):
        mode = "espece"

    date_raw = request.form.get("date_depense")
    if date_raw:
        try:
            date_depense = datetime.strptime(date_raw, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Date de dépense invalide.") from exc
    else:
        date_depense = facture.date_emission or dt.date.today()

    justificatif = request.files.get("justificatif")
    has_new_file = bool(justificatif and justificatif.filename)
    if justificatif_required and not has_new_file:
        raise ValueError("Justificatif obligatoire (PDF, PNG ou JPEG).")

    return {
        "categorie": categorie,
        "libelle_base": libelle_base,
        "montant_ht": montant_ht,
        "mode_paiement": mode,
        "date_depense": date_depense,
        "justificatif": justificatif if has_new_file else None,
    }


@ventes_bp.route('/')
@login_required
@permission_required('ventes', 'read')
def index():
    facture_id = request.args.get('facture_id', type=int)
    bl_id = request.args.get('bl_id', type=int)
    proforma_id = request.args.get('proforma_id', type=int)
    derniere_facture = Facture.query.get(facture_id) if facture_id else None
    dernier_bl = BonLivraison.query.get(bl_id) if bl_id else None
    dernier_proforma = Proforma.query.get(proforma_id) if proforma_id else None

    # Factures impayées (reste > 0, statuts ouverts)
    fq_imp = Facture.query.filter(
        Facture.statut.in_(["emise", "partiellement_payee"]),
        Facture.reste_a_payer > 0,
    )
    total_factures_impaye = (
        db.session.query(func.coalesce(func.sum(Facture.reste_a_payer), 0))
        .filter(
            Facture.statut.in_(["emise", "partiellement_payee"]),
            Facture.reste_a_payer > 0,
        )
        .scalar()
        or 0
    )
    nb_factures_impayees = fq_imp.count()

    # BL à livrer (pas encore livré entièrement / pas retourné)
    bl_a_livrer_list = (
        BonLivraison.query.filter(
            BonLivraison.statut.in_(["prepare", "partiellement_livre"])
        )
        .order_by(BonLivraison.date_livraison.asc(), BonLivraison.created_at.asc())
        .all()
    )
    nb_bl_a_livrer = len(bl_a_livrer_list)
    _seen_bl_cli = set()
    noms_clients_bl_livrer = []
    _ids_bl = list({bl.client_id for bl in bl_a_livrer_list})
    _map_bl = {
        c.id: c
        for c in Client.query.filter(Client.id.in_(_ids_bl)).all()
    } if _ids_bl else {}
    for bl in bl_a_livrer_list:
        if bl.client_id in _seen_bl_cli:
            continue
        _seen_bl_cli.add(bl.client_id)
        cl = _map_bl.get(bl.client_id)
        if cl and cl.raison_sociale:
            noms_clients_bl_livrer.append(cl.raison_sociale.strip())

    # Proformas non converties : montant total & nombre
    pf_ouverts_filter = Proforma.query.filter(
        ~Proforma.statut.in_(["converti", "refuse"]),
    )
    total_proformas_montant = (
        db.session.query(func.coalesce(func.sum(Proforma.total_ttc), 0))
        .filter(~Proforma.statut.in_(["converti", "refuse"]))
        .scalar()
        or 0
    )
    nb_proformas_ouverts = pf_ouverts_filter.count()

    # Proformas à suivre (envoyées / acceptées) — défilement noms clients
    pf_suivi_list = (
        Proforma.query.filter(Proforma.statut.in_(["envoye", "accepte"]))
        .order_by(Proforma.date_emission.asc(), Proforma.created_at.asc())
        .all()
    )
    nb_proformas_suivi = len(pf_suivi_list)
    _seen_pf_cli = set()
    noms_clients_proforma_suivi = []
    _ids_pf = list({pf.client_id for pf in pf_suivi_list})
    _map_pf = {
        c.id: c
        for c in Client.query.filter(Client.id.in_(_ids_pf)).all()
    } if _ids_pf else {}
    for pf in pf_suivi_list:
        if pf.client_id in _seen_pf_cli:
            continue
        _seen_pf_cli.add(pf.client_id)
        cl = _map_pf.get(pf.client_id)
        if cl and cl.raison_sociale:
            noms_clients_proforma_suivi.append(cl.raison_sociale.strip())

    hub_stats = {
        "total_factures_impaye": float(total_factures_impaye),
        "nb_factures_impayees": nb_factures_impayees,
        "nb_bl_a_livrer": nb_bl_a_livrer,
        "noms_clients_bl_livrer": noms_clients_bl_livrer,
        "total_proformas_montant": float(total_proformas_montant),
        "nb_proformas_ouverts": nb_proformas_ouverts,
        "nb_proformas_suivi": nb_proformas_suivi,
        "noms_clients_proforma_suivi": noms_clients_proforma_suivi,
        "clients_actifs": Client.query.filter_by(est_actif=True).count(),
    }
    return render_template(
        'ventes/index.html',
        derniere_facture=derniere_facture,
        dernier_bl=dernier_bl,
        dernier_proforma=dernier_proforma,
        hub_stats=hub_stats,
    )


def _produits_catalogue_vente():
    """Produits actifs avec stock pour le catalogue de la nouvelle vente."""
    produits_actifs = (
        Produit.query.filter_by(est_actif=True).order_by(Produit.designation).all()
    )
    catalogue = []
    for p in produits_actifs:
        st = Stock.query.filter_by(produit_id=p.id).first()
        dispo = int(st.quantite_disponible) if st else 0
        catalogue.append(
            {
                'obj': p,
                'stock_dispo': dispo,
                'prix_vente': float(p.prix_vente_ht or 0),
            }
        )
    return catalogue


@ventes_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
@permission_required('ventes', 'create')
def nouvelle_vente():
    """
    Point d’entrée des ventes : vente directe → facture (émise) + BL générés ;
    case « Proforma » → uniquement proforma (conversion facture + BL plus tard).
    """
    clients = Client.query.filter_by(est_actif=True).all()
    produits = Produit.query.filter_by(est_actif=True).all()
    depense_categories = CategorieDepense.query.order_by(CategorieDepense.nom).all()
    default_depense_cat = get_categorie_by_code(CODE_VENTE_LIEE) or (
        depense_categories[0] if depense_categories else None
    )
    today = dt.date.today()
    default_echeance = today + dt.timedelta(days=30)
    default_validite = today + dt.timedelta(days=30)

    if request.method == 'POST':
        proforma_only = request.form.get('proforma_seulement') == '1'
        try:
            client_id = int(request.form.get('client_id'))
            date_emission = datetime.strptime(request.form.get('date_emission'), '%Y-%m-%d').date()
            remise_globale = float(request.form.get('remise_globale', 0) or 0)

            produit_ids = request.form.getlist('produit_id[]')
            quantites = request.form.getlist('quantite[]')
            prix_unitaires = request.form.getlist('prix_unitaire_ht[]')

            if not produit_ids or not any(produit_ids):
                flash('Veuillez ajouter au moins un produit.', 'danger')
                return redirect(request.url)

            client = Client.query.get(client_id)
            if not client:
                flash('Client introuvable.', 'danger')
                return redirect(request.url)

            total_ht_global = 0.0
            tva_montant_global = 0.0
            lignes_calc = []

            for i in range(len(produit_ids)):
                if not produit_ids[i]:
                    continue
                pid = int(produit_ids[i])
                qte = int(quantites[i])
                pu = float(prix_unitaires[i])
                prod = Produit.query.get(pid)
                if not prod:
                    flash(f'Produit introuvable (id={pid}).', 'danger')
                    return redirect(request.url)
                montant_ligne_ht = pu * qte
                tva_ligne = montant_ligne_ht * (float(prod.tva) / 100)
                total_ht_global += montant_ligne_ht
                tva_montant_global += tva_ligne
                lignes_calc.append(
                    {
                        'produit_id': pid,
                        'quantite': qte,
                        'prix_unitaire_ht': pu,
                        'remise': 0,
                        'montant_ht': montant_ligne_ht,
                    }
                )

            total_ht_remise = total_ht_global * (1 - remise_globale / 100)
            tva_montant_remise = tva_montant_global * (1 - remise_globale / 100)
            total_ttc = total_ht_remise + tva_montant_remise

            if proforma_only:
                date_validite = datetime.strptime(
                    request.form.get('date_validite'), '%Y-%m-%d'
                ).date()
                notes = request.form.get('notes', '')
                annee = date_emission.year
                count = Proforma.query.filter(
                    db.extract('year', Proforma.date_emission) == annee
                ).count()
                numero = f'PROF-{annee}-{count + 1:04d}'

                proforma = Proforma(
                    numero=numero,
                    client_id=client_id,
                    date_emission=date_emission,
                    date_validite=date_validite,
                    remise_globale=remise_globale,
                    total_ht=total_ht_remise,
                    tva_montant=tva_montant_remise,
                    total_ttc=total_ttc,
                    statut='envoye',
                    notes=notes,
                    commercial_id=current_user.id,
                )
                db.session.add(proforma)
                db.session.flush()

                for row in lignes_calc:
                    db.session.add(
                        LigneProforma(
                            proforma_id=proforma.id,
                            produit_id=row['produit_id'],
                            quantite=row['quantite'],
                            prix_unitaire_ht=row['prix_unitaire_ht'],
                            remise=row['remise'],
                            montant_ht=row['montant_ht'],
                        )
                    )

                db.session.commit()
                flash(
                    f'Proforma {numero} enregistrée seule. Vous pourrez la convertir en facture + bon de livraison plus tard.',
                    'success',
                )
                return redirect(
                    url_for('ventes.index', proforma_id=proforma.id)
                )

            # Vente directe : facture émise + BL lié
            date_echeance = datetime.strptime(
                request.form.get('date_echeance'), '%Y-%m-%d'
            ).date()
            dl_str = request.form.get('date_livraison') or request.form.get(
                'date_emission'
            )
            date_livraison = datetime.strptime(dl_str, '%Y-%m-%d').date()
            adresse_liv = _adresse_livraison_client(
                client, request.form.get('adresse_livraison')
            )
            livreur = (request.form.get('livreur') or '').strip() or None
            bl_notes = (request.form.get('notes_bl') or '').strip() or None
            dep_libelles = request.form.getlist('depense_libelle[]')
            dep_descriptions = request.form.getlist('depense_description[]')
            dep_montants = request.form.getlist('depense_montant[]')
            dep_modes = request.form.getlist('depense_mode[]')
            dep_cat_ids = request.form.getlist('depense_categorie_id[]')
            dep_justifs = request.files.getlist('depense_justificatif[]')

            numero_fact = _prochain_numero_facture(date_emission)

            facture = Facture(
                numero=numero_fact,
                proforma_id=None,
                client_id=client_id,
                date_emission=date_emission,
                date_echeance=date_echeance,
                remise_globale=remise_globale,
                total_ht=total_ht_remise,
                tva_montant=tva_montant_remise,
                total_ttc=total_ttc,
                reste_a_payer=total_ttc,
                statut='emise',
                commercial_id=current_user.id,
            )
            db.session.add(facture)
            db.session.flush()

            for row in lignes_calc:
                db.session.add(
                    LigneFacture(
                        facture_id=facture.id,
                        produit_id=row['produit_id'],
                        quantite=row['quantite'],
                        prix_unitaire_ht=row['prix_unitaire_ht'],
                        remise=row['remise'],
                        montant_ht=row['montant_ht'],
                    )
                )

            numero_bl = numero_bl_pour_facture(facture)

            bl = BonLivraison(
                numero=numero_bl,
                facture_id=facture.id,
                client_id=client_id,
                date_livraison=date_livraison,
                adresse_livraison=adresse_liv,
                livreur=livreur,
                statut='prepare',
                notes=bl_notes,
            )
            db.session.add(bl)
            db.session.flush()

            for row in lignes_calc:
                db.session.add(
                    LigneBL(
                        bl_id=bl.id,
                        produit_id=row['produit_id'],
                        quantite_commandee=row['quantite'],
                        quantite_livree=0,
                    )
                )

            # Dépenses d'accompagnement (transport, etc.) : enregistrées en base, non imprimées sur la facture.
            dep_rows: list[dict] = []
            n_dep = max(
                len(dep_descriptions),
                len(dep_montants),
                len(dep_cat_ids),
                len(dep_modes),
                len(dep_justifs),
            )
            for i in range(n_dep):
                desc = (dep_descriptions[i] if i < len(dep_descriptions) else "").strip()
                libelle = desc
                cat_id = None
                try:
                    cat_id = int(dep_cat_ids[i]) if i < len(dep_cat_ids) and dep_cat_ids[i] else None
                except Exception:
                    cat_id = None
                cat_name = ""
                if cat_id is not None:
                    cat = CategorieDepense.query.get(cat_id)
                    cat_name = (cat.nom or "").strip() if cat else ""
                if not libelle and cat_name:
                    libelle = cat_name
                if not libelle:
                    continue
                montant_raw = dep_montants[i] if i < len(dep_montants) else "0"
                try:
                    montant_ht = float(montant_raw or 0)
                except Exception:
                    montant_ht = 0.0
                if montant_ht <= 0:
                    continue
                mode = (dep_modes[i] if i < len(dep_modes) else "espece") or "espece"
                if mode not in ("espece", "cheque", "virement", "carte"):
                    mode = "espece"
                justif_file = dep_justifs[i] if i < len(dep_justifs) else None
                if justif_file and not justif_file.filename:
                    justif_file = None
                dep_rows.append(
                    {
                        "libelle": libelle,
                        "montant_ht": montant_ht,
                        "mode": mode,
                        "cat_id": cat_id,
                        "justificatif": justif_file,
                    }
                )

            if dep_rows:
                cat_dep_default = _categorie_depense_vente()
                for row in dep_rows:
                    cat_dep = (
                        CategorieDepense.query.get(row["cat_id"])
                        if row["cat_id"] is not None
                        else cat_dep_default
                    ) or cat_dep_default
                    _creer_depense_liee_facture(
                        facture=facture,
                        categorie=cat_dep,
                        libelle_base=row["libelle"],
                        montant_ht=row["montant_ht"],
                        mode_paiement=row["mode"],
                        justificatif_file=row["justificatif"],
                        date_depense=date_emission,
                    )

            db.session.commit()
            flash(
                f'Vente enregistrée : facture et BL n° {numero_fact} créés. '
                'PDF disponibles ci-dessous ou depuis les listes.',
                'success',
            )
            return redirect(
                url_for('ventes.index', facture_id=facture.id, bl_id=bl.id)
            )

        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la vente : {str(e)}', 'danger')

    return render_template(
        'ventes/form_vente.html',
        clients=clients,
        produits=produits,
        produits_data=_produits_catalogue_vente(),
        depense_categories=depense_categories,
        default_depense_cat_id=default_depense_cat.id if default_depense_cat else None,
        title='Nouvelle vente',
        today=today.isoformat(),
        default_echeance=default_echeance.isoformat(),
        default_validite=default_validite.isoformat(),
        prefill_proforma=request.args.get('mode') == 'proforma',
    )

PROFORMAS_PAR_PAGE = 15

_STATUTS_PROFORMA = (
    'brouillon',
    'envoye',
    'accepte',
    'refuse',
    'converti',
)


@ventes_bp.route('/proformas')
@login_required
@permission_required('ventes', 'read')
def proformas():
    q = (request.args.get('q') or '').strip()
    statut = (request.args.get('statut') or '').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if statut and statut not in _STATUTS_PROFORMA:
        statut = ''

    query = Proforma.query.options(joinedload(Proforma.client))
    if q:
        pattern = f'%{q}%'
        query = query.join(Client, Proforma.client_id == Client.id).filter(
            or_(
                Proforma.numero.ilike(pattern),
                Client.raison_sociale.ilike(pattern),
            )
        )
    if statut:
        query = query.filter(Proforma.statut == statut)

    pagination = (
        query.order_by(
            Proforma.date_emission.desc(),
            Proforma.created_at.desc(),
            Proforma.id.desc(),
        )
        .paginate(page=page, per_page=PROFORMAS_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if q:
        filtres_url['q'] = q
    if statut:
        filtres_url['statut'] = statut

    return render_template(
        'ventes/proformas_index.html',
        proformas=pagination.items,
        pagination=pagination,
        q=q,
        statut_filtre=statut,
        filtres_url=filtres_url,
        statuts_proforma=_STATUTS_PROFORMA,
    )


@ventes_bp.route('/proformas/<int:id>')
@login_required
@permission_required('ventes', 'read')
def proforma_detail(id):
    proforma = (
        Proforma.query.options(
            joinedload(Proforma.client),
            joinedload(Proforma.lignes).joinedload(LigneProforma.produit),
            joinedload(Proforma.factures),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    facture_issue = (proforma.factures[0] if getattr(proforma, "factures", None) else None)
    return render_template(
        'ventes/proforma_detail.html',
        proforma=proforma,
        facture_issue=facture_issue,
        format_fcfa=format_montant_espace,
        affiche_tva=document_affiche_tva(proforma),
    )

FACTURES_PAR_PAGE = 15
BL_PAR_PAGE = 15

_STATUTS_BL = (
    'prepare',
    'livre',
    'partiellement_livre',
    'retourne',
)

_STATUTS_FACTURE = (
    'brouillon',
    'emise',
    'partiellement_payee',
    'payee',
    'annulee',
)


@ventes_bp.route('/factures')
@login_required
@permission_required('ventes', 'read')
def factures():
    q = (request.args.get('q') or '').strip()
    statut = (request.args.get('statut') or '').strip()
    annee = request.args.get('annee', type=int)
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if statut and statut not in _STATUTS_FACTURE:
        statut = ''

    annees_dispo = [
        int(y)
        for (y,) in db.session.query(extract('year', Facture.date_emission))
        .filter(Facture.date_emission.isnot(None))
        .distinct()
        .order_by(extract('year', Facture.date_emission).desc())
        .all()
        if y is not None
    ]
    if annee and annee not in annees_dispo:
        annee = None

    query = Facture.query.options(joinedload(Facture.client))
    if q:
        pattern = f'%{q}%'
        query = query.join(Client, Facture.client_id == Client.id).filter(
            or_(
                Facture.numero.ilike(pattern),
                Client.raison_sociale.ilike(pattern),
            )
        )
    if statut:
        query = query.filter(Facture.statut == statut)
    if annee:
        query = query.filter(extract('year', Facture.date_emission) == annee)

    pagination = (
        query.order_by(
            Facture.date_emission.desc(),
            Facture.created_at.desc(),
            Facture.id.desc(),
        )
        .paginate(page=page, per_page=FACTURES_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if q:
        filtres_url['q'] = q
    if statut:
        filtres_url['statut'] = statut
    if annee:
        filtres_url['annee'] = annee

    bl_par_facture = {}
    if pagination.items:
        facture_ids = [f.id for f in pagination.items]
        for bl_row in BonLivraison.query.filter(BonLivraison.facture_id.in_(facture_ids)).all():
            bl_par_facture[bl_row.facture_id] = bl_row

    return render_template(
        'ventes/factures_index.html',
        factures=pagination.items,
        pagination=pagination,
        q=q,
        statut_filtre=statut,
        annee_filtre=annee,
        annees_dispo=annees_dispo,
        filtres_url=filtres_url,
        statuts_facture=_STATUTS_FACTURE,
        bl_par_facture=bl_par_facture,
        format_fcfa=format_montant_espace,
    )

@ventes_bp.route('/bons-livraison')
@login_required
@permission_required('ventes', 'read')
def bons_livraison():
    q = (request.args.get('q') or '').strip()
    statut = (request.args.get('statut') or '').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if statut and statut not in _STATUTS_BL:
        statut = ''

    query = BonLivraison.query.options(joinedload(BonLivraison.client))
    if q:
        pattern = f'%{q}%'
        query = query.join(Client, BonLivraison.client_id == Client.id).filter(
            or_(
                BonLivraison.numero.ilike(pattern),
                Client.raison_sociale.ilike(pattern),
            )
        )
    if statut:
        query = query.filter(BonLivraison.statut == statut)

    pagination = (
        query.order_by(
            BonLivraison.date_livraison.desc(),
            BonLivraison.created_at.desc(),
            BonLivraison.id.desc(),
        )
        .paginate(page=page, per_page=BL_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if q:
        filtres_url['q'] = q
    if statut:
        filtres_url['statut'] = statut

    return render_template(
        'ventes/bl_index.html',
        bls=pagination.items,
        pagination=pagination,
        q=q,
        statut_filtre=statut,
        filtres_url=filtres_url,
        statuts_bl=_STATUTS_BL,
    )


@ventes_bp.route('/bons-livraison/<int:id>')
@login_required
@permission_required('ventes', 'read')
def bl_detail(id):
    bl = (
        BonLivraison.query.options(
            joinedload(BonLivraison.client),
            joinedload(BonLivraison.lignes).joinedload(LigneBL.produit),
            joinedload(BonLivraison.lignes).joinedload(LigneBL.lot),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    return render_template('ventes/bl_detail.html', bl=bl)


# --- API AJAX pour les Lignes Dynamiques ---

@ventes_bp.route('/api/produits/<int:id>')
@login_required
def get_produit_info(id):
    produit = Produit.query.get_or_404(id)
    # On pourrait aussi renvoyer le stock disponible ici, ou les lots
    return jsonify({
        'id': produit.id,
        'reference': produit.reference,
        'designation': produit.designation,
        'prix_vente_ht': float(produit.prix_vente_ht),
        'tva': float(produit.tva),
        'unite': produit.unite
    })

# --- CRUD Proforma ---

@ventes_bp.route('/proformas/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('ventes', 'create')
def nouveau_proforma():
    clients = Client.query.filter_by(est_actif=True).all()
    produits = Produit.query.filter_by(est_actif=True).all()
    
    if request.method == 'POST':
        try:
            client_id = int(request.form.get('client_id'))
            date_emission = datetime.strptime(request.form.get('date_emission'), '%Y-%m-%d').date()
            date_validite = datetime.strptime(request.form.get('date_validite'), '%Y-%m-%d').date()
            remise_globale = float(request.form.get('remise_globale', 0) or 0)
            notes = request.form.get('notes', '')
            
            # Récupérer les données des lignes (tableaux)
            produit_ids = request.form.getlist('produit_id[]')
            quantites = request.form.getlist('quantite[]')
            prix_unitaires = request.form.getlist('prix_unitaire_ht[]')
            
            if not produit_ids:
                flash("Veuillez ajouter au moins un produit.", "danger")
                return redirect(request.url)

            # Numéro automatique (ex: PROF-2023-0001)
            annee = date_emission.year
            count = Proforma.query.filter(db.extract('year', Proforma.date_emission) == annee).count()
            numero = f"PROF-{annee}-{count+1:04d}"

            total_ht_global = 0.0
            tva_montant_global = 0.0
            
            proforma = Proforma(
                numero=numero,
                client_id=client_id,
                date_emission=date_emission,
                date_validite=date_validite,
                remise_globale=remise_globale,
                total_ht=0, # sera mis à jour
                tva_montant=0, # sera mis à jour
                total_ttc=0, # sera mis à jour
                statut='brouillon',
                notes=notes,
                commercial_id=current_user.id
            )
            db.session.add(proforma)
            db.session.flush() # pour avoir l'ID
            
            for i in range(len(produit_ids)):
                if not produit_ids[i]: continue
                pid = int(produit_ids[i])
                qte = int(quantites[i])
                pu = float(prix_unitaires[i])
                
                prod = Produit.query.get(pid)
                
                montant_ligne_ht = pu * qte
                tva_ligne = montant_ligne_ht * (float(prod.tva) / 100)
                
                total_ht_global += montant_ligne_ht
                tva_montant_global += tva_ligne
                
                ligne = LigneProforma(
                    proforma_id=proforma.id,
                    produit_id=pid,
                    quantite=qte,
                    prix_unitaire_ht=pu,
                    remise=0,
                    montant_ht=montant_ligne_ht
                )
                db.session.add(ligne)
            
            # Application remise globale sur HT
            total_ht_remise = total_ht_global * (1 - remise_globale/100)
            # Simplification: Ajustement proportionnel de la TVA si remise globale
            tva_montant_remise = tva_montant_global * (1 - remise_globale/100)
            
            proforma.total_ht = total_ht_remise
            proforma.tva_montant = tva_montant_remise
            proforma.total_ttc = total_ht_remise + tva_montant_remise
            
            db.session.commit()
            flash(f'Proforma {numero} créé avec succès.', 'success')
            return redirect(url_for('ventes.proformas'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")

    return render_template('ventes/form_proforma.html', clients=clients, produits=produits, title="Nouveau Proforma")

@ventes_bp.route('/proformas/<int:id>/convertir', methods=['POST'])
@login_required
@permission_required('ventes', 'update')
def convertir_proforma(id):
    proforma = Proforma.query.get_or_404(id)
    if proforma.statut == 'converti':
        flash('Cette proforma a déjà été convertie en facture et bon de livraison.', 'warning')
        return redirect(url_for('ventes.proformas'))

    try:
        client = proforma.client
        if not client:
            flash('Client de la proforma introuvable.', 'danger')
            return redirect(url_for('ventes.proformas'))

        today = dt.date.today()
        numero_fact = _prochain_numero_facture(today)
        date_echeance = today + dt.timedelta(days=30)

        facture = Facture(
            numero=numero_fact,
            proforma_id=proforma.id,
            client_id=proforma.client_id,
            date_emission=today,
            date_echeance=date_echeance,
            remise_globale=proforma.remise_globale,
            total_ht=proforma.total_ht,
            tva_montant=proforma.tva_montant,
            total_ttc=proforma.total_ttc,
            reste_a_payer=proforma.total_ttc,
            statut='emise',
            commercial_id=proforma.commercial_id,
        )
        db.session.add(facture)
        db.session.flush()

        for p_ligne in proforma.lignes:
            db.session.add(
                LigneFacture(
                    facture_id=facture.id,
                    produit_id=p_ligne.produit_id,
                    quantite=p_ligne.quantite,
                    prix_unitaire_ht=p_ligne.prix_unitaire_ht,
                    remise=p_ligne.remise,
                    montant_ht=p_ligne.montant_ht,
                )
            )

        adresse_liv = _adresse_livraison_client(client, None)
        numero_bl = numero_bl_pour_facture(facture)

        bl = BonLivraison(
            numero=numero_bl,
            facture_id=facture.id,
            client_id=proforma.client_id,
            date_livraison=today,
            adresse_livraison=adresse_liv,
            livreur=None,
            statut='prepare',
            notes=(proforma.notes or '').strip() or None,
        )
        db.session.add(bl)
        db.session.flush()

        for p_ligne in proforma.lignes:
            db.session.add(
                LigneBL(
                    bl_id=bl.id,
                    produit_id=p_ligne.produit_id,
                    quantite_commandee=p_ligne.quantite,
                    quantite_livree=0,
                )
            )

        proforma.statut = 'converti'
        db.session.commit()
        flash(
            f'Proforma convertie : facture et BL n° {numero_fact} créés (statut préparé).',
            'success',
        )
        return redirect(
            url_for('ventes.index', facture_id=facture.id, bl_id=bl.id)
        )
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la conversion : {str(e)}', 'danger')

    return redirect(url_for('ventes.proformas'))

# --- CRUD Factures ---

FACTURE_EDITABLE_STATUTS = frozenset({"brouillon", "emise", "partiellement_payee"})


def _prochain_numero_facture(d_emission, exclude_facture_id=None):
    """
    Numéro YYYY/MM/NN (ex. 2026/06/02) : année/mois d'émission,
    NN = prochain rang libre du mois (partagé avec les BL).
    """
    return prochain_numero_document(d_emission, exclude_facture_id=exclude_facture_id)


def _clients_for_facture_form(facture=None):
    if facture is not None:
        return (
            Client.query.filter(db.or_(Client.est_actif == True, Client.id == facture.client_id))  # noqa: E712
            .order_by(Client.raison_sociale)
            .all()
        )
    return Client.query.filter_by(est_actif=True).order_by(Client.raison_sociale).all()


def _parse_facture_post():
    """Analyse le formulaire facture ; lève ValueError si invalide."""
    raw_client = request.form.get("client_id")
    if not raw_client:
        raise ValueError("Client requis.")
    client_id = int(raw_client)
    date_emission = datetime.strptime(request.form.get("date_emission"), "%Y-%m-%d").date()
    date_echeance = datetime.strptime(request.form.get("date_echeance"), "%Y-%m-%d").date()
    remise_globale = float(request.form.get("remise_globale", 0) or 0)
    bc = (request.form.get("bc") or "").strip() or None

    produit_ids = request.form.getlist("produit_id[]")
    quantites = request.form.getlist("quantite[]")
    prix_unitaires = request.form.getlist("prix_unitaire_ht[]")

    lignes = []
    total_ht_global = 0.0
    tva_montant_global = 0.0

    for i in range(len(produit_ids)):
        if not produit_ids[i]:
            continue
        pid = int(produit_ids[i])
        qte = int(quantites[i])
        pu = float(prix_unitaires[i])
        prod = Produit.query.get(pid)
        if not prod:
            raise ValueError(f"Produit {pid} introuvable.")
        montant_ligne_ht = pu * qte
        tva_ligne = montant_ligne_ht * (float(prod.tva) / 100)
        total_ht_global += montant_ligne_ht
        tva_montant_global += tva_ligne
        lignes.append(
            {
                "produit_id": pid,
                "quantite": qte,
                "prix_unitaire_ht": pu,
                "remise": 0,
                "montant_ht": montant_ligne_ht,
            }
        )

    if not lignes:
        raise ValueError("Ajoutez au moins une ligne produit valide.")

    return {
        "client_id": client_id,
        "date_emission": date_emission,
        "date_echeance": date_echeance,
        "remise_globale": remise_globale,
        "bc": bc,
        "lignes": lignes,
        "total_ht_global": total_ht_global,
        "tva_montant_global": tva_montant_global,
    }


def _apply_totals_to_facture(facture, data):
    rem = data["remise_globale"]
    total_ht_remise = data["total_ht_global"] * (1 - rem / 100)
    tva_montant_remise = data["tva_montant_global"] * (1 - rem / 100)
    total_ttc = total_ht_remise + tva_montant_remise
    facture.client_id = data["client_id"]
    facture.date_emission = data["date_emission"]
    facture.date_echeance = data["date_echeance"]
    facture.remise_globale = rem
    facture.bc = data.get("bc")
    facture.total_ht = total_ht_remise
    facture.tva_montant = tva_montant_remise
    facture.total_ttc = total_ttc
    if facture.statut == "brouillon":
        facture.reste_a_payer = total_ttc
    else:
        mp = float(facture.montant_paye or 0)
        tt = float(total_ttc)
        reste = max(0.0, tt - mp)
        facture.reste_a_payer = reste
        if reste <= 0.001:
            facture.statut = "payee"
        elif mp > 0.001:
            facture.statut = "partiellement_payee"
        else:
            facture.statut = "emise"


def _replace_lignes_facture(facture_id, lignes_specs):
    LigneFacture.query.filter_by(facture_id=facture_id).delete(synchronize_session=False)
    for spec in lignes_specs:
        db.session.add(
            LigneFacture(
                facture_id=facture_id,
                produit_id=spec["produit_id"],
                quantite=spec["quantite"],
                prix_unitaire_ht=spec["prix_unitaire_ht"],
                remise=spec["remise"],
                montant_ht=spec["montant_ht"],
            )
        )


def _sync_bl_depuis_facture(facture: Facture, bl: BonLivraison | None) -> bool:
    """Recopie les lignes facture → BL (mêmes produits et quantités) si BL encore préparé."""
    if bl is None or bl.statut != "prepare":
        return False
    lignes_facture = sorted(facture.lignes or [], key=lambda x: x.id)
    LigneBL.query.filter_by(bl_id=bl.id).delete(synchronize_session=False)
    for lf in lignes_facture:
        db.session.add(
            LigneBL(
                bl_id=bl.id,
                produit_id=lf.produit_id,
                lot_id=getattr(lf, "lot_id", None),
                quantite_commandee=int(lf.quantite or 0),
                quantite_livree=0,
            )
        )
    return True


def _bl_desaligne_depuis_facture(facture: Facture, bl: BonLivraison | None) -> bool:
    if bl is None or bl.statut != "prepare":
        return False
    f_map = {lf.produit_id: int(lf.quantite or 0) for lf in (facture.lignes or [])}
    b_map = {lb.produit_id: int(lb.quantite_commandee or 0) for lb in (bl.lignes or [])}
    return f_map != b_map


@ventes_bp.route("/factures/<int:id>")
@login_required
@permission_required("ventes", "read")
def facture_detail(id):
    facture = (
        Facture.query.options(
            joinedload(Facture.client),
            joinedload(Facture.lignes).joinedload(LigneFacture.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    bl = (
        BonLivraison.query.options(
            joinedload(BonLivraison.lignes).joinedload(LigneBL.produit),
        )
        .filter_by(facture_id=id)
        .first()
    )
    if bl and _bl_desaligne_depuis_facture(facture, bl):
        _sync_bl_depuis_facture(facture, bl)
        db.session.commit()
        bl = (
            BonLivraison.query.options(
                joinedload(BonLivraison.lignes).joinedload(LigneBL.produit),
            )
            .filter_by(facture_id=id)
            .first()
        )
        flash("Le bon de livraison a été realigné sur les quantités de la facture.", "info")
    proforma = None
    if facture.proforma_id:
        proforma = Proforma.query.get(facture.proforma_id)
    depenses_liees = (
        Depense.query.options(joinedload(Depense.categorie))
        .filter(Depense.libelle.ilike(f"%(vente {facture.numero})%"))
        .order_by(Depense.date_depense.desc(), Depense.id.desc())
        .all()
    )
    depenses_liees_total = float(sum(float(d.montant_ttc or 0) for d in depenses_liees))
    depense_categories = CategorieDepense.query.order_by(CategorieDepense.nom).all()
    peut_ajouter_depense = user_has_permission(current_user, "depenses", "saisir")
    return render_template(
        "ventes/facture_detail.html",
        facture=facture,
        bl=bl,
        proforma_src=proforma,
        depenses_liees=depenses_liees,
        depenses_liees_total=depenses_liees_total,
        depense_categories=depense_categories,
        peut_ajouter_depense=peut_ajouter_depense,
        format_fcfa=format_montant_espace,
        affiche_tva=document_affiche_tva(facture),
    )


@ventes_bp.route("/factures/<int:id>/depenses", methods=["POST"])
@login_required
@permission_required("depenses", "saisir")
def facture_ajouter_depense(id):
    facture = Facture.query.filter_by(id=id).first_or_404()
    if facture.statut == "annulee":
        flash("Impossible d'ajouter une dépense à une facture annulée.", "warning")
        return redirect(url_for("ventes.facture_detail", id=id))

    try:
        data = _parse_depense_vente_form(facture, justificatif_required=False)
        _creer_depense_liee_facture(
            facture=facture,
            categorie=data["categorie"],
            libelle_base=data["libelle_base"],
            montant_ht=data["montant_ht"],
            mode_paiement=data["mode_paiement"],
            justificatif_file=data["justificatif"],
            date_depense=data["date_depense"],
        )
        db.session.commit()
        flash("Dépense liée enregistrée (en attente de validation).", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("ventes.facture_detail", id=id))


@ventes_bp.route("/factures/<int:id>/depenses/<int:depense_id>/modifier", methods=["POST"])
@login_required
@permission_required("depenses", "saisir")
def facture_modifier_depense(id, depense_id):
    facture, depense = _get_depense_liee_facture(id, depense_id)

    if facture.statut == "annulee":
        flash("Impossible de modifier une dépense sur une facture annulée.", "warning")
        return redirect(url_for("ventes.facture_detail", id=id))

    if depense.statut != "en_attente":
        flash("Seules les dépenses en attente de validation peuvent être modifiées.", "warning")
        return redirect(url_for("ventes.facture_detail", id=id))

    try:
        data = _parse_depense_vente_form(
            facture,
            justificatif_required=False,
        )
        categorie = data["categorie"]
        type_depense = getattr(categorie.type_depense, "value", categorie.type_depense) or "variable"

        depense.categorie_id = categorie.id
        depense.type_depense = type_depense
        depense.libelle = f"{data['libelle_base']} (vente {facture.numero})"
        depense.montant_ht = data["montant_ht"]
        depense.tva = 0
        depense.montant_ttc = data["montant_ht"]
        depense.date_depense = data["date_depense"]
        depense.mode_paiement = data["mode_paiement"]

        if data["justificatif"]:
            remove_justificatif_file(depense.justificatif)
            depense.justificatif = upload_depense_justificatif(
                data["justificatif"],
                categorie.nom,
                depense.reference,
            )

        db.session.commit()
        flash("Dépense liée mise à jour.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("ventes.facture_detail", id=id))


@ventes_bp.route("/factures/<int:id>/modifier", methods=["GET", "POST"])
@login_required
@permission_required("ventes", "create")
def modifier_facture(id):
    facture = (
        Facture.query.options(joinedload(Facture.lignes))
        .filter_by(id=id)
        .first_or_404()
    )
    if facture.statut not in FACTURE_EDITABLE_STATUTS:
        flash(
            "Cette facture ne peut pas être modifiée (statut payée, annulée ou autre).",
            "warning",
        )
        return redirect(url_for("ventes.facture_detail", id=id))

    clients = _clients_for_facture_form(facture)
    produits = Produit.query.filter_by(est_actif=True).order_by(Produit.designation).all()

    if request.method == "POST":
        try:
            if facture.statut != "brouillon":
                if request.form.get("confirm_edit_facture_emise") != "1":
                    flash(
                        "Cochez la case de confirmation pour modifier une facture déjà émise.",
                        "warning",
                    )
                    return render_template(
                        "ventes/form_facture.html",
                        clients=clients,
                        produits=produits,
                        facture=facture,
                        title=f"Modifier la facture {facture.numero}",
                        form_action=url_for("ventes.modifier_facture", id=facture.id),
                        edit_requires_confirm=True,
                    )
            data = _parse_facture_post()
            old_em = facture.date_emission
            if facture.statut == "brouillon" and (
                data["date_emission"].year != old_em.year
                or data["date_emission"].month != old_em.month
            ):
                facture.numero = _prochain_numero_facture(
                    data["date_emission"], exclude_facture_id=facture.id
                )
            _replace_lignes_facture(facture.id, data["lignes"])
            _apply_totals_to_facture(facture, data)
            db.session.flush()
            bl_lie = BonLivraison.query.filter_by(facture_id=facture.id).first()
            if bl_lie and bl_lie.numero != facture.numero:
                # Facture et BL portent toujours le même numéro
                conflit = BonLivraison.query.filter(
                    BonLivraison.numero == facture.numero,
                    BonLivraison.id != bl_lie.id,
                ).first()
                if not conflit:
                    bl_lie.numero = facture.numero
            if _sync_bl_depuis_facture(facture, bl_lie):
                flash("Le bon de livraison lié a été aligné sur les lignes de la facture.", "info")
            if facture.statut != "brouillon":
                mp = float(facture.montant_paye or 0)
                tt = float(facture.total_ttc)
                if mp > tt + 0.01:
                    flash(
                        "Attention : les paiements enregistrés dépassent le nouveau total TTC. "
                        "Vérifiez les écritures et les montants payés.",
                        "warning",
                    )
            db.session.commit()
            flash(f"Facture {facture.numero} mise à jour.", "success")
            return redirect(url_for("ventes.facture_detail", id=facture.id))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement : {e}", "danger")

    return render_template(
        "ventes/form_facture.html",
        clients=clients,
        produits=produits,
        facture=facture,
        title=f"Modifier la facture {facture.numero}",
        form_action=url_for("ventes.modifier_facture", id=facture.id),
        edit_requires_confirm=(facture.statut != "brouillon"),
    )


@ventes_bp.route("/factures/<int:id>/emettre", methods=["POST"])
@login_required
@permission_required("ventes", "create")
def emettre_facture(id):
    facture = Facture.query.get_or_404(id)
    if facture.statut != "brouillon":
        flash("Cette facture n'est pas un brouillon.", "info")
        return redirect(url_for("ventes.facture_detail", id=id))
    try:
        facture.statut = "emise"
        db.session.commit()
        flash(f"Facture {facture.numero} émise.", "success")
    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")
    return redirect(url_for("ventes.facture_detail", id=id))


@ventes_bp.route('/factures/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('ventes', 'create')
def nouveau_facture():
    clients = _clients_for_facture_form(None)
    produits = Produit.query.filter_by(est_actif=True).order_by(Produit.designation).all()

    if request.method == 'POST':
        try:
            data = _parse_facture_post()
            numero = _prochain_numero_facture(data["date_emission"])

            facture = Facture(
                numero=numero,
                client_id=data["client_id"],
                date_emission=data["date_emission"],
                date_echeance=data["date_echeance"],
                remise_globale=data["remise_globale"],
                total_ht=0,
                tva_montant=0,
                total_ttc=0,
                reste_a_payer=0,
                statut='brouillon',
                commercial_id=current_user.id
            )
            db.session.add(facture)
            db.session.flush()
            _replace_lignes_facture(facture.id, data["lignes"])
            _apply_totals_to_facture(facture, data)

            db.session.commit()
            flash(f'Facture {numero} créée avec succès.', 'success')
            return redirect(url_for('ventes.facture_detail', id=facture.id))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement de la facture: {str(e)}", "danger")

    return render_template(
        'ventes/form_facture.html',
        clients=clients,
        produits=produits,
        title="Nouvelle facture",
        form_action=url_for('ventes.nouveau_facture'),
    )

# --- CRUD Bons de Livraison ---

@ventes_bp.route('/bons-livraison/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('ventes', 'create')
def nouveau_bl():
    clients = Client.query.filter_by(est_actif=True).all()
    produits = Produit.query.filter_by(est_actif=True).all()
    
    if request.method == 'POST':
        try:
            client_id = int(request.form.get('client_id'))
            date_livraison = datetime.strptime(request.form.get('date_livraison'), '%Y-%m-%d').date()
            adresse_livraison = request.form.get('adresse_livraison', '')
            livreur = request.form.get('livreur', '')
            notes = request.form.get('notes', '')
            
            produit_ids = request.form.getlist('produit_id[]')
            quantites = request.form.getlist('quantite[]')
            
            if not produit_ids:
                flash("Veuillez ajouter au moins un produit.", "danger")
                return redirect(request.url)

            # BL seul : même nomenclature YYYY/MM/NN (séquence partagée)
            numero = prochain_numero_document(date_livraison)
            
            bl = BonLivraison(
                numero=numero,
                client_id=client_id,
                date_livraison=date_livraison,
                adresse_livraison=adresse_livraison,
                livreur=livreur,
                statut='prepare',
                notes=notes
            )
            db.session.add(bl)
            db.session.flush()
            
            for i in range(len(produit_ids)):
                if not produit_ids[i]: continue
                pid = int(produit_ids[i])
                qte = int(quantites[i])
                
                ligne = LigneBL(
                    bl_id=bl.id,
                    produit_id=pid,
                    quantite_commandee=qte,
                    quantite_livree=0 # 0 tant qu'il n'est pas "livré"
                )
                db.session.add(ligne)
            
            db.session.commit()
            flash(f'Bon de Livraison {numero} créé avec succès.', 'success')
            return redirect(url_for('ventes.bons_livraison'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement du BL: {str(e)}", "danger")

    return render_template('ventes/form_bl.html', clients=clients, produits=produits, title="Nouveau Bon de Livraison")

@ventes_bp.route('/bons-livraison/<int:id>/valider', methods=['POST'])
@login_required
@permission_required('ventes', 'update')
def valider_bl(id):
    bl = BonLivraison.query.get_or_404(id)
    if bl.statut == 'livre':
        flash("Ce Bon de Livraison est déjà validé.", "warning")
        return redirect(url_for('ventes.bons_livraison'))
        
    try:
        # 1. Update BL status to delivered
        bl.statut = 'livre'
        touched_products = set()
        
        # 2. Process lines: sortie depuis lots (lot imposé ou allocation FEFO)
        for ligne in bl.lignes:
            reste = int(ligne.quantite_commandee or 0) - int(ligne.quantite_livree or 0)
            if reste <= 0:
                continue

            allocations = []
            if ligne.lot_id:
                lot = Lot.query.filter_by(id=ligne.lot_id, produit_id=ligne.produit_id).first()
                if not lot:
                    raise ValueError(f"Lot invalide sur ligne BL (produit {ligne.produit_id}).")
                if int(lot.quantite_disponible or 0) < reste:
                    raise ValueError(f"Stock insuffisant sur le lot {lot.numero_lot} (BL {bl.numero}).")
                allocations.append((lot, reste))
            else:
                lots = (
                    Lot.query.filter(
                        Lot.produit_id == ligne.produit_id,
                        Lot.quantite_disponible > 0,
                    )
                    .order_by(Lot.date_peremption.asc(), Lot.id.asc())
                    .all()
                )
                a_sortir = reste
                for lot in lots:
                    dispo = int(lot.quantite_disponible or 0)
                    if dispo <= 0:
                        continue
                    take = min(dispo, a_sortir)
                    if take > 0:
                        allocations.append((lot, take))
                        a_sortir -= take
                    if a_sortir <= 0:
                        break
                if a_sortir > 0:
                    raise ValueError(
                        f"Stock lot insuffisant pour le produit {ligne.produit_id} (reste à sortir: {a_sortir})."
                    )

            for lot, qte in allocations:
                lot.quantite_disponible = int(lot.quantite_disponible or 0) - int(qte)
                mvt = MouvementStock(
                    produit_id=ligne.produit_id,
                    lot_id=lot.id,
                    type_mouvement='sortie',
                    quantite=int(qte),
                    motif='Livraison Client',
                    reference_document=bl.numero,
                    utilisateur_id=current_user.id
                )
                db.session.add(mvt)

            ligne.quantite_livree = int(ligne.quantite_livree or 0) + reste
            touched_products.add(ligne.produit_id)

        for pid in touched_products:
            total = (
                db.session.query(func.coalesce(func.sum(Lot.quantite_disponible), 0))
                .filter(Lot.produit_id == pid)
                .scalar()
                or 0
            )
            stock = Stock.query.filter_by(produit_id=pid).first()
            if not stock:
                stock = Stock(produit_id=pid, quantite_disponible=0, quantite_reservee=0)
                db.session.add(stock)
            stock.quantite_disponible = int(total)
            stock.dernier_mouvement = datetime.utcnow()
            
        db.session.commit()
        flash(f'Le BL {bl.numero} a été marqué comme livré. Les sorties de stock ont été enregistrées.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la livraison: {str(e)}", "danger")
        
    return redirect(url_for('ventes.bons_livraison'))

# --- PDF Generation ---


def _ctx_pdf_vente_ht(doc, total_ht_attr="total_ht"):
    ctx = pdf_company_context()
    dp = ctx["doc_params"]
    devise = (getattr(dp, "devise_libelle", None) or "francs").strip() or "francs"
    ctx["montant_lettres"] = montant_document_lettres(doc, devise, total_ht_attr)
    ctx["format_fcfa"] = format_montant_espace
    ctx["affiche_tva"] = document_affiche_tva(doc)
    return ctx


_MOIS_FR_LONG = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def _date_lieu_fr(d, lieu: str) -> str:
    if not d:
        return ""
    m = _MOIS_FR_LONG[d.month - 1]
    m_cap = m[0].upper() + m[1:] if m else m
    return f"{(lieu or 'St Louis').strip()}, le {d.day} {m_cap} {d.year}"


@ventes_bp.route("/factures/<int:id>/imprimer")
@login_required
@permission_required("ventes", "read")
def facture_imprimer(id):
    """Aperçu navigateur + impression (window.print), style document papier."""
    avec_bl = request.args.get('avec_bl', '0').lower() in ('1', 'true', 'oui', 'yes')
    facture = (
        Facture.query.options(
            joinedload(Facture.client),
            joinedload(Facture.lignes).joinedload(LigneFacture.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    bl = BonLivraison.query.options(
        joinedload(BonLivraison.client),
        joinedload(BonLivraison.lignes).joinedload(LigneBL.produit),
        joinedload(BonLivraison.lignes).joinedload(LigneBL.lot),
    ).filter_by(facture_id=id).first()

    ctx = merge_browser_print_logo(_ctx_pdf_vente_ht(facture))
    dp = ctx["doc_params"]
    lieu = (getattr(dp, "lieu_signature", None) or "St Louis").strip()
    inclure_bl = bool(avec_bl and bl)

    return render_template(
        "ventes/facture_impression.html",
        **ctx,
        facture=facture,
        bl=bl if inclure_bl else None,
        avec_bl=inclure_bl,
        date_signature_fr=_date_lieu_fr(facture.date_emission, lieu),
        date_signature_bl_fr=_date_lieu_fr(bl.date_livraison, lieu) if bl else "",
    )


@ventes_bp.route("/bons-livraison/<int:id>/imprimer")
@login_required
@permission_required("ventes", "read")
def bl_imprimer(id):
    """Aperçu navigateur + impression BL (même modèle visuel que facture/proforma)."""
    bl = (
        BonLivraison.query.options(
            joinedload(BonLivraison.client),
            joinedload(BonLivraison.lignes).joinedload(LigneBL.produit),
            joinedload(BonLivraison.lignes).joinedload(LigneBL.lot),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    ctx = merge_browser_print_logo(pdf_company_context())
    ctx["format_fcfa"] = format_montant_espace
    dp = ctx["doc_params"]
    lieu = (getattr(dp, "lieu_signature", None) or "St Louis").strip()
    return render_template(
        "ventes/bl_impression.html",
        **ctx,
        bl=bl,
        date_signature_bl_fr=_date_lieu_fr(bl.date_livraison, lieu),
    )


@ventes_bp.route("/proformas/<int:id>/imprimer")
@login_required
@permission_required("ventes", "read")
def proforma_imprimer(id):
    """Aperçu navigateur + impression proforma (même modèle visuel que facture)."""
    proforma = (
        Proforma.query.options(
            joinedload(Proforma.client),
            joinedload(Proforma.lignes).joinedload(LigneProforma.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    ctx = merge_browser_print_logo(_ctx_pdf_vente_ht(proforma))
    dp = ctx["doc_params"]
    lieu = (getattr(dp, "lieu_signature", None) or "St Louis").strip()

    return render_template(
        "ventes/proforma_impression.html",
        **ctx,
        proforma=proforma,
        date_signature_fr=_date_lieu_fr(proforma.date_emission, lieu),
    )


@ventes_bp.route('/proformas/<int:id>/pdf')
@login_required
@permission_required('ventes', 'read')
def proforma_pdf(id):
    proforma = (
        Proforma.query.options(
            joinedload(Proforma.client),
            joinedload(Proforma.lignes).joinedload(LigneProforma.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    ctx = _ctx_pdf_vente_ht(proforma)
    ctx["proforma"] = proforma
    logo_path = get_logo_filepath()
    try:
        pdf_io = build_proforma_pdf_bytesio(
            proforma,
            ctx["doc_params"],
            ctx["montant_lettres"],
            format_montant_espace,
            logo_path,
        )
    except Exception as e:
        current_app.logger.warning("PDF proforma ReportLab → HTML : %s", e)
        try:
            html = render_template("ventes/pdf_proforma.html", **ctx)
            pdf_io = generate_pdf(html)
        except Exception as e2:
            flash(str(e2), "danger")
            return redirect(url_for("ventes.proformas"))
    return send_file(
        pdf_io,
        download_name=download_name_document(
            "Proforma",
            proforma.numero,
            proforma.client.raison_sociale if proforma.client else None,
        ),
        as_attachment=True,
        mimetype="application/pdf",
    )

@ventes_bp.route("/factures/<int:id>/pdf")
@login_required
@permission_required("ventes", "read")
def facture_pdf(id):
    """PDF ReportLab : en-tête / pied sur chaque page, zone pied 5 cm."""
    facture = (
        Facture.query.options(
            joinedload(Facture.client),
            joinedload(Facture.lignes).joinedload(LigneFacture.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    ctx = _ctx_pdf_vente_ht(facture)
    dp = ctx["doc_params"]
    lieu = (getattr(dp, "lieu_signature", None) or "St Louis").strip()
    logo_path = get_logo_filepath()
    try:
        pdf_io = build_facture_pdf_bytesio(
            facture,
            dp,
            ctx["montant_lettres"],
            format_montant_espace,
            logo_path,
            _date_lieu_fr(facture.date_emission, lieu),
        )
    except Exception as e:
        current_app.logger.exception("PDF facture ReportLab échoué : %s", e)
        flash("Impossible de générer le PDF de la facture. Réessayez ou contactez l’administrateur.", "danger")
        return redirect(url_for("ventes.facture_detail", id=id))
    return send_file(
        pdf_io,
        download_name=download_name_document(
            "Facture",
            facture.numero,
            facture.client.raison_sociale if facture.client else None,
        ),
        as_attachment=True,
        mimetype="application/pdf",
    )

@ventes_bp.route('/bons-livraison/<int:id>/pdf')
@login_required
@permission_required('ventes', 'read')
def bl_pdf(id):
    bl = (
        BonLivraison.query.options(
            joinedload(BonLivraison.client),
            joinedload(BonLivraison.lignes).joinedload(LigneBL.produit),
            joinedload(BonLivraison.lignes).joinedload(LigneBL.lot),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    ctx = pdf_company_context()
    ctx["bl"] = bl
    logo_path = get_logo_filepath()
    try:
        pdf_io = build_bl_pdf_bytesio(bl, ctx["doc_params"], logo_path)
    except Exception as e:
        current_app.logger.warning("PDF BL ReportLab → HTML : %s", e)
        try:
            html = render_template("ventes/pdf_bl.html", **ctx)
            pdf_io = generate_pdf(html)
        except Exception as e2:
            flash(str(e2), "danger")
            return redirect(url_for("ventes.bons_livraison"))
    return send_file(
        pdf_io,
        download_name=download_name_document(
            "BL",
            bl.numero,
            bl.client.raison_sociale if bl.client else None,
        ),
        as_attachment=True,
        mimetype="application/pdf",
    )
