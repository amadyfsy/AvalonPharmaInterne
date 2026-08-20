import datetime

from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func

from ...extensions import db
from ...models.employe import Conge, Employe
from ...models.facture import Facture
from ...models.produit import Produit
from ...models.stock import MouvementStock, Stock
from ...models.tresorerie import TresorerieOperation
from ...utils.decorators import permission_required
from ...utils.statistiques_queries import _FACTURE_CA
from . import rapports_bp


@rapports_bp.route('/')
@login_required
@permission_required('rapports', 'read')
def index():
    today = datetime.date.today()
    mois = request.args.get('mois', type=int)
    annee = request.args.get('annee', type=int) or today.year
    if mois is None:
        mois = 0  # 0 = tous les mois (année complète)
    if mois < 0 or mois > 12:
        mois = 0
    if annee < 2000 or annee > 2100:
        annee = today.year

    if mois == 0:
        start_month = datetime.date(annee, 1, 1)
        end_month = datetime.date(annee + 1, 1, 1)
    else:
        start_month = datetime.date(annee, mois, 1)
        if mois == 12:
            end_month = datetime.date(annee + 1, 1, 1)
        else:
            end_month = datetime.date(annee, mois + 1, 1)

    ca_mois = (
        db.session.query(func.coalesce(func.sum(Facture.total_ttc), 0))
        .filter(Facture.date_emission >= start_month, Facture.date_emission < end_month)
        .filter(_FACTURE_CA)
        .scalar()
        or 0
    )
    reste_a_encaisser = (
        db.session.query(func.coalesce(func.sum(Facture.reste_a_payer), 0))
        .filter(Facture.date_emission >= start_month, Facture.date_emission < end_month)
        .filter(Facture.statut.in_(['emise', 'partiellement_payee']))
        .scalar()
        or 0
    )
    factures_impayees = (
        db.session.query(func.count(Facture.id))
        .filter(Facture.date_emission >= start_month, Facture.date_emission < end_month)
        .filter(Facture.statut.in_(['emise', 'partiellement_payee']))
        .scalar()
        or 0
    )
    produits_stock_critique = (
        db.session.query(func.count(Stock.id))
        .join(Produit, Produit.id == Stock.produit_id)
        .filter(Stock.quantite_disponible <= Produit.seuil_alerte_stock)
        .scalar()
        or 0
    )
    conges_en_attente = (
        db.session.query(func.count(Conge.id))
        .filter(Conge.statut == 'en_attente', Conge.created_at >= start_month, Conge.created_at < end_month)
        .scalar()
        or 0
    )
    employes_actifs = (
        db.session.query(func.count(Employe.id))
        .filter(Employe.statut == 'actif')
        .scalar()
        or 0
    )

    top_ventes = (
        Facture.query.filter(
            Facture.date_emission >= start_month,
            Facture.date_emission < end_month,
            _FACTURE_CA,
        )
        .order_by(Facture.date_emission.desc(), Facture.created_at.desc())
        .limit(8)
        .all()
    )
    stocks_critiques = (
        Stock.query.join(Produit, Produit.id == Stock.produit_id)
        .filter(Stock.quantite_disponible <= Produit.seuil_alerte_stock)
        .order_by(Stock.quantite_disponible.asc())
        .limit(10)
        .all()
    )
    mouvements_recents = (
        MouvementStock.query.filter(MouvementStock.created_at >= start_month, MouvementStock.created_at < end_month)
        .order_by(MouvementStock.created_at.desc())
        .limit(10)
        .all()
    )
    tresorerie_recente = (
        TresorerieOperation.query.filter(
            TresorerieOperation.date_operation >= start_month,
            TresorerieOperation.date_operation < end_month,
        ).order_by(
            TresorerieOperation.date_operation.desc(),
            TresorerieOperation.created_at.desc(),
        )
        .limit(8)
        .all()
    )

    return render_template(
        'rapports/index.html',
        ca_mois=float(ca_mois),
        reste_a_encaisser=float(reste_a_encaisser),
        factures_impayees=int(factures_impayees),
        produits_stock_critique=int(produits_stock_critique),
        conges_en_attente=int(conges_en_attente),
        employes_actifs=int(employes_actifs),
        top_ventes=top_ventes,
        stocks_critiques=stocks_critiques,
        mouvements_recents=mouvements_recents,
        tresorerie_recente=tresorerie_recente,
        mois_label=(f"Toute l'année {annee}" if mois == 0 else f"{mois:02d}/{annee}"),
        selected_mois=mois,
        selected_annee=annee,
        annees_disponibles=list(range(today.year - 5, today.year + 1)),
    )
