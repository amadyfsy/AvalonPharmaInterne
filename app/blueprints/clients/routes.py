import os
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import extract, func, or_

from ...extensions import db
from ...models.client import Client
from ...models.facture import Facture
from ...models.paiement_client import PaiementClient
from ...utils.decorators import permission_required
from ...utils.paiement_justificatif import (
    allowed_paiement_justificatif,
    paiement_justificatif_abs_path,
    remove_paiement_justificatif_file,
    upload_paiement_justificatif,
)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from . import clients_bp
from .forms import ClientForm

MODE_PAIEMENT_LABELS = {
    "espece": "Espèces",
    "cheque": "Chèque",
    "virement": "Virement",
    "orange_money": "Orange Money",
    "wave": "Wave",
    "carte": "Carte Bancaire",
}
MODES_PAIEMENT_AUTORISES = set(MODE_PAIEMENT_LABELS.keys())
PAIEMENTS_PAR_PAGE = 25
_MOIS_FILTRE_PAIEMENTS = (
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


def recalculer_facture_apres_paiements(facture: Facture) -> None:
    """Recalcule montant payé, avoirs et reste à payer d'une facture."""
    if not facture or facture.statut == "annulee":
        return
    from ...utils.avoir_service import ajuster_solde_facture

    ajuster_solde_facture(facture)


def _grouper_encaissements(lignes) -> list:
    """Une ligne par encaissement (référence), montant = somme réellement encaissée."""
    groupes: dict[str, dict] = {}
    ordre: list[str] = []
    for p in lignes:
        ref = p.reference
        g = groupes.get(ref)
        if g is None:
            g = {
                "reference": ref,
                "date_paiement": p.date_paiement,
                "client": getattr(p, "client", None),
                "client_id": p.client_id,
                "mode_paiement": p.mode_paiement,
                "montant": Decimal("0.00"),
                "justificatif": p.justificatif,
                "facture_ids": set(),
            }
            groupes[ref] = g
            ordre.append(ref)
        g["montant"] = _q2(g["montant"] + Decimal(p.montant or 0))
        if p.date_paiement and (g["date_paiement"] is None or p.date_paiement < g["date_paiement"]):
            g["date_paiement"] = p.date_paiement
        if p.justificatif and not g["justificatif"]:
            g["justificatif"] = p.justificatif
        if p.facture_id:
            g["facture_ids"].add(p.facture_id)
    out = []
    for ref in ordre:
        g = groupes[ref]
        out.append(
            SimpleNamespace(
                reference=g["reference"],
                date_paiement=g["date_paiement"],
                client=g["client"],
                client_id=g["client_id"],
                mode_paiement=g["mode_paiement"],
                montant=g["montant"],
                justificatif=g["justificatif"],
                nb_factures=len(g["facture_ids"]),
            )
        )
    return out


def _paiement_ref(year: int) -> str:
    prefix = f"ENC-{year}-"
    rows = (
        db.session.query(PaiementClient.reference)
        .filter(PaiementClient.reference.like(f"{prefix}%"))
        .all()
    )
    max_seq = 0
    for (ref,) in rows:
        if not ref or not ref.startswith(prefix):
            continue
        try:
            max_seq = max(max_seq, int(ref[len(prefix) :]))
        except ValueError:
            continue
    return f"{prefix}{max_seq + 1:04d}"


def _generate_quick_client_code() -> str:
    """Code interne unique pour saisie rapide (ex. RAP-00042)."""
    i = Client.query.count() + 1
    while i < 999999:
        code = f'RAP-{i:05d}'
        if not Client.query.filter_by(code=code).first():
            return code
        i += 1
    return f'RAP-X{Client.query.count() + 1}'


def _clients_search_query(q: Optional[str]):
    query = Client.query
    qs = (q or '').strip()
    if qs:
        like = f'%{qs}%'
        query = query.filter(
            or_(
                Client.raison_sociale.ilike(like),
                Client.code.ilike(like),
                Client.contact.ilike(like),
                Client.telephone.ilike(like),
                Client.ville.ilike(like),
                Client.email.ilike(like),
                Client.adresse.ilike(like),
            )
        )
    return query.order_by(Client.raison_sociale)


def _client_picker_dict(client: Client) -> dict:
    return {
        'id': client.id,
        'raison_sociale': client.raison_sociale or '',
        'code': client.code or '',
        'contact': client.contact or '',
        'telephone': client.telephone or '',
        'ville': client.ville or '',
        'email': client.email or '',
        'adresse': client.adresse or '',
    }


@clients_bp.route('/')
@login_required
@permission_required('ventes', 'read')
def index():
    q = request.args.get('q', '') or ''
    clients = _clients_search_query(q).all()
    total_actifs = Client.query.filter_by(est_actif=True).count()
    return render_template(
        'clients/index.html',
        clients=clients,
        q=q,
        total_actifs=total_actifs,
    )


def _q2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _recompute_client_solde(client_id: int) -> None:
    factures_ouvertes = Facture.query.filter(
        Facture.client_id == client_id,
        Facture.statut.in_(["emise", "partiellement_payee"]),
    ).all()
    total = sum(Decimal(f.reste_a_payer or 0) for f in factures_ouvertes)
    client = Client.query.get(client_id)
    if client:
        client.solde_encours = _q2(total)


@clients_bp.route('/<int:id>')
@login_required
@permission_required('ventes', 'read')
def detail(id):
    client = Client.query.get_or_404(id)
    factures = (
        Facture.query.filter_by(client_id=client.id)
        .order_by(Facture.date_emission.desc(), Facture.created_at.desc())
        .limit(20)
        .all()
    )
    factures_impayees = (
        Facture.query.filter(
            Facture.client_id == client.id,
            Facture.statut.in_(["emise", "partiellement_payee"]),
            Facture.reste_a_payer > 0,
        )
        .order_by(Facture.date_emission.asc(), Facture.created_at.asc())
        .all()
    )
    solde_impaye = _q2(sum(Decimal(f.reste_a_payer or 0) for f in factures_impayees))
    return render_template(
        'clients/detail.html',
        client=client,
        factures=factures,
        factures_impayees=factures_impayees,
        solde_impaye=solde_impaye,
        today=date.today(),
    )


def _parse_date_arg(name: str) -> Optional[date]:
    raw = (request.args.get(name) or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


@clients_bp.route('/paiements')
@login_required
@permission_required('ventes', 'read')
def tous_les_paiements():
    """Page dédiée : historique de tous les paiements, avec filtres."""
    q = (request.args.get('q') or '').strip()
    mode = (request.args.get('mode') or '').strip().lower()
    client_id = request.args.get('client_id', type=int)
    annee = request.args.get('annee', type=int)
    mois = request.args.get('mois', type=int)
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if mois is not None and (mois < 1 or mois > 12):
        mois = None
    if mode and mode not in MODES_PAIEMENT_AUTORISES:
        mode = ''

    date_filtre = _parse_date_arg('date')
    date_debut = _parse_date_arg('date_debut')
    date_fin = _parse_date_arg('date_fin')
    if date_debut and date_fin and date_debut > date_fin:
        date_debut, date_fin = date_fin, date_debut

    annees_dispo = [
        int(y)
        for (y,) in db.session.query(extract('year', PaiementClient.date_paiement))
        .filter(PaiementClient.date_paiement.isnot(None))
        .distinct()
        .order_by(extract('year', PaiementClient.date_paiement).desc())
        .all()
        if y is not None
    ]
    if annee and annee not in annees_dispo:
        annee = None

    query = PaiementClient.query

    if client_id:
        query = query.filter(PaiementClient.client_id == client_id)
    if mode:
        query = query.filter(PaiementClient.mode_paiement == mode)

    # Une date précise prime sur le mois/année ; sinon période, mois et/ou année.
    if date_filtre:
        query = query.filter(PaiementClient.date_paiement == date_filtre)
    else:
        if date_debut:
            query = query.filter(PaiementClient.date_paiement >= date_debut)
        if date_fin:
            query = query.filter(PaiementClient.date_paiement <= date_fin)
        if annee:
            query = query.filter(extract('year', PaiementClient.date_paiement) == annee)
        if mois:
            query = query.filter(extract('month', PaiementClient.date_paiement) == mois)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                PaiementClient.reference.ilike(like),
                PaiementClient.client.has(Client.raison_sociale.ilike(like)),
                PaiementClient.facture.has(Facture.numero.ilike(like)),
            )
        )

    totaux = (
        query.enable_eagerloads(False)
        .order_by(None)
        .with_entities(
            func.count(func.distinct(PaiementClient.reference)),
            func.coalesce(func.sum(PaiementClient.montant), 0),
            func.count(func.distinct(PaiementClient.client_id)),
        )
        .first()
    )
    nb_paiements = int(totaux[0] or 0)
    total_encaisse = _q2(Decimal(totaux[1] or 0))
    nb_clients = int(totaux[2] or 0)

    grouped = (
        query.with_entities(
            PaiementClient.reference.label("reference"),
            func.min(PaiementClient.date_paiement).label("date_paiement"),
            func.min(PaiementClient.client_id).label("client_id"),
            func.min(PaiementClient.mode_paiement).label("mode_paiement"),
            func.coalesce(func.sum(PaiementClient.montant), 0).label("montant"),
            func.max(PaiementClient.justificatif).label("justificatif"),
            func.count(func.distinct(PaiementClient.facture_id)).label("nb_factures"),
        )
        .group_by(PaiementClient.reference)
        .order_by(
            func.min(PaiementClient.date_paiement).desc(),
            PaiementClient.reference.desc(),
        )
    )
    pagination = grouped.paginate(page=page, per_page=PAIEMENTS_PAR_PAGE, error_out=False)
    client_ids = {row.client_id for row in pagination.items if row.client_id}
    clients_map = (
        {c.id: c for c in Client.query.filter(Client.id.in_(client_ids)).all()}
        if client_ids
        else {}
    )
    paiements_page = [
        SimpleNamespace(
            reference=row.reference,
            date_paiement=row.date_paiement,
            client=clients_map.get(row.client_id),
            mode_paiement=row.mode_paiement,
            montant=row.montant,
            justificatif=row.justificatif,
            nb_factures=int(row.nb_factures or 0),
        )
        for row in pagination.items
    ]

    clients_filtre = (
        Client.query.join(PaiementClient, PaiementClient.client_id == Client.id)
        .distinct()
        .order_by(Client.raison_sociale)
        .all()
    )

    filtres_url = {}
    if q:
        filtres_url['q'] = q
    if mode:
        filtres_url['mode'] = mode
    if client_id:
        filtres_url['client_id'] = client_id
    if date_filtre:
        filtres_url['date'] = date_filtre.isoformat()
    if date_debut and not date_filtre:
        filtres_url['date_debut'] = date_debut.isoformat()
    if date_fin and not date_filtre:
        filtres_url['date_fin'] = date_fin.isoformat()
    if annee and not date_filtre:
        filtres_url['annee'] = annee
    if mois and not date_filtre:
        filtres_url['mois'] = mois

    has_filtres = bool(
        q or mode or client_id or date_filtre or date_debut or date_fin or annee or mois
    )

    return render_template(
        'clients/tous_les_paiements.html',
        paiements=paiements_page,
        pagination=pagination,
        total_encaisse=total_encaisse,
        nb_paiements=nb_paiements,
        nb_clients=nb_clients,
        mode_labels=MODE_PAIEMENT_LABELS,
        modes_autorises=MODES_PAIEMENT_AUTORISES,
        q=q,
        mode_filtre=mode,
        client_id_filtre=client_id,
        date_filtre=date_filtre,
        date_debut=date_debut,
        date_fin=date_fin,
        annee_filtre=annee,
        mois_filtre=mois,
        annees_dispo=annees_dispo,
        mois_dispo=_MOIS_FILTRE_PAIEMENTS,
        clients=clients_filtre,
        filtres_url=filtres_url,
        has_filtres=has_filtres,
        today=date.today(),
    )


@clients_bp.route('/<int:id>/paiements')
@login_required
@permission_required('ventes', 'read')
def paiements(id):
    client = Client.query.get_or_404(id)
    paiements_list = (
        PaiementClient.query.options(
            joinedload(PaiementClient.facture),
            joinedload(PaiementClient.client),
        )
        .filter_by(client_id=client.id)
        .order_by(PaiementClient.date_paiement.desc(), PaiementClient.id.desc())
        .all()
    )
    total_encaisse = _q2(sum(Decimal(p.montant or 0) for p in paiements_list))
    encaissements = _grouper_encaissements(paiements_list)
    return render_template(
        'clients/paiements.html',
        client=client,
        paiements=encaissements,
        total_encaisse=total_encaisse,
        mode_labels=MODE_PAIEMENT_LABELS,
        today=date.today(),
    )


@clients_bp.route('/<int:id>/encaisser', methods=['POST'])
@login_required
@permission_required('ventes', 'create')
def encaisser(id):
    client = Client.query.get_or_404(id)
    redir_default = url_for('clients.detail', id=client.id)
    target_facture_id = request.form.get('facture_id', type=int)
    is_source_facture = request.form.get('source') == 'facture'
    if is_source_facture and target_facture_id:
        redir_default = url_for('ventes.facture_detail', id=target_facture_id)
    next_url = request.form.get('next') or redir_default

    try:
        montant = _q2(Decimal((request.form.get('montant') or '0').replace(',', '.')))
    except Exception:
        flash("Montant invalide.", "danger")
        return redirect(next_url)

    mode_paiement = (request.form.get('mode_paiement') or '').strip().lower()
    date_paiement = (request.form.get('date_paiement') or '').strip()
    if mode_paiement not in MODES_PAIEMENT_AUTORISES:
        flash("Mode de paiement invalide.", "danger")
        return redirect(next_url)
    if montant <= 0:
        flash("Le montant doit être supérieur à 0.", "danger")
        return redirect(next_url)
    if not date_paiement:
        date_paiement = str(date.today())
    try:
        date_paiement_obj = datetime.strptime(date_paiement, "%Y-%m-%d").date()
    except ValueError:
        flash("Date de paiement invalide.", "danger")
        return redirect(next_url)

    factures_ouvertes = (
        Facture.query.filter(
            Facture.client_id == client.id,
            Facture.statut.in_(["emise", "partiellement_payee"]),
            Facture.reste_a_payer > 0,
        )
        .order_by(Facture.date_emission.asc(), Facture.created_at.asc())
        .all()
    )
    if not factures_ouvertes:
        flash("Aucune facture impayée pour ce client.", "warning")
        return redirect(next_url)

    # Facture ciblée d'abord, sinon les plus anciennes. Le montant est réparti
    # dans cet ordre, sans sauter vers une autre facture au solde identique.
    if target_facture_id:
        tf = next((f for f in factures_ouvertes if f.id == target_facture_id), None)
        if tf:
            factures_ouvertes = [tf] + [f for f in factures_ouvertes if f.id != target_facture_id]

    total_ouvert = _q2(sum(Decimal(f.reste_a_payer or 0) for f in factures_ouvertes))
    if montant > total_ouvert:
        flash(
            f"Montant supérieur au solde impayé disponible ({total_ouvert} FCFA).",
            "danger",
        )
        return redirect(next_url)

    allocations = []
    restant = montant
    for f in factures_ouvertes:
        if restant <= 0:
            break
        reste_facture = _q2(Decimal(f.reste_a_payer or 0))
        if reste_facture <= 0:
            continue
        part = min(reste_facture, restant)
        allocations.append((f, part))
        restant = _q2(restant - part)
    if restant > Decimal("0.00") or not allocations:
        flash("Impossible d'affecter tout le montant aux factures ouvertes.", "danger")
        return redirect(next_url)

    enc_ref = _paiement_ref(date_paiement_obj.year)

    # Téléversement justificatif
    stored_justificatif = None
    justif_file = request.files.get('justificatif')
    if justif_file and justif_file.filename:
        try:
            stored_justificatif = upload_paiement_justificatif(justif_file, enc_ref)
        except Exception as exc:
            flash(f"Erreur justificatif : {exc}", "danger")
            return redirect(next_url)

    for facture, part in allocations:
        db.session.add(
            PaiementClient(
                client_id=client.id,
                facture_id=facture.id,
                reference=enc_ref,
                montant=part,
                mode_paiement=mode_paiement,
                date_paiement=date_paiement_obj,
                justificatif=stored_justificatif,
                created_by=current_user.id,
            )
        )
    db.session.flush()
    for facture, _part in allocations:
        facture.mode_paiement = mode_paiement
        recalculer_facture_apres_paiements(facture)

    _recompute_client_solde(client.id)
    db.session.commit()

    details = ", ".join([f"{f.numero}: {part} F" for f, part in allocations])
    has_j_label = " avec justificatif" if stored_justificatif else ""
    flash(
        f"Encaissement enregistré ({montant} FCFA, {MODE_PAIEMENT_LABELS.get(mode_paiement, mode_paiement)}, {date_paiement}{has_j_label}). Affectation: {details}.",
        "success",
    )
    return redirect(next_url)


@clients_bp.route('/paiements/encaissement/<reference>')
@login_required
@permission_required('ventes', 'read')
def paiement_detail(reference):
    lignes = (
        PaiementClient.query.options(
            joinedload(PaiementClient.client),
            joinedload(PaiementClient.facture),
            joinedload(PaiementClient.createur),
        )
        .filter(PaiementClient.reference == reference)
        .order_by(PaiementClient.id.asc())
        .all()
    )
    if not lignes:
        abort(404)
    entete = lignes[0]
    montant_total = _q2(sum(Decimal(p.montant or 0) for p in lignes))
    justificatif = next((p.justificatif for p in lignes if p.justificatif), None)
    factures_client = (
        Facture.query.filter_by(client_id=entete.client_id)
        .order_by(Facture.numero.desc())
        .all()
    )
    return render_template(
        'clients/paiement_detail.html',
        reference=reference,
        lignes=lignes,
        entete=entete,
        montant_total=montant_total,
        justificatif=justificatif,
        mode_labels=MODE_PAIEMENT_LABELS,
        factures_client=factures_client,
        today=date.today(),
    )


@clients_bp.route('/paiements/<int:id>/modifier', methods=['POST'])
@login_required
@permission_required('ventes', 'update')
def modifier_paiement(id):
    paiement = PaiementClient.query.get_or_404(id)
    old_facture_id = paiement.facture_id
    old_client_id = paiement.client_id
    next_url = request.form.get('next') or request.referrer or url_for('clients.paiements', id=old_client_id)

    try:
        montant = _q2(Decimal((request.form.get('montant') or '0').replace(',', '.')))
    except Exception:
        flash("Montant invalide.", "danger")
        return redirect(next_url)

    if montant <= 0:
        flash("Le montant doit être supérieur à 0.", "danger")
        return redirect(next_url)

    mode_paiement = (request.form.get('mode_paiement') or '').strip().lower()
    if mode_paiement not in MODES_PAIEMENT_AUTORISES:
        flash("Mode de paiement invalide.", "danger")
        return redirect(next_url)

    date_paiement = (request.form.get('date_paiement') or '').strip()
    try:
        date_paiement_obj = datetime.strptime(date_paiement, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        flash("Date de paiement invalide.", "danger")
        return redirect(next_url)

    new_facture_id = request.form.get('facture_id', type=int)
    if new_facture_id:
        facture_candidate = Facture.query.filter_by(id=new_facture_id, client_id=paiement.client_id).first()
        if not facture_candidate:
            flash("Facture sélectionnée invalide pour ce client.", "danger")
            return redirect(next_url)
        paiement.facture_id = facture_candidate.id
    elif 'facture_id' in request.form and not new_facture_id:
        paiement.facture_id = None

    meme_encaissement = PaiementClient.query.filter_by(reference=paiement.reference).all()
    if paiement not in meme_encaissement:
        meme_encaissement.append(paiement)

    paiement.montant = montant
    for ligne in meme_encaissement:
        ligne.mode_paiement = mode_paiement
        ligne.date_paiement = date_paiement_obj

    if paiement.facture_id:
        facture_cible = Facture.query.get(paiement.facture_id)
        if facture_cible:
            autres = (
                db.session.query(func.coalesce(func.sum(PaiementClient.montant), 0))
                .filter(
                    PaiementClient.facture_id == facture_cible.id,
                    PaiementClient.id != paiement.id,
                )
                .scalar()
            )
            if _q2(Decimal(autres or 0) + montant) > _q2(Decimal(facture_cible.total_ttc or 0)):
                flash(
                    f"Ce montant dépasse le total de la facture {facture_cible.numero}.",
                    "danger",
                )
                db.session.rollback()
                return redirect(next_url)

    # Un encaissement partage un seul justificatif, même s'il couvre plusieurs factures.
    if request.form.get('supprimer_justificatif') == '1':
        ancien = paiement.justificatif
        if ancien:
            for ligne in meme_encaissement:
                if ligne.justificatif == ancien:
                    ligne.justificatif = None
            remove_paiement_justificatif_file(ancien)

    justif_file = request.files.get('justificatif')
    if justif_file and justif_file.filename:
        try:
            nouveau = upload_paiement_justificatif(justif_file, paiement.reference)
        except Exception as exc:
            flash(f"Erreur justificatif : {exc}", "danger")
            db.session.rollback()
            return redirect(next_url)
        anciens = {ligne.justificatif for ligne in meme_encaissement if ligne.justificatif}
        for ligne in meme_encaissement:
            ligne.justificatif = nouveau
        for ancien in anciens:
            if ancien != nouveau:
                remove_paiement_justificatif_file(ancien)

    db.session.flush()

    if old_facture_id:
        recalculer_facture_apres_paiements(Facture.query.get(old_facture_id))
    if paiement.facture_id and paiement.facture_id != old_facture_id:
        recalculer_facture_apres_paiements(Facture.query.get(paiement.facture_id))

    _recompute_client_solde(old_client_id)
    if paiement.client_id != old_client_id:
        _recompute_client_solde(paiement.client_id)

    db.session.commit()
    flash(f"Paiement {paiement.reference} modifié avec succès.", "success")
    return redirect(next_url)


@clients_bp.route('/paiements/<int:id>/supprimer', methods=['POST'])
@login_required
@permission_required('ventes', 'update')
def supprimer_paiement(id):
    paiement = PaiementClient.query.get_or_404(id)
    old_facture_id = paiement.facture_id
    old_client_id = paiement.client_id
    ref = paiement.reference
    next_url = request.form.get('next') or request.referrer or url_for('clients.paiements', id=old_client_id)

    partage_justificatif = False
    if paiement.justificatif:
        partage_justificatif = (
            PaiementClient.query.filter(
                PaiementClient.id != paiement.id,
                PaiementClient.justificatif == paiement.justificatif,
            ).count()
            > 0
        )
        if not partage_justificatif:
            remove_paiement_justificatif_file(paiement.justificatif)

    db.session.delete(paiement)
    db.session.flush()

    if old_facture_id:
        recalculer_facture_apres_paiements(Facture.query.get(old_facture_id))
    _recompute_client_solde(old_client_id)

    db.session.commit()
    reste = PaiementClient.query.filter_by(reference=ref).count()
    detail_url = url_for('clients.paiement_detail', reference=ref)
    if reste == 0 and next_url == detail_url:
        next_url = url_for('clients.tous_les_paiements')
    flash(
        f"Paiement {ref} supprimé." if reste == 0 else f"Affectation du paiement {ref} supprimée.",
        "info",
    )
    return redirect(next_url)


@clients_bp.route('/paiements/justificatif/<path:stored_name>')
@login_required
@permission_required('ventes', 'read')
def paiement_justificatif_fichier(stored_name):
    """Téléchargement / affichage d'un justificatif de paiement."""
    safe = stored_name.replace('\\', '/').lstrip('/')
    if not safe.startswith('paiements/') or '..' in safe:
        flash('Fichier introuvable.', 'danger')
        return redirect(request.referrer or url_for('clients.index'))
    path = paiement_justificatif_abs_path(safe)
    if not path or not os.path.isfile(path):
        flash('Justificatif introuvable.', 'danger')
        return redirect(request.referrer or url_for('clients.index'))
    return send_file(path, as_attachment=False, download_name=os.path.basename(path))


@clients_bp.route('/api/recherche')
@login_required
@permission_required('ventes', 'read')
def api_clients_recherche():
    """Recherche JSON pour le sélecteur client (ventes, factures, BL)."""
    cid = request.args.get('id', type=int)
    if cid:
        client = Client.query.get(cid)
        if not client:
            return jsonify(ok=True, clients=[])
        return jsonify(ok=True, clients=[_client_picker_dict(client)])

    q = (request.args.get('q') or '').strip()
    limit = min(max(request.args.get('limit', 15, type=int) or 15, 1), 50)
    query = _clients_search_query(q).filter(Client.est_actif == True)  # noqa: E712
    clients = query.limit(limit).all()
    return jsonify(ok=True, clients=[_client_picker_dict(c) for c in clients])


@clients_bp.route('/api/rapide', methods=['POST'])
@login_required
@permission_required('ventes', 'create')
def api_client_rapide():
    """Création JSON minimale : nom de la structure uniquement (ventes / caisse)."""
    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Requête JSON attendue.'}), 400
    payload = request.get_json(silent=True) or {}
    nom = (payload.get('raison_sociale') or '').strip()
    if len(nom) < 2:
        return jsonify(
            {
                'ok': False,
                'error': 'Indiquez le nom de la structure (au moins 2 caractères).',
            }
        ), 400
    try:
        client = Client(
            code=_generate_quick_client_code(),
            raison_sociale=nom[:150],
            type_client='autre',
            est_actif=True,
        )
        db.session.add(client)
        db.session.commit()
        return jsonify(
            {
                'ok': True,
                'id': client.id,
                'raison_sociale': client.raison_sociale,
                'code': client.code,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

@clients_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@permission_required('ventes', 'create')
def nouveau():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            code=form.code.data,
            raison_sociale=form.raison_sociale.data,
            type_client=form.type_client.data,
            contact=form.contact.data,
            telephone=form.telephone.data,
            email=form.email.data,
            adresse=form.adresse.data,
            ville=form.ville.data,
            nif_stat=form.nif_stat.data,
            plafond_credit=form.plafond_credit.data,
            remise_habituelle=form.remise_habituelle.data,
            est_actif=form.est_actif.data
        )
        db.session.add(client)
        db.session.commit()
        flash('Client ajouté avec succès.', 'success')
        return redirect(url_for('clients.index'))
    return render_template('clients/form.html', form=form, title="Nouveau Client")


@clients_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@permission_required('ventes', 'create')
def modifier(id):
    client = Client.query.get_or_404(id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        flash('Informations client mises à jour.', 'success')
        return redirect(url_for('clients.detail', id=client.id))
    return render_template(
        'clients/form.html',
        form=form,
        title=f"Modifier {client.raison_sociale}",
        client=client,
    )
