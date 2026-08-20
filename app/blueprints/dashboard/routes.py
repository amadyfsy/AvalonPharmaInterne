from datetime import date, datetime

from ...extensions import db
from ...models.bon_livraison import BonLivraison
from ...models.commande import CommandeFournisseur, LigneCommandeFournisseur
from ...models.depense import Depense
from ...models.facture import Facture, LigneFacture
from ...models.produit import Lot, Produit
from ...models.stock import Stock
from dateutil.relativedelta import relativedelta
from flask_login import login_required
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload

from flask import render_template

from ...utils.nombre_lettres import format_montant_espace
from ...utils.parametres_pdf import has_cachet
from ...utils.statistiques_queries import _FACTURE_CA

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


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    first_day_this_month = today.replace(day=1)
    first_day_last_month = (first_day_this_month - relativedelta(months=1))
    
    # Chiffre d'Affaires (Current Month) — hors brouillons et annulées
    ca_current = float(
        db.session.query(func.sum(Facture.total_ttc)).filter(
            _FACTURE_CA,
            extract('month', Facture.date_emission) == today.month,
            extract('year', Facture.date_emission) == today.year
        ).scalar()
        or 0.0
    )

    # Chiffre d'Affaires (Last Month)
    ca_last = float(
        db.session.query(func.sum(Facture.total_ttc)).filter(
            _FACTURE_CA,
            extract('month', Facture.date_emission) == first_day_last_month.month,
            extract('year', Facture.date_emission) == first_day_last_month.year
        ).scalar()
        or 0.0
    )
    
    ca_variation = 0
    if ca_last > 0:
        ca_variation = ((ca_current - ca_last) / ca_last) * 100
    elif ca_current > 0:
        ca_variation = 100

    # Factures Impayées
    impayes_stats = db.session.query(
        func.count(Facture.id),
        func.sum(Facture.reste_a_payer)
    ).filter(
        Facture.statut.in_(['emise', 'partiellement_payee']),
        Facture.reste_a_payer > 0
    ).first()
    impayes_count = impayes_stats[0] or 0
    impayes_montant = impayes_stats[1] or 0.0

    # Alertes Stock
    alertes_stock = db.session.query(func.count(Stock.id)).join(Produit).filter(
        Stock.quantite_disponible <= Produit.seuil_alerte_stock,
        Produit.est_actif == True
    ).scalar() or 0

    # Alerte Péremption (< 90 jours), lots avec date renseignée uniquement
    alertes_peremption = db.session.query(func.count(Lot.id)).filter(
        Lot.date_peremption.isnot(None),
        Lot.date_peremption <= (today + relativedelta(days=90)),
        Lot.quantite_initiale > 0,  # approximation : pas de jointure stock réel par lot
    ).scalar() or 0

    # Dépenses (Current Month)
    depenses = db.session.query(
        Depense.type_depense, 
        func.sum(Depense.montant_ttc)
    ).filter(
        extract('month', Depense.date_depense) == today.month,
        extract('year', Depense.date_depense) == today.year,
        Depense.statut == 'valide'
    ).group_by(Depense.type_depense).all()
    
    depenses_fixes = sum(montant for t, montant in depenses if t == 'fixe') or 0.0
    depenses_variables = sum(montant for t, montant in depenses if t == 'variable') or 0.0
    depenses_fixes = float(depenses_fixes)
    depenses_variables = float(depenses_variables)
    depenses_total = depenses_fixes + depenses_variables

    # Dépenses mois précédent (variation)
    depenses_prev_month = float(
        db.session.query(func.sum(Depense.montant_ttc)).filter(
            extract('month', Depense.date_depense) == first_day_last_month.month,
            extract('year', Depense.date_depense) == first_day_last_month.year,
            Depense.statut == 'valide',
        ).scalar()
        or 0.0
    )
    depenses_variation = 0.0
    if depenses_prev_month > 0:
        depenses_variation = ((depenses_total - depenses_prev_month) / depenses_prev_month) * 100
    elif depenses_total > 0:
        depenses_variation = 100.0

    # Bénéfice estimé (CA mois - dépenses mois)
    benefice_net = float(ca_current) - depenses_total
    benefice_last_month = float(ca_last) - depenses_prev_month
    benefice_variation = 0.0
    if benefice_last_month != 0:
        benefice_variation = ((benefice_net - benefice_last_month) / abs(benefice_last_month)) * 100
    elif benefice_net > 0:
        benefice_variation = 100.0

    # Evolution CA (12 derniers mois)
    _mois_fr = (
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
    )

    def _ca_compact(v: float) -> str:
        """Libellé court pour les barres (ex. 1,2 M / 850 k)."""
        x = float(v or 0)
        if x >= 1_000_000:
            n = x / 1_000_000
            s = f"{n:.1f}".replace(".", ",").rstrip("0").rstrip(",")
            return f"{s} M"
        if x >= 1_000:
            n = x / 1_000
            s = f"{n:.0f}" if n >= 10 else f"{n:.1f}".replace(".", ",").rstrip("0").rstrip(",")
            return f"{s} k"
        return format_montant_espace(int(round(x))) or "0"

    ca_evolution = []
    for i in range(11, -1, -1):
        m = today - relativedelta(months=i)
        m_ca = float(
            db.session.query(func.sum(Facture.total_ttc)).filter(
                _FACTURE_CA,
                extract("month", Facture.date_emission) == m.month,
                extract("year", Facture.date_emission) == m.year,
            ).scalar()
            or 0.0
        )
        ca_evolution.append(
            {
                "month": m.month,
                "year": m.year,
                "label": _mois_fr[m.month - 1],
                "year_short": str(m.year)[2:],
                "value": m_ca,
                "value_label": _ca_compact(m_ca),
                "value_full": format_montant_espace(m_ca),
                "is_current": m.month == today.month and m.year == today.year,
            }
        )

    max_ca = max((row["value"] for row in ca_evolution), default=0.0)
    max_ca = max(max_ca, 1.0)
    for row in ca_evolution:
        row["pct"] = round((row["value"] / max_ca) * 100, 2)
        row["is_peak"] = row["value"] == max(r["value"] for r in ca_evolution) and row["value"] > 0

    ca_evolution_total = sum(row["value"] for row in ca_evolution)
    # Variation mois courant vs mois précédent
    ca_evolution_mom = 0.0
    if len(ca_evolution) >= 2:
        prev_v = ca_evolution[-2]["value"]
        cur_v = ca_evolution[-1]["value"]
        if prev_v > 0:
            ca_evolution_mom = ((cur_v - prev_v) / prev_v) * 100.0
        elif cur_v > 0:
            ca_evolution_mom = 100.0

    # Compatibilité éventuelle anciens templates
    ca_evolution_labels = [f'{r["label"]} {r["year"]}' for r in ca_evolution]
    ca_evolution_data = [r["value"] for r in ca_evolution]
    ca_evolution_pct = [r["pct"] for r in ca_evolution]
    ca_evolution_active_i = next(
        (i for i, r in enumerate(ca_evolution) if r["is_current"]),
        len(ca_evolution) - 1,
    )

    # Factures récentes
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

    # Top 5 produits (quantités vendues sur l'année en cours, factures validées)
    top_rows = (
        db.session.query(
            Produit.reference,
            Produit.designation,
            func.coalesce(func.sum(LigneFacture.quantite), 0).label('qty'),
            func.coalesce(func.sum(LigneFacture.montant_ht), 0).label('montant_ht'),
        )
        .join(LigneFacture, LigneFacture.produit_id == Produit.id)
        .join(Facture, Facture.id == LigneFacture.facture_id)
        .filter(
            _FACTURE_CA,
            extract('year', Facture.date_emission) == today.year,
        )
        .group_by(Produit.id, Produit.reference, Produit.designation)
        .order_by(func.sum(LigneFacture.quantite).desc())
        .limit(5)
        .all()
    )
    top_produits = [
        {
            'reference': r[0],
            'designation': r[1],
            'qty': int(r[2] or 0),
            'montant_ht': float(r[3] or 0),
        }
        for r in top_rows
    ]

    # Commandes fournisseur pas encore reçues (hors annulées), les plus récentes d’abord
    _cmdes_attente = (
        CommandeFournisseur.query.options(
            joinedload(CommandeFournisseur.fournisseur),
            joinedload(CommandeFournisseur.lignes).joinedload(LigneCommandeFournisseur.produit),
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
        {'commande': c, 'lignes': _lignes_resume_commande_fournisseur(c)} for c in _cmdes_attente
    ]

    pct_depenses_fixe = (depenses_fixes / depenses_total * 100) if depenses_total > 0 else 0.0
    pct_depenses_variable = (depenses_variables / depenses_total * 100) if depenses_total > 0 else 0.0

    alerts_count = int(impayes_count or 0) + int(alertes_stock or 0) + int(alertes_peremption or 0)

    return render_template(
        'dashboard/index.html',
        today=today,
        ca_current=float(ca_current),
        ca_variation=float(ca_variation),
        impayes_count=impayes_count,
        impayes_montant=float(impayes_montant),
        alertes_stock=alertes_stock,
        alertes_peremption=alertes_peremption,
        depenses_fixes=depenses_fixes,
        depenses_variables=depenses_variables,
        depenses_total=depenses_total,
        depenses_variation=float(depenses_variation),
        benefice_net=float(benefice_net),
        benefice_variation=float(benefice_variation),
        ca_evolution=ca_evolution,
        ca_evolution_total=ca_evolution_total,
        ca_evolution_mom=float(ca_evolution_mom),
        ca_evolution_labels=ca_evolution_labels,
        ca_evolution_data=ca_evolution_data,
        ca_evolution_pct=ca_evolution_pct,
        ca_evolution_active_i=ca_evolution_active_i,
        factures_recentes=factures_recentes,
        bl_par_facture=bl_par_facture,
        top_produits=top_produits,
        commandes_fournisseur_attente=commandes_fournisseur_attente,
        pct_depenses_fixe=pct_depenses_fixe,
        pct_depenses_variable=pct_depenses_variable,
        alerts_count=alerts_count,
        format_fcfa=format_montant_espace,
        has_cachet=has_cachet(),
    )

@dashboard_bp.route('/export')
@login_required
def export_mensuel():
    from ...utils.excel_generator import generate_excel

    from flask import send_file
    
    today = date.today()
    factures = Facture.query.filter(
        extract('month', Facture.date_emission) == today.month,
        extract('year', Facture.date_emission) == today.year
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
            f.statut
        ])
        
    excel_io = generate_excel(headers, data, sheet_title=f"Ventes {today.strftime('%m-%Y')}")
    filename = f"Rapport_Ventes_{today.strftime('%Y%m')}.xlsx"
    return send_file(excel_io, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
