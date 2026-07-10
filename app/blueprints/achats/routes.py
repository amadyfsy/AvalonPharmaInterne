from datetime import date, datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models.commande import CommandeFournisseur, LigneCommandeFournisseur
from ...models.depense import CategorieDepense, Depense
from ...models.fournisseur import Fournisseur
from ...models.produit import Lot, Produit
from ...models.stock import MouvementStock, Stock
from ...utils.approvisionnement_depenses import (
    parse_frais_json,
    sync_depenses_from_wizard_payload,
    valider_frais_justificatifs,
)
from ...utils.commande_depenses import (
    depense_liee_a_commande,
    libelle_depense_achat,
    marqueur_achat,
    notes_commande_sans_frais,
)
from ...utils.decorators import permission_required, user_has_permission
from ...utils.depense_justificatif import remove_justificatif_file, upload_depense_justificatif
from ...utils.depense_reference import prochaine_reference_depense
from ...utils.nombre_lettres import format_montant_espace
from ...utils.pdf_generator import generate_pdf
from flask_login import current_user, login_required

from flask import abort, flash, redirect, render_template, request, send_file, url_for

from . import achats_bp

COMMANDES_PAR_PAGE = 15

_STATUTS_COMMANDE = (
    'brouillon',
    'envoyee',
    'partiellement_recue',
    'recue',
    'annulee',
)


def _justificatifs_wizard_from_request():
    return {
        'transport': request.files.get('justificatif_transport'),
        'douane': request.files.get('justificatif_douane'),
        'autre': request.files.get('justificatif_autre'),
    }


def _depenses_liees_commande(commande: CommandeFournisseur):
    marker = f"%{marqueur_achat(commande.numero)}%"
    return (
        Depense.query.options(joinedload(Depense.categorie))
        .filter(Depense.libelle.ilike(marker))
        .order_by(Depense.date_depense.desc(), Depense.id.desc())
        .all()
    )


def _get_depense_liee_commande(commande_id: int, depense_id: int) -> tuple[CommandeFournisseur, Depense]:
    commande = CommandeFournisseur.query.filter_by(id=commande_id).first_or_404()
    depense = (
        Depense.query.options(joinedload(Depense.categorie))
        .filter_by(id=depense_id)
        .first_or_404()
    )
    if not depense_liee_a_commande(depense, commande.numero):
        abort(404)
    return commande, depense


def _parse_depense_commande_form(commande: CommandeFournisseur, *, justificatif_required: bool):
    try:
        cat_id = int(request.form.get('categorie_id') or 0)
    except (TypeError, ValueError):
        cat_id = 0
    categorie = CategorieDepense.query.get(cat_id)
    if not categorie:
        raise ValueError('Catégorie de dépense invalide.')

    description = (request.form.get('description') or '').strip()
    libelle_base = description or (categorie.nom or 'Dépense')
    try:
        montant_ht = float(request.form.get('montant_ht') or 0)
    except (TypeError, ValueError):
        montant_ht = 0.0
    if montant_ht <= 0:
        raise ValueError('Montant HT invalide.')

    mode = (request.form.get('mode_paiement') or 'espece').strip()
    if mode not in ('espece', 'cheque', 'virement', 'carte'):
        mode = 'espece'

    date_raw = request.form.get('date_depense')
    if date_raw:
        try:
            date_depense = datetime.strptime(date_raw, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValueError('Date de dépense invalide.') from exc
    else:
        date_depense = commande.date_commande or date.today()

    justificatif = request.files.get('justificatif')
    has_new_file = bool(justificatif and justificatif.filename)
    if justificatif_required and not has_new_file:
        raise ValueError('Justificatif obligatoire (PDF, PNG ou JPEG).')

    return {
        'categorie': categorie,
        'libelle_base': libelle_base,
        'montant_ht': montant_ht,
        'mode_paiement': mode,
        'date_depense': date_depense,
        'justificatif': justificatif if has_new_file else None,
    }


def _creer_depense_liee_commande(
    *,
    commande: CommandeFournisseur,
    categorie: CategorieDepense,
    libelle_base: str,
    montant_ht: float,
    mode_paiement: str,
    justificatif_file,
    date_depense=None,
) -> Depense:
    d = date_depense or commande.date_commande or date.today()
    reference = prochaine_reference_depense(d)
    justificatif = upload_depense_justificatif(justificatif_file, categorie.nom, reference)
    type_depense = getattr(categorie.type_depense, 'value', categorie.type_depense) or 'variable'
    dep = Depense(
        reference=reference,
        categorie_id=categorie.id,
        type_depense=type_depense,
        libelle=libelle_depense_achat(libelle_base, commande.numero),
        montant_ht=montant_ht,
        tva=0,
        montant_ttc=montant_ht,
        date_depense=d,
        mode_paiement=mode_paiement,
        fournisseur_id=commande.fournisseur_id,
        justificatif=justificatif,
        statut='en_attente',
        created_by=current_user.id,
    )
    db.session.add(dep)
    db.session.flush()
    return dep


def _creer_commande_fournisseur_from_form():
    """
    Crée une commande depuis request.form (assistant commande fournisseur / POST legacy /achats/nouvelle).
    Retourne (numero, None, warnings) en cas de succès, (None, message_erreur, []) sinon.
    """
    try:
        fournisseur_id = int(request.form.get('fournisseur_id'))
    except (TypeError, ValueError):
        return None, 'Fournisseur invalide.', []

    if not Fournisseur.query.get(fournisseur_id):
        return None, 'Fournisseur introuvable.', []

    date_str = request.form.get('date_commande')
    if not date_str:
        return None, 'Date de commande manquante.', []
    try:
        date_commande = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None, 'Date de commande invalide.', []

    date_livraison_prevue = request.form.get('date_livraison_prevue')
    if date_livraison_prevue:
        try:
            date_livraison_prevue = datetime.strptime(date_livraison_prevue, '%Y-%m-%d').date()
        except ValueError:
            date_livraison_prevue = None
    else:
        date_livraison_prevue = None

    notes = (request.form.get('notes') or '').strip()
    frais_json = (request.form.get('frais_approvisionnement') or '').strip()
    frais_data = parse_frais_json(frais_json)
    if frais_data:
        justif_err = valider_frais_justificatifs(frais_data, _justificatifs_wizard_from_request())
        if justif_err:
            return None, justif_err, []
    if frais_json:
        notes = f'{notes}\n\n--- Dépenses (wizard approvisionnement) ---\n{frais_json}'.strip()

    produit_ids = request.form.getlist('produit_id[]')
    quantites = request.form.getlist('quantite[]')
    prix_achats = request.form.getlist('prix_achat_ht[]')

    if not produit_ids or not any(str(x).strip() for x in produit_ids):
        return None, 'Veuillez ajouter au moins un produit.', []

    n = len(produit_ids)
    if len(quantites) < n or len(prix_achats) < n:
        return None, 'Données produits incomplètes (quantités / prix).', []

    annee = date_commande.year
    count = CommandeFournisseur.query.filter(
        db.extract('year', CommandeFournisseur.date_commande) == annee
    ).count()
    numero = f'CMD-{annee}-{count + 1:04d}'

    total_ht_global = 0.0
    tva_montant_global = 0.0

    try:
        commande = CommandeFournisseur(
            numero=numero,
            fournisseur_id=fournisseur_id,
            date_commande=date_commande,
            date_livraison_prevue=date_livraison_prevue,
            total_ht=0,
            tva_montant=0,
            total_ttc=0,
            statut='envoyee',
            notes=notes,
        )
        db.session.add(commande)
        db.session.flush()

        for i in range(len(produit_ids)):
            if not str(produit_ids[i]).strip():
                continue
            pid = int(produit_ids[i])
            qte = int(quantites[i])
            pa = float(prix_achats[i])

            prod = Produit.query.get(pid)
            if not prod:
                db.session.rollback()
                return None, f'Produit introuvable (id={pid}).', []

            montant_ligne_ht = pa * qte
            tva_ligne = montant_ligne_ht * (float(prod.tva) / 100)

            total_ht_global += montant_ligne_ht
            tva_montant_global += tva_ligne

            ligne = LigneCommandeFournisseur(
                commande_id=commande.id,
                produit_id=pid,
                quantite_commandee=qte,
                prix_achat_ht=pa,
                quantite_recue=0,
            )
            db.session.add(ligne)

        total_ttc = total_ht_global + tva_montant_global

        commande.total_ht = total_ht_global
        commande.tva_montant = tva_montant_global
        commande.total_ttc = total_ttc
        db.session.flush()

        uid = current_user.id if current_user.is_authenticated else None
        warnings = sync_depenses_from_wizard_payload(
            commande, frais_data, uid, _justificatifs_wizard_from_request()
        )

        db.session.commit()
        return numero, None, warnings
    except Exception as e:
        db.session.rollback()
        return None, str(e), []


def _maj_commande_fournisseur_from_form(commande):
    """
    Met à jour une commande existante (en-tête + lignes).
    Retourne None si OK, sinon un message d'erreur str.
    """
    if commande.statut in ('recue', 'annulee'):
        return 'Cette commande ne peut plus être modifiée (déjà reçue ou annulée).'

    try:
        fournisseur_id = int(request.form.get('fournisseur_id'))
    except (TypeError, ValueError):
        return 'Fournisseur invalide.'

    if not Fournisseur.query.get(fournisseur_id):
        return 'Fournisseur introuvable.'

    date_str = request.form.get('date_commande')
    if not date_str:
        return 'Date de commande manquante.'
    try:
        date_commande = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return 'Date de commande invalide.'

    date_livraison_prevue = request.form.get('date_livraison_prevue')
    if date_livraison_prevue:
        try:
            date_livraison_prevue = datetime.strptime(date_livraison_prevue, '%Y-%m-%d').date()
        except ValueError:
            date_livraison_prevue = None
    else:
        date_livraison_prevue = None

    notes = (request.form.get('notes') or '').strip()

    ligne_ids = request.form.getlist('ligne_id[]')
    produit_ids = request.form.getlist('produit_id[]')
    quantites = request.form.getlist('quantite[]')
    prix_achats = request.form.getlist('prix_achat_ht[]')

    rows = []
    for i, pid_raw in enumerate(produit_ids):
        if not str(pid_raw).strip():
            continue
        lid = 0
        if i < len(ligne_ids) and str(ligne_ids[i]).strip().isdigit():
            lid = int(ligne_ids[i])
        try:
            pid = int(pid_raw)
            qte = int(quantites[i])
            pa = float(prix_achats[i])
        except (IndexError, ValueError, TypeError):
            return 'Données de lignes invalides.'
        if qte <= 0:
            return 'Chaque quantité doit être supérieure à 0.'
        rows.append((lid, pid, qte, pa))

    if not rows:
        return 'Au moins une ligne produit est requise.'

    keep_ids = {lid for lid, _, _, _ in rows if lid > 0}

    try:
        for ligne in list(commande.lignes):
            if ligne.id not in keep_ids:
                db.session.delete(ligne)

        total_ht_global = 0.0
        tva_montant_global = 0.0

        for lid, pid, qte, pa in rows:
            prod = Produit.query.get(pid)
            if not prod:
                db.session.rollback()
                return f'Produit introuvable (id={pid}).'

            montant_ligne_ht = pa * qte
            tva_ligne = montant_ligne_ht * (float(prod.tva) / 100)
            total_ht_global += montant_ligne_ht
            tva_montant_global += tva_ligne

            if lid > 0:
                lg = LigneCommandeFournisseur.query.filter_by(
                    id=lid, commande_id=commande.id
                ).first()
                if not lg:
                    db.session.rollback()
                    return 'Ligne de commande invalide.'
                lg.produit_id = pid
                lg.quantite_commandee = qte
                lg.prix_achat_ht = pa
            else:
                db.session.add(
                    LigneCommandeFournisseur(
                        commande_id=commande.id,
                        produit_id=pid,
                        quantite_commandee=qte,
                        prix_achat_ht=pa,
                        quantite_recue=0,
                    )
                )

        commande.fournisseur_id = fournisseur_id
        commande.date_commande = date_commande
        commande.date_livraison_prevue = date_livraison_prevue
        commande.notes = notes
        commande.total_ht = total_ht_global
        commande.tva_montant = tva_montant_global
        commande.total_ttc = total_ht_global + tva_montant_global

        db.session.commit()
        return None
    except Exception as e:
        db.session.rollback()
        return str(e)


@achats_bp.route('/')
@login_required
@permission_required('achats', 'read')
def index():
    q = (request.args.get('q') or '').strip()
    statut = (request.args.get('statut') or '').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if statut and statut not in _STATUTS_COMMANDE:
        statut = ''

    query = CommandeFournisseur.query.options(joinedload(CommandeFournisseur.fournisseur))
    if q:
        pattern = f'%{q}%'
        query = query.join(Fournisseur, CommandeFournisseur.fournisseur_id == Fournisseur.id).filter(
            or_(
                CommandeFournisseur.numero.ilike(pattern),
                Fournisseur.raison_sociale.ilike(pattern),
            )
        )
    if statut:
        query = query.filter(CommandeFournisseur.statut == statut)

    pagination = (
        query.order_by(
            CommandeFournisseur.date_commande.desc(),
            CommandeFournisseur.created_at.desc(),
            CommandeFournisseur.id.desc(),
        )
        .paginate(page=page, per_page=COMMANDES_PAR_PAGE, error_out=False)
    )

    filtres_url = {}
    if q:
        filtres_url['q'] = q
    if statut:
        filtres_url['statut'] = statut

    return render_template(
        'achats/index.html',
        commandes=pagination.items,
        pagination=pagination,
        q=q,
        statut_filtre=statut,
        filtres_url=filtres_url,
        statuts_commande=_STATUTS_COMMANDE,
    )


@achats_bp.route('/approvisionnement')
@login_required
@permission_required('achats', 'read')
def approvisionnement():
    """Assistant unique : nouvelle commande fournisseur (fournisseur, produits, dépenses)."""
    fournisseurs_actifs = (
        Fournisseur.query.filter_by(est_actif=True)
        .order_by(Fournisseur.raison_sociale)
        .all()
    )
    nb_par_fournisseur = dict(
        db.session.query(
            CommandeFournisseur.fournisseur_id,
            func.count(CommandeFournisseur.id),
        )
        .group_by(CommandeFournisseur.fournisseur_id)
        .all()
    )
    fournisseurs_data = []
    for f in fournisseurs_actifs:
        detail_parts = []
        if f.telephone:
            detail_parts.append('Tél: ' + str(f.telephone))
        if f.email:
            detail_parts.append(str(f.email))
        if f.ville:
            detail_parts.append(str(f.ville))
        if f.adresse:
            detail_parts.append(str(f.adresse)[:60])
        fournisseurs_data.append(
            {
                'obj': f,
                'details': ' | '.join(detail_parts) or '—',
                'nb_commandes': int(nb_par_fournisseur.get(f.id, 0)),
            }
        )

    produits_actifs = (
        Produit.query.filter_by(est_actif=True).order_by(Produit.designation).all()
    )
    produits_data = []
    for p in produits_actifs:
        st = Stock.query.filter_by(produit_id=p.id).first()
        dispo = int(st.quantite_disponible) if st else 0
        produits_data.append(
            {
                'obj': p,
                'stock_dispo': dispo,
                'prix_achat': float(p.prix_achat_ht),
                'prix_vente': float(p.prix_vente_ht),
            }
        )

    return render_template(
        'achats/approvisionnement.html',
        fournisseurs_data=fournisseurs_data,
        produits_data=produits_data,
        depense_categories=CategorieDepense.query.order_by(CategorieDepense.nom).all(),
        today=date.today(),
    )


@achats_bp.route('/approvisionnement/commande', methods=['POST'])
@login_required
@permission_required('achats', 'create')
def approvisionnement_commande():
    """Soumission du wizard approvisionnement (même logique que nouvelle commande)."""
    try:
        numero, err, warns = _creer_commande_fournisseur_from_form()
        if err:
            flash(err, 'danger')
            return redirect(url_for('achats.approvisionnement'))
        for w in warns:
            flash(w, 'warning')
        flash(f'Commande fournisseur {numero} créée avec succès.', 'success')
        return redirect(url_for('achats.index'))
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'enregistrement de la commande: {str(e)}", 'danger')
        return redirect(url_for('achats.approvisionnement'))


@achats_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
@permission_required('achats', 'create')
def nouvelle_commande():
    """
    Ancienne URL « nouvelle commande » : fusionnée avec l’assistant approvisionnement.
    GET → redirection ; POST → même traitement que /approvisionnement/commande (compat. intégrations).
    """
    if request.method == 'POST':
        return approvisionnement_commande()
    return redirect(url_for('achats.approvisionnement'))


@achats_bp.route('/<int:id>')
@login_required
@permission_required('achats', 'read')
def detail_commande(id):
    commande = (
        CommandeFournisseur.query.options(
            joinedload(CommandeFournisseur.fournisseur),
            joinedload(CommandeFournisseur.lignes).joinedload(LigneCommandeFournisseur.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )
    lignes = sorted(commande.lignes, key=lambda x: x.id)
    depenses_liees = _depenses_liees_commande(commande)
    depenses_liees_total = float(sum(float(d.montant_ttc or 0) for d in depenses_liees))
    depense_categories = CategorieDepense.query.order_by(CategorieDepense.nom).all()
    peut_gerer_depenses = user_has_permission(current_user, 'depenses', 'saisir')
    notes_affichage = notes_commande_sans_frais(commande.notes)
    return render_template(
        'achats/commande_detail.html',
        commande=commande,
        lignes=lignes,
        depenses_liees=depenses_liees,
        depenses_liees_total=depenses_liees_total,
        depense_categories=depense_categories,
        peut_gerer_depenses=peut_gerer_depenses,
        notes_affichage=notes_affichage,
        format_fcfa=format_montant_espace,
    )


@achats_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@permission_required('achats', 'update')
def modifier_commande(id):
    commande = (
        CommandeFournisseur.query.options(
            joinedload(CommandeFournisseur.fournisseur),
            joinedload(CommandeFournisseur.lignes).joinedload(LigneCommandeFournisseur.produit),
        )
        .filter_by(id=id)
        .first_or_404()
    )

    if commande.statut in ('recue', 'annulee'):
        flash('Cette commande ne peut plus être modifiée.', 'warning')
        return redirect(url_for('achats.detail_commande', id=id))

    fournisseurs = Fournisseur.query.filter_by(est_actif=True).order_by(
        Fournisseur.raison_sociale
    ).all()
    produits = Produit.query.filter_by(est_actif=True).order_by(Produit.designation).all()

    if request.method == 'POST':
        err = _maj_commande_fournisseur_from_form(commande)
        if err:
            flash(err, 'danger')
            db.session.rollback()
            commande = (
                CommandeFournisseur.query.options(
                    joinedload(CommandeFournisseur.fournisseur),
                    joinedload(CommandeFournisseur.lignes).joinedload(
                        LigneCommandeFournisseur.produit
                    ),
                )
                .filter_by(id=id)
                .first_or_404()
            )
        else:
            flash('Commande mise à jour.', 'success')
            return redirect(url_for('achats.detail_commande', id=id))

    lignes = sorted(commande.lignes, key=lambda x: x.id)
    return render_template(
        'achats/commande_modifier.html',
        commande=commande,
        lignes=lignes,
        fournisseurs=fournisseurs,
        produits=produits,
        today=date.today(),
    )


@achats_bp.route('/<int:id>/recevoir', methods=['POST'])
@login_required
@permission_required('achats', 'update')
def recevoir_commande(id):
    c = CommandeFournisseur.query.get_or_404(id)
    if c.statut == 'recue':
        flash("Cette commande a déjà été reçue.", "warning")
        return redirect(url_for('achats.detail_commande', id=id))
        
    try:
        c.statut = 'recue'
        touched_products = set()
        
        import random
        from datetime import timedelta
        
        for ligne in c.lignes:
            reste = int(ligne.quantite_commandee or 0) - int(ligne.quantite_recue or 0)
            if reste <= 0:
                continue
            ligne.quantite_recue = int(ligne.quantite_recue or 0) + reste
            
            # Create Lot automatically
            lot_num = f"L{datetime.utcnow().strftime('%y%m%d')}-{random.randint(10,99)}"
            new_lot = Lot(
                produit_id=ligne.produit_id,
                numero_lot=lot_num,
                date_fabrication=datetime.utcnow().date(),
                date_peremption=(datetime.utcnow() + timedelta(days=365)).date(), # default 1 year
                fournisseur_id=c.fournisseur_id,
                quantite_initiale=reste,
                quantite_disponible=reste,
            )
            db.session.add(new_lot)
            db.session.flush()
            touched_products.add(ligne.produit_id)
            
            # Record the movement
            mvt = MouvementStock(
                produit_id=ligne.produit_id,
                lot_id=new_lot.id,
                type_mouvement='entree',
                quantite=reste,
                motif='Réception Commande Fournisseur',
                reference_document=c.numero,
                utilisateur_id=current_user.id
            )
            db.session.add(mvt)

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
        flash(
            f'Commande {c.numero} réceptionnée : entrées en stock enregistrées (quantités, lots, mouvements).',
            'success',
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la réception: {str(e)}", 'danger')

    return redirect(url_for('achats.detail_commande', id=id))


@achats_bp.route('/<int:id>/depenses', methods=['POST'])
@login_required
@permission_required('depenses', 'saisir')
def commande_ajouter_depense(id):
    commande = CommandeFournisseur.query.filter_by(id=id).first_or_404()
    if commande.statut == 'annulee':
        flash("Impossible d'ajouter une dépense à une commande annulée.", 'warning')
        return redirect(url_for('achats.detail_commande', id=id))

    try:
        data = _parse_depense_commande_form(commande, justificatif_required=False)
        _creer_depense_liee_commande(
            commande=commande,
            categorie=data['categorie'],
            libelle_base=data['libelle_base'],
            montant_ht=data['montant_ht'],
            mode_paiement=data['mode_paiement'],
            justificatif_file=data['justificatif'],
            date_depense=data['date_depense'],
        )
        db.session.commit()
        flash('Dépense liée enregistrée (en attente de validation).', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')

    return redirect(url_for('achats.detail_commande', id=id))


@achats_bp.route('/<int:id>/depenses/<int:depense_id>/modifier', methods=['POST'])
@login_required
@permission_required('depenses', 'saisir')
def commande_modifier_depense(id, depense_id):
    commande, depense = _get_depense_liee_commande(id, depense_id)

    if commande.statut == 'annulee':
        flash('Impossible de modifier une dépense sur une commande annulée.', 'warning')
        return redirect(url_for('achats.detail_commande', id=id))

    if depense.statut != 'en_attente':
        flash('Seules les dépenses en attente de validation peuvent être modifiées.', 'warning')
        return redirect(url_for('achats.detail_commande', id=id))

    try:
        data = _parse_depense_commande_form(
            commande,
            justificatif_required=False,
        )
        categorie = data['categorie']
        type_depense = getattr(categorie.type_depense, 'value', categorie.type_depense) or 'variable'

        depense.categorie_id = categorie.id
        depense.type_depense = type_depense
        depense.libelle = libelle_depense_achat(data['libelle_base'], commande.numero)
        depense.montant_ht = data['montant_ht']
        depense.tva = 0
        depense.montant_ttc = data['montant_ht']
        depense.date_depense = data['date_depense']
        depense.mode_paiement = data['mode_paiement']
        depense.fournisseur_id = commande.fournisseur_id

        if data['justificatif']:
            remove_justificatif_file(depense.justificatif)
            depense.justificatif = upload_depense_justificatif(
                data['justificatif'],
                categorie.nom,
                depense.reference,
            )

        db.session.commit()
        flash('Dépense liée mise à jour.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')

    return redirect(url_for('achats.detail_commande', id=id))
