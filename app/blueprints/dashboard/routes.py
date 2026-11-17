from datetime import date, datetime

from ...extensions import db
from ...models.bon_livraison import BonLivraison
from ...models.commande import CommandeFournisseur, LigneCommandeFournisseur
from ...models.depense import Depense
from ...models.facture import Facture
from dateutil.relativedelta import relativedelta
from flask_login import login_required
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload

from flask import render_template, request, send_file

from ...utils.nombre_lettres import format_montant_espace
from ...utils.parametres_pdf import has_cachet
from ...utils.pdf_generator import generate_pdf
from ...utils.statistiques_export import export_filename, generate_statistiques_excel
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

    # Courbe CA — 12 derniers mois (graphique barres d’origine)
    _mois_fr = (
        'janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin',
        'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.',
    )

    def _ca_compact(v: float) -> str:
        x = float(v or 0)
        if x >= 1_000_000:
            n = x / 1_000_000
            s = f'{n:.1f}'.replace('.', ',').rstrip('0').rstrip(',')
            return f'{s} M'
        if x >= 1_000:
            n = x / 1_000
            s = f'{n:.0f}' if n >= 10 else f'{n:.1f}'.replace('.', ',').rstrip('0').rstrip(',')
            return f'{s} k'
        return format_montant_espace(int(round(x))) or '0'

    ca_evolution = []
    for i in range(11, -1, -1):
        m = today - relativedelta(months=i)
        m_ca = float(
            db.session.query(func.sum(Facture.total_ttc)).filter(
                _FACTURE_CA,
                extract('month', Facture.date_emission) == m.month,
                extract('year', Facture.date_emission) == m.year,
            ).scalar()
            or 0.0
        )
        ca_evolution.append(
            {
                'month': m.month,
                'year': m.year,
                'label': _mois_fr[m.month - 1],
                'year_short': str(m.year)[2:],
                'value': m_ca,
                'value_label': _ca_compact(m_ca),
                'value_full': format_montant_espace(m_ca),
                'is_current': m.month == today.month and m.year == today.year,
            }
        )
    max_ca = max((row['value'] for row in ca_evolution), default=0.0)
    max_ca = max(max_ca, 1.0)
    peak_val = max((r['value'] for r in ca_evolution), default=0.0)
    for row in ca_evolution:
        row['pct'] = round((row['value'] / max_ca) * 100, 2)
        row['is_peak'] = row['value'] == peak_val and row['value'] > 0
    ca_evolution_total = sum(row['value'] for row in ca_evolution)
    ca_evolution_mom = 0.0
    if len(ca_evolution) >= 2:
        prev_v = ca_evolution[-2]['value']
        cur_v = ca_evolution[-1]['value']
        if prev_v > 0:
            ca_evolution_mom = ((cur_v - prev_v) / prev_v) * 100.0
        elif cur_v > 0:
            ca_evolution_mom = 100.0

    return render_template(
        'dashboard/index.html',
        today=today,
        annee=periode.annee,
        annees=annees,
        periode=periode,
        filtres_query=_filtres_query(periode),
        kpi=kpi,
        alertes=alertes,
        top_clients=top_clients,
        chart_data=chart_data,
        ca_annuel=float(ca_annuel),
        ca_annuel_variation=float(ca_annuel_variation),
        depenses_annuelles=float(depenses_annuelles),
        depenses_annuelles_variation=float(depenses_annuelles_variation),
        benefice_annuel=float(benefice_annuel),
        benefice_annuel_variation=float(benefice_annuel_variation),
        ca_evolution=ca_evolution,
        ca_evolution_total=ca_evolution_total,
        ca_evolution_mom=float(ca_evolution_mom),
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


@dashboard_bp.route('/export/excel')
@login_required
def export_excel():
    periode, _ = parse_periode_from_request(request.args)
    bundle = build_statistiques_bundle(periode)
    excel_io = generate_statistiques_excel(bundle)
    return send_file(
        excel_io,
        download_name=export_filename(periode, 'xlsx'),
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@dashboard_bp.route('/export/pdf')
@login_required
def export_pdf():
    periode, _ = parse_periode_from_request(request.args)
    bundle = build_statistiques_bundle(periode)
    html = render_template(
        'statistiques/export_pdf.html',
        periode=periode,
        kpi=bundle['kpi'],
        alertes=bundle['alertes'],
        top_clients=bundle['top_clients'],
        chart_data=bundle['chart_data'],
        format_fcfa=format_montant_espace,
        genere_le=datetime.now(),
    )
    pdf_io = generate_pdf(html)
    return send_file(
        pdf_io,
        download_name=export_filename(periode, 'pdf'),
        as_attachment=True,
        mimetype='application/pdf',
    )
