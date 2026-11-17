from datetime import date

from ...extensions import db
from ...models.bon_livraison import BonLivraison
from ...models.commande import CommandeFournisseur, LigneCommandeFournisseur
from ...models.depense import Depense
from ...models.facture import Facture
from flask_login import login_required
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload

from flask import render_template, request, send_file

from ...utils.nombre_lettres import format_montant_espace
from ...utils.parametres_pdf import has_cachet
from ...utils.statistiques_queries import (
    _FACTURE_CA,
    build_statistiques_bundle,
    classement_produits,
    parse_periode_from_request,
)

from . import dashboard_bp


def _lignes_resume_commande_fournisseur(commande):
    """Liste {quantite, nom} pour affichage type « 2000 ProduitA(s) » sur le tableau de bord."""
    if not commande:
        return []
    lignes = sorted(commande.lignes or [], key=lambda x: x.id)
    out = []
    for ligne in lignes:
        if ligne.produit and getattr(ligne.produit, 'designation', None):
            nom = str(ligne.produit.designation).strip()
        else:
            nom = 'Produit'
        out.append(
            {
                'quantite': int(ligne.quantite_commandee),
                'nom': nom,
            }
        )
    return out


def _filtres_query(periode) -> dict:
    q = {
        'annee': periode.annee,
        'granularite': periode.granularite,
    }
    if periode.mois:
        q['mois'] = periode.mois
    if periode.trimestre:
        q['trimestre'] = periode.trimestre
    return q


def _pct_variation(current: float, previous: float) -> float:
    if previous > 0:
        return ((current - previous) / previous) * 100
    if current > 0:
        return 100.0
    return 0.0


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()

    # Bundle statistiques (mêmes données que la page Statistiques)
    periode, annees = parse_periode_from_request(request.args)
    bundle = build_statistiques_bundle(periode)
    kpi = bundle['kpi']
    alertes = bundle['alertes']
    top_clients = bundle['top_clients']
    chart_data = bundle['chart_data']

    # Synthèse annuelle calendaire (toujours année en cours)
    ca_annuel = float(
        db.session.query(func.sum(Facture.total_ttc)).filter(
            _FACTURE_CA,
            extract('year', Facture.date_emission) == today.year,
        ).scalar()
        or 0.0
    )
    ca_annuel_prev = float(
        db.session.query(func.sum(Facture.total_ttc)).filter(
            _FACTURE_CA,
            extract('year', Facture.date_emission) == today.year - 1,
        ).scalar()
        or 0.0
    )
    depenses_annuelles = float(
        db.session.query(func.sum(Depense.montant_ttc)).filter(
            extract('year', Depense.date_depense) == today.year,
            Depense.statut == 'valide',
        ).scalar()
        or 0.0
    )
    depenses_annuelles_prev = float(
        db.session.query(func.sum(Depense.montant_ttc)).filter(
            extract('year', Depense.date_depense) == today.year - 1,
            Depense.statut == 'valide',
        ).scalar()
        or 0.0
    )
    benefice_annuel = ca_annuel - depenses_annuelles
    benefice_annuel_prev = ca_annuel_prev - depenses_annuelles_prev

    ca_annuel_variation = _pct_variation(ca_annuel, ca_annuel_prev)
    depenses_annuelles_variation = _pct_variation(
        depenses_annuelles, depenses_annuelles_prev
    )
    if benefice_annuel_prev != 0:
        benefice_annuel_variation = (
            (benefice_annuel - benefice_annuel_prev) / abs(benefice_annuel_prev)
        ) * 100
    elif benefice_annuel > 0:
        benefice_annuel_variation = 100.0
    else:
        benefice_annuel_variation = 0.0

    # Widgets opérationnels
    factures_recentes = (
        Facture.query.options(joinedload(Facture.client))
        .order_by(Facture.date_emission.desc(), Facture.created_at.desc())
        .limit(5)
        .all()
    )
    bl_par_facture = {}
    if factures_recentes:
        fids = [f.id for f in factures_recentes]
        for bl_row in BonLivraison.query.filter(BonLivraison.facture_id.in_(fids)).all():
            bl_par_facture[bl_row.facture_id] = bl_row

    top_produits = classement_produits(
        date(today.year, 1, 1),
        date(today.year, 12, 31),
        limit=10,
    )

    _cmdes_attente = (
        CommandeFournisseur.query.options(
            joinedload(CommandeFournisseur.fournisseur),
            joinedload(CommandeFournisseur.lignes).joinedload(
                LigneCommandeFournisseur.produit
            ),
        )
        .filter(
            CommandeFournisseur.statut != 'recue',
            CommandeFournisseur.statut != 'annulee',
        )
        .order_by(CommandeFournisseur.created_at.desc())
        .limit(30)
        .all()
    )
    commandes_fournisseur_attente = [
        {'commande': c, 'lignes': _lignes_resume_commande_fournisseur(c)}
        for c in _cmdes_attente
    ]

    alerts_count = int(alertes.get('sous_seuil') or 0) + int(
        alertes.get('peremption_90') or 0
    )
    impayes_montant = float(kpi.get('creances_total') or 0)

    return render_template(
        'dashboard/index.html',
        today=today,
        # Stats (même contenu que /statistiques)
        annee=periode.annee,
        annees=annees,
        periode=periode,
        filtres_query=_filtres_query(periode),
        kpi=kpi,
        alertes=alertes,
        top_clients=top_clients,
        chart_data=chart_data,
        # Synthèse annuelle
        ca_annuel=float(ca_annuel),
        ca_annuel_variation=float(ca_annuel_variation),
        depenses_annuelles=float(depenses_annuelles),
        depenses_annuelles_variation=float(depenses_annuelles_variation),
        benefice_annuel=float(benefice_annuel),
        benefice_annuel_variation=float(benefice_annuel_variation),
        # Opérationnel
        factures_recentes=factures_recentes,
        bl_par_facture=bl_par_facture,
        top_produits=top_produits,
        commandes_fournisseur_attente=commandes_fournisseur_attente,
        alerts_count=alerts_count,
        impayes_montant=impayes_montant,
        format_fcfa=format_montant_espace,
        has_cachet=has_cachet(),
    )


@dashboard_bp.route('/export')
@login_required
def export_mensuel():
    from ...utils.excel_generator import generate_excel

    today = date.today()
    factures = Facture.query.filter(
        extract('month', Facture.date_emission) == today.month,
        extract('year', Facture.date_emission) == today.year,
    ).order_by(Facture.date_emission.asc()).all()

    headers = ['Numéro', 'Date', 'Client', 'Total HT', 'TVA', 'Total TTC', 'Statut']
    data = []

    for f in factures:
        data.append([
            f.numero,
            f.date_emission.strftime('%d/%m/%Y'),
            f.client.raison_sociale if f.client else 'Occasionnel',
            float(f.total_ht),
            float(f.tva_montant),
            float(f.total_ttc),
            f.statut,
        ])

    excel_io = generate_excel(headers, data, sheet_title=f"Ventes {today.strftime('%m-%Y')}")
    filename = f"Rapport_Ventes_{today.strftime('%Y%m')}.xlsx"
    return send_file(
        excel_io,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
