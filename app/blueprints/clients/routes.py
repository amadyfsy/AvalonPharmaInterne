import os
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import func, or_

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

from flask import flash, jsonify, redirect, render_template, request, send_file, url_for

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


def recalculer_facture_apres_paiements(facture: Facture) -> None:
    """Recalcule montant_paye, reste_a_payer et statut d'une facture depuis ses paiements réels."""
    if not facture:
        return
    total_paye = (
        db.session.query(func.coalesce(func.sum(PaiementClient.montant), Decimal("0.00")))
        .filter(PaiementClient.facture_id == facture.id)
        .scalar()
    )
    total_paye = _q2(Decimal(total_paye or 0))
    facture.montant_paye = total_paye
    reste = max(Decimal("0.00"), _q2(Decimal(facture.total_ttc or 0) - total_paye))
    facture.reste_a_payer = reste
    if facture.statut != "annulee":
        if reste <= Decimal("0.00"):
            facture.statut = "payee"
        elif total_paye > Decimal("0.00"):
            facture.statut = "partiellement_payee"
        else:
            facture.statut = "emise"


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


@clients_bp.route('/paiements')
@login_required
@permission_required('ventes', 'read')
def tous_les_paiements():
    """Liste globale de tous les paiements clients avec filtres et recherche."""
    q = (request.args.get('q') or '').strip()
    mode = (request.args.get('mode') or '').strip().lower()
    client_id = request.args.get('client_id', type=int)

    query = PaiementClient.query.options(
        joinedload(PaiementClient.client),
        joinedload(PaiementClient.facture),
        joinedload(PaiementClient.createur),
    )

    if client_id:
        query = query.filter(PaiementClient.client_id == client_id)
    if mode and mode in MODES_PAIEMENT_AUTORISES:
        query = query.filter(PaiementClient.mode_paiement == mode)
    if q:
        like = f"%{q}%"
        query = query.join(Client, PaiementClient.client_id == Client.id).outerjoin(
            Facture, PaiementClient.facture_id == Facture.id
        ).filter(
            or_(
                PaiementClient.reference.ilike(like),
                Client.raison_sociale.ilike(like),
                Facture.numero.ilike(like),
            )
        )

    paiements_list = query.order_by(
        PaiementClient.date_paiement.desc(),
        PaiementClient.id.desc(),
    ).all()

    total_encaisse = _q2(sum(Decimal(p.montant or 0) for p in paiements_list))
    clients_actifs = Client.query.filter_by(est_actif=True).order_by(Client.raison_sociale).all()

    return render_template(
        'clients/tous_les_paiements.html',
        paiements=paiements_list,
        total_encaisse=total_encaisse,
        mode_labels=MODE_PAIEMENT_LABELS,
        modes_autorises=MODES_PAIEMENT_AUTORISES,
        q=q,
        mode_filtre=mode,
        client_id_filtre=client_id,
        clients=clients_actifs,
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
    factures_client = (
        Facture.query.filter_by(client_id=client.id)
        .order_by(Facture.numero.desc())
        .all()
    )
    return render_template(
        'clients/paiements.html',
        client=client,
        paiements=paiements_list,
        total_encaisse=total_encaisse,
        mode_labels=MODE_PAIEMENT_LABELS,
        modes_autorises=MODES_PAIEMENT_AUTORISES,
        factures_client=factures_client,
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

    # Si une facture cible est spécifiée, la traiter en priorité
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
                justificatif=stored_justificatif,
                created_by=current_user.id,
            )
        )

    _recompute_client_solde(client.id)
    db.session.commit()

    details = ", ".join([f"{f.numero}: {part} F" for f, part in allocations])
    has_j_label = " avec justificatif" if stored_justificatif else ""
    flash(
        f"Encaissement enregistré ({montant} FCFA, {MODE_PAIEMENT_LABELS.get(mode_paiement, mode_paiement)}, {date_paiement}{has_j_label}). Affectation: {details}.",
        "success",
    )
    return redirect(next_url)


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

    paiement.montant = montant
    paiement.mode_paiement = mode_paiement
    paiement.date_paiement = date_paiement_obj

    # Gestion suppression justificatif
    if request.form.get('supprimer_justificatif') == '1':
        remove_paiement_justificatif_file(paiement.justificatif)
        paiement.justificatif = None

    # Téléversement d'un nouveau justificatif
    justif_file = request.files.get('justificatif')
    if justif_file and justif_file.filename:
        try:
            if paiement.justificatif:
                remove_paiement_justificatif_file(paiement.justificatif)
            paiement.justificatif = upload_paiement_justificatif(justif_file, paiement.reference)
        except Exception as exc:
            flash(f"Erreur justificatif : {exc}", "danger")
            return redirect(next_url)

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

    if paiement.justificatif:
        remove_paiement_justificatif_file(paiement.justificatif)

    db.session.delete(paiement)
    db.session.flush()

    if old_facture_id:
        recalculer_facture_apres_paiements(Facture.query.get(old_facture_id))
    _recompute_client_solde(old_client_id)

    db.session.commit()
    flash(f"Paiement {ref} supprimé.", "info")
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
