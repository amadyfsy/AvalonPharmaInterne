from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import or_

from ...extensions import db
from ...models.client import Client
from ...models.facture import Facture
from ...models.paiement_client import PaiementClient
from ...utils.decorators import permission_required
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from flask import flash, jsonify, redirect, render_template, request, url_for

from . import clients_bp
from .forms import ClientForm

MODE_PAIEMENT_LABELS = {
    "cheque": "Chèque",
    "virement": "Virement",
    "orange_money": "Orange Money",
    "wave": "Wave",
}


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


@clients_bp.route('/<int:id>/paiements')
@login_required
@permission_required('ventes', 'read')
def paiements(id):
    client = Client.query.get_or_404(id)
    paiements_list = (
        PaiementClient.query.options(joinedload(PaiementClient.facture))
        .filter_by(client_id=client.id)
        .order_by(PaiementClient.date_paiement.desc(), PaiementClient.id.desc())
        .all()
    )
    total_encaisse = _q2(sum(Decimal(p.montant or 0) for p in paiements_list))
    return render_template(
        'clients/paiements.html',
        client=client,
        paiements=paiements_list,
        total_encaisse=total_encaisse,
        mode_labels=MODE_PAIEMENT_LABELS,
    )


@clients_bp.route('/<int:id>/encaisser', methods=['POST'])
@login_required
@permission_required('ventes', 'create')
def encaisser(id):
    client = Client.query.get_or_404(id)
    try:
        montant = _q2(Decimal((request.form.get('montant') or '0').replace(',', '.')))
    except Exception:
        flash("Montant invalide.", "danger")
        return redirect(url_for('clients.detail', id=client.id))

    mode_paiement = (request.form.get('mode_paiement') or '').strip().lower()
    date_paiement = (request.form.get('date_paiement') or '').strip()
    modes_autorises = {'cheque', 'virement', 'orange_money', 'wave'}
    if mode_paiement not in modes_autorises:
        flash("Mode de paiement invalide.", "danger")
        return redirect(url_for('clients.detail', id=client.id))
    if montant <= 0:
        flash("Le montant doit être supérieur à 0.", "danger")
        return redirect(url_for('clients.detail', id=client.id))
    if not date_paiement:
        date_paiement = str(date.today())
    try:
        date_paiement_obj = datetime.strptime(date_paiement, "%Y-%m-%d").date()
    except ValueError:
        flash("Date de paiement invalide.", "danger")
        return redirect(url_for('clients.detail', id=client.id))

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
        return redirect(url_for('clients.detail', id=client.id))

    total_ouvert = _q2(sum(Decimal(f.reste_a_payer or 0) for f in factures_ouvertes))
    if montant > total_ouvert:
        flash(
            f"Montant supérieur au solde du client ({total_ouvert} FCFA).",
            "danger",
        )
        return redirect(url_for('clients.detail', id=client.id))

    allocations = []
    facture_exacte = next(
        (f for f in factures_ouvertes if _q2(Decimal(f.reste_a_payer or 0)) == montant),
        None,
    )
    if facture_exacte:
        allocations.append((facture_exacte, montant))
    else:
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

    enc_ref = _paiement_ref(date_paiement_obj.year)
    for facture, part in allocations:
        facture.montant_paye = _q2(Decimal(facture.montant_paye or 0) + part)
        facture.reste_a_payer = _q2(Decimal(facture.reste_a_payer or 0) - part)
        facture.mode_paiement = mode_paiement
        if facture.reste_a_payer <= Decimal("0.00"):
            facture.reste_a_payer = Decimal("0.00")
            facture.statut = "payee"
        else:
            facture.statut = "partiellement_payee"
        db.session.add(
            PaiementClient(
                client_id=client.id,
                facture_id=facture.id,
                reference=enc_ref,
                montant=part,
                mode_paiement=mode_paiement,
                date_paiement=date_paiement_obj,
                created_by=current_user.id,
            )
        )

    _recompute_client_solde(client.id)
    db.session.commit()

    details = ", ".join([f"{f.numero}: {part}" for f, part in allocations])
    flash(
        f"Encaissement enregistré ({montant} FCFA, {mode_paiement}, {date_paiement}). Affectation: {details}.",
        "success",
    )
    return redirect(url_for('clients.detail', id=client.id))


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
