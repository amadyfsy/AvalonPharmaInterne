"""Agrégations pour la page Statistiques."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from ..extensions import db
from ..models.client import Client
from ..models.commande import CommandeFournisseur
from ..models.depense import CategorieDepense, Depense
from ..models.facture import Facture, LigneFacture
from ..models.produit import Lot, Produit
from ..models.stock import Stock

_FACTURE_CA = Facture.statut.in_(('emise', 'partiellement_payee', 'payee'))

_MOIS_FR = (
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
)
_MOIS_FR_COURT = (
    'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
    'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc',
)

_TYPE_CLIENT_LABELS = {
    'hopital': 'Hôpitaux',
    'clinique': 'Cliniques',
    'pharmacie': 'Pharmacies',
    'grossiste': 'Grossistes',
    'autre': 'Autres',
}


@dataclass
class PeriodeStats:
    granularite: str  # annee | trimestre | mois
    annee: int
    mois: int | None
    trimestre: int | None
    debut: date
    fin: date
    label: str
    variation_label: str


def parse_periode(
    annee: int,
    granularite: str = 'annee',
    mois: int | None = None,
    trimestre: int | None = None,
) -> PeriodeStats:
    today = date.today()
    g = (granularite or 'annee').strip().lower()
    if g not in ('annee', 'trimestre', 'mois'):
        g = 'annee'

    if g == 'mois':
        m = mois or today.month
        if m < 1 or m > 12:
            m = today.month
        debut = date(annee, m, 1)
        fin = (debut + relativedelta(months=1)) - relativedelta(days=1)
        label = f'{_MOIS_FR[m - 1]} {annee}'
        variation_label = 'vs mois N-1'
        mois_val = m
        trimestre_val = None
    elif g == 'trimestre':
        t = trimestre or ((today.month - 1) // 3 + 1)
        if t < 1 or t > 4:
            t = 1
        mois_debut = (t - 1) * 3 + 1
        debut = date(annee, mois_debut, 1)
        fin = (debut + relativedelta(months=3)) - relativedelta(days=1)
        label = f'T{t} {annee}'
        variation_label = 'vs T N-1'
        mois_val = None
        trimestre_val = t
    else:
        debut = date(annee, 1, 1)
        fin = date(annee, 12, 31)
        label = str(annee)
        variation_label = 'vs N-1'
        mois_val = None
        trimestre_val = None

    if fin > today:
        fin = today
    if debut > today:
        debut = today

    return PeriodeStats(
        granularite=g,
        annee=annee,
        mois=mois_val,
        trimestre=trimestre_val,
        debut=debut,
        fin=fin,
        label=label,
        variation_label=variation_label,
    )


def _periode_comparaison(periode: PeriodeStats) -> tuple[date, date]:
    if periode.granularite == 'mois' and periode.mois:
        prev_debut = periode.debut - relativedelta(months=1)
        prev_fin = periode.debut - relativedelta(days=1)
        return prev_debut, prev_fin
    if periode.granularite == 'trimestre' and periode.trimestre:
        prev_debut = date(periode.annee - 1, (periode.trimestre - 1) * 3 + 1, 1)
        prev_fin = (prev_debut + relativedelta(months=3)) - relativedelta(days=1)
        return prev_debut, prev_fin
    prev_debut = date(periode.annee - 1, 1, 1)
    prev_fin = date(periode.annee - 1, 12, 31)
    today = date.today()
    if periode.annee == today.year:
        try:
            prev_fin = date(periode.annee - 1, today.month, today.day)
        except ValueError:
            prev_fin = date(periode.annee - 1, today.month, 28)
    return prev_debut, prev_fin


def _sum_ca_ttc(debut: date, fin: date) -> float:
    return float(
        db.session.query(func.coalesce(func.sum(Facture.total_ttc), 0))
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .scalar()
        or 0
    )


def _sum_ca_ht(debut: date, fin: date) -> float:
    return float(
        db.session.query(func.coalesce(func.sum(Facture.total_ht), 0))
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .scalar()
        or 0
    )


def _sum_achats_ttc(debut: date, fin: date) -> float:
    return float(
        db.session.query(func.coalesce(func.sum(CommandeFournisseur.total_ttc), 0))
        .filter(
            CommandeFournisseur.statut != 'annulee',
            CommandeFournisseur.date_commande >= debut,
            CommandeFournisseur.date_commande <= fin,
        )
        .scalar()
        or 0
    )


def _sum_depenses_ttc(debut: date, fin: date) -> float:
    return float(
        db.session.query(func.coalesce(func.sum(Depense.montant_ttc), 0))
        .filter(
            Depense.statut == 'valide',
            Depense.date_depense >= debut,
            Depense.date_depense <= fin,
        )
        .scalar()
        or 0
    )


def _cout_achat_vendu(debut: date, fin: date) -> float:
    return float(
        db.session.query(
            func.coalesce(func.sum(LigneFacture.quantite * Produit.prix_achat_ht), 0)
        )
        .join(Facture, Facture.id == LigneFacture.facture_id)
        .join(Produit, Produit.id == LigneFacture.produit_id)
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .scalar()
        or 0
    )


def _valeur_stock() -> float:
    return float(
        db.session.query(
            func.coalesce(func.sum(Stock.quantite_disponible * Produit.prix_achat_ht), 0)
        )
        .join(Produit, Produit.id == Stock.produit_id)
        .filter(Produit.est_actif == True)  # noqa: E712
        .scalar()
        or 0
    )


def _creances_total() -> float:
    return float(
        db.session.query(func.coalesce(func.sum(Facture.reste_a_payer), 0))
        .filter(
            Facture.statut.in_(['emise', 'partiellement_payee']),
            Facture.reste_a_payer > 0,
        )
        .scalar()
        or 0
    )


def kpi_periode(periode: PeriodeStats) -> dict:
    debut, fin = periode.debut, periode.fin
    ca_ttc = _sum_ca_ttc(debut, fin)
    ca_ht = _sum_ca_ht(debut, fin)
    achats_ttc = _sum_achats_ttc(debut, fin)
    depenses_ttc = _sum_depenses_ttc(debut, fin)
    cout_vendu = _cout_achat_vendu(debut, fin)
    marge_brute = ca_ht - cout_vendu
    benefice_net = ca_ttc - depenses_ttc

    prev_debut, prev_fin = _periode_comparaison(periode)
    ca_prev = _sum_ca_ttc(prev_debut, prev_fin)
    ca_variation = 0.0
    if ca_prev > 0:
        ca_variation = ((ca_ttc - ca_prev) / ca_prev) * 100
    elif ca_ttc > 0:
        ca_variation = 100.0

    nb_factures = (
        db.session.query(func.count(Facture.id))
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .scalar()
        or 0
    )
    nb_commandes = (
        db.session.query(func.count(CommandeFournisseur.id))
        .filter(
            CommandeFournisseur.statut != 'annulee',
            CommandeFournisseur.date_commande >= debut,
            CommandeFournisseur.date_commande <= fin,
        )
        .scalar()
        or 0
    )

    return {
        'periode_label': periode.label,
        'variation_label': periode.variation_label,
        'ca_ttc': ca_ttc,
        'ca_ht': ca_ht,
        'ca_variation': ca_variation,
        'achats_ttc': achats_ttc,
        'depenses_ttc': depenses_ttc,
        'marge_brute': marge_brute,
        'taux_marge': (marge_brute / ca_ht * 100) if ca_ht > 0 else 0.0,
        'benefice_net': benefice_net,
        'creances_total': _creances_total(),
        'valeur_stock': _valeur_stock(),
        'nb_factures': int(nb_factures),
        'nb_commandes': int(nb_commandes),
    }


def evolution_periode(periode: PeriodeStats) -> dict:
    today = date.today()
    labels: list[str] = []
    ca: list[float] = []
    achats: list[float] = []
    depenses: list[float] = []
    marge: list[float] = []

    if periode.granularite == 'mois' and periode.mois:
        debut_mois = date(periode.annee, periode.mois, 1)
        fin_mois = min(
            (debut_mois + relativedelta(months=1)) - relativedelta(days=1),
            today,
        )
        cursor = debut_mois
        sem = 1
        while cursor <= fin_mois:
            sem_fin = min(cursor + relativedelta(days=6), fin_mois)
            labels.append(f'S{sem}')
            ca.append(_sum_ca_ttc(cursor, sem_fin))
            achats.append(_sum_achats_ttc(cursor, sem_fin))
            depenses.append(_sum_depenses_ttc(cursor, sem_fin))
            ca_ht = _sum_ca_ht(cursor, sem_fin)
            marge.append(ca_ht - _cout_achat_vendu(cursor, sem_fin))
            cursor = sem_fin + relativedelta(days=1)
            sem += 1
        return {'labels': labels, 'ca': ca, 'achats': achats, 'depenses': depenses, 'marge': marge}

    if periode.granularite == 'trimestre' and periode.trimestre:
        mois_debut = (periode.trimestre - 1) * 3 + 1
        for offset in range(3):
            mois = mois_debut + offset
            if periode.annee > today.year or (
                periode.annee == today.year and mois > today.month
            ):
                labels.append(_MOIS_FR_COURT[mois - 1])
                ca.append(0.0)
                achats.append(0.0)
                depenses.append(0.0)
                marge.append(0.0)
                continue
            debut = date(periode.annee, mois, 1)
            fin = min((debut + relativedelta(months=1)) - relativedelta(days=1), today)
            labels.append(_MOIS_FR_COURT[mois - 1])
            ca.append(_sum_ca_ttc(debut, fin))
            achats.append(_sum_achats_ttc(debut, fin))
            depenses.append(_sum_depenses_ttc(debut, fin))
            ca_ht = _sum_ca_ht(debut, fin)
            marge.append(ca_ht - _cout_achat_vendu(debut, fin))
        return {'labels': labels, 'ca': ca, 'achats': achats, 'depenses': depenses, 'marge': marge}

    for mois in range(1, 13):
        if periode.annee > today.year or (
            periode.annee == today.year and mois > today.month
        ):
            labels.append(_MOIS_FR_COURT[mois - 1])
            ca.append(0.0)
            achats.append(0.0)
            depenses.append(0.0)
            marge.append(0.0)
            continue
        debut = date(periode.annee, mois, 1)
        fin = min((debut + relativedelta(months=1)) - relativedelta(days=1), today)
        labels.append(_MOIS_FR_COURT[mois - 1])
        ca.append(_sum_ca_ttc(debut, fin))
        achats.append(_sum_achats_ttc(debut, fin))
        depenses.append(_sum_depenses_ttc(debut, fin))
        ca_ht = _sum_ca_ht(debut, fin)
        marge.append(ca_ht - _cout_achat_vendu(debut, fin))

    return {'labels': labels, 'ca': ca, 'achats': achats, 'depenses': depenses, 'marge': marge}


def _bounds(periode: PeriodeStats) -> tuple[date, date]:
    return periode.debut, periode.fin


def ca_par_type_client(periode: PeriodeStats) -> dict:
    debut, fin = _bounds(periode)
    rows = (
        db.session.query(
            Client.type_client,
            func.coalesce(func.sum(Facture.total_ttc), 0).label('montant'),
        )
        .join(Facture, Facture.client_id == Client.id)
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .group_by(Client.type_client)
        .order_by(func.sum(Facture.total_ttc).desc())
        .all()
    )
    labels = []
    data = []
    for typ, montant in rows:
        labels.append(_TYPE_CLIENT_LABELS.get(str(typ), str(typ)))
        data.append(float(montant or 0))
    return {'labels': labels, 'data': data}


def top_produits(periode: PeriodeStats, limit: int = 10) -> dict:
    debut, fin = _bounds(periode)
    rows = (
        db.session.query(
            Produit.designation,
            func.coalesce(func.sum(LigneFacture.quantite), 0).label('qty'),
            func.coalesce(func.sum(LigneFacture.montant_ht), 0).label('montant'),
        )
        .join(LigneFacture, LigneFacture.produit_id == Produit.id)
        .join(Facture, Facture.id == LigneFacture.facture_id)
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .group_by(Produit.id, Produit.designation)
        .order_by(func.sum(LigneFacture.quantite).desc())
        .limit(limit)
        .all()
    )
    labels = []
    qty = []
    montants = []
    for desig, q, m in rows:
        labels.append((desig or 'Produit')[:40])
        qty.append(int(q or 0))
        montants.append(float(m or 0))
    return {'labels': labels, 'qty': qty, 'montants': montants}


def depenses_par_categorie(periode: PeriodeStats, limit: int = 8) -> dict:
    debut, fin = _bounds(periode)
    rows = (
        db.session.query(
            CategorieDepense.nom,
            func.coalesce(func.sum(Depense.montant_ttc), 0).label('montant'),
        )
        .join(CategorieDepense, CategorieDepense.id == Depense.categorie_id)
        .filter(
            Depense.statut == 'valide',
            Depense.date_depense >= debut,
            Depense.date_depense <= fin,
        )
        .group_by(CategorieDepense.id, CategorieDepense.nom)
        .order_by(func.sum(Depense.montant_ttc).desc())
        .limit(limit)
        .all()
    )
    return {'labels': [r[0] for r in rows], 'data': [float(r[1] or 0) for r in rows]}


def creances_par_anciennete() -> dict:
    today = date.today()
    buckets = [('0-30 j',), ('31-60 j',), ('61-90 j',), ('90+ j',)]
    factures = Facture.query.filter(
        Facture.statut.in_(['emise', 'partiellement_payee']),
        Facture.reste_a_payer > 0,
    ).all()
    montants = [0.0, 0.0, 0.0, 0.0]
    nbs = [0, 0, 0, 0]
    for f in factures:
        age = (today - (f.date_emission or today)).days
        reste = float(f.reste_a_payer or 0)
        idx = 0 if age <= 30 else 1 if age <= 60 else 2 if age <= 90 else 3
        montants[idx] += reste
        nbs[idx] += 1
    return {
        'labels': [b[0] for b in buckets],
        'data': montants,
        'counts': nbs,
    }


def alertes_stock() -> dict:
    today = date.today()
    sous_seuil = (
        db.session.query(func.count(Stock.id))
        .join(Produit, Produit.id == Stock.produit_id)
        .filter(
            Produit.est_actif == True,  # noqa: E712
            Stock.quantite_disponible <= Produit.seuil_alerte_stock,
        )
        .scalar()
        or 0
    )
    peremption_90 = (
        db.session.query(func.count(Lot.id))
        .filter(
            Lot.date_peremption.isnot(None),
            Lot.date_peremption <= today + relativedelta(days=90),
            Lot.quantite_disponible > 0,
        )
        .scalar()
        or 0
    )
    peremption_30 = (
        db.session.query(func.count(Lot.id))
        .filter(
            Lot.date_peremption.isnot(None),
            Lot.date_peremption <= today + relativedelta(days=30),
            Lot.quantite_disponible > 0,
        )
        .scalar()
        or 0
    )
    return {
        'sous_seuil': int(sous_seuil),
        'peremption_90': int(peremption_90),
        'peremption_30': int(peremption_30),
    }


def commandes_par_statut(periode: PeriodeStats) -> dict:
    debut, fin = _bounds(periode)
    statuts = ('envoyee', 'partiellement_recue', 'recue', 'brouillon')
    labels_map = {
        'envoyee': 'Envoyées',
        'partiellement_recue': 'Part. reçues',
        'recue': 'Reçues',
        'brouillon': 'Brouillons',
    }
    labels = []
    data = []
    for st in statuts:
        nb = (
            db.session.query(func.count(CommandeFournisseur.id))
            .filter(
                CommandeFournisseur.statut == st,
                CommandeFournisseur.date_commande >= debut,
                CommandeFournisseur.date_commande <= fin,
            )
            .scalar()
            or 0
        )
        if nb:
            labels.append(labels_map[st])
            data.append(int(nb))
    return {'labels': labels, 'data': data}


def top_clients(periode: PeriodeStats, limit: int = 8) -> list[dict]:
    debut, fin = _bounds(periode)
    rows = (
        db.session.query(
            Client.raison_sociale,
            Client.type_client,
            func.coalesce(func.sum(Facture.total_ttc), 0).label('montant'),
            func.count(Facture.id).label('nb'),
        )
        .join(Facture, Facture.client_id == Client.id)
        .filter(_FACTURE_CA, Facture.date_emission >= debut, Facture.date_emission <= fin)
        .group_by(Client.id, Client.raison_sociale, Client.type_client)
        .order_by(func.sum(Facture.total_ttc).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            'nom': r[0],
            'type': _TYPE_CLIENT_LABELS.get(str(r[1]), str(r[1])),
            'montant': float(r[2] or 0),
            'nb_factures': int(r[3] or 0),
        }
        for r in rows
    ]


def annees_disponibles() -> list[int]:
    today = date.today()
    min_facture = db.session.query(func.min(Facture.date_emission)).scalar()
    min_annee = min_facture.year if min_facture else today.year
    return list(range(today.year, min_annee - 1, -1))


def build_statistiques_bundle(periode: PeriodeStats) -> dict:
    """Données complètes pour la page et les exports."""
    kpi = kpi_periode(periode)
    evolution = evolution_periode(periode)
    return {
        'periode': periode,
        'kpi': kpi,
        'alertes': alertes_stock(),
        'top_clients': top_clients(periode),
        'chart_data': {
            'evolution': evolution,
            'ca_type_client': ca_par_type_client(periode),
            'top_produits': top_produits(periode),
            'depenses_categorie': depenses_par_categorie(periode),
            'creances': creances_par_anciennete(),
            'commandes_statut': commandes_par_statut(periode),
        },
    }


def parse_periode_from_request(args) -> tuple[PeriodeStats, list[int]]:
    today = date.today()
    annees = annees_disponibles() or [today.year]
    annee = args.get('annee', today.year, type=int)
    if annee not in annees:
        annee = annees[0]
    granularite = (args.get('granularite') or 'annee').strip().lower()
    mois = args.get('mois', type=int)
    trimestre = args.get('trimestre', type=int)
    if granularite == 'mois' and not mois:
        mois = today.month
    if granularite == 'trimestre' and not trimestre:
        trimestre = (today.month - 1) // 3 + 1
    periode = parse_periode(annee, granularite, mois, trimestre)
    return periode, annees
