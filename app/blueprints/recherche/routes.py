"""Recherche globale : clients, produits, documents ventes, fournisseurs."""

from typing import Any, Dict, List, Optional

from flask import jsonify, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from ...models.bon_livraison import BonLivraison
from ...models.client import Client
from ...models.facture import Facture
from ...models.fournisseur import Fournisseur
from ...models.produit import Produit
from ...models.proforma import Proforma

from . import recherche_bp

# Limite par famille pour garder la page lisible tout en couvrant largement les correspondances.
PER_SECTION = 80


def _safe_like(q: str) -> str:
    """Échappe % et _ pour LIKE / ILIKE."""
    return q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _run_search(q_raw: Optional[str]) -> Dict[str, Any]:
    qs = (q_raw or '').strip()
    out: Dict[str, Any] = {
        'q': qs,
        'too_short': False,
        'clients': [],
        'produits': [],
        'factures': [],
        'bons_livraison': [],
        'proformas': [],
        'fournisseurs': [],
        'counts': {},
    }
    if len(qs) < 2:
        out['too_short'] = True
        return out

    like = f'%{_safe_like(qs)}%'

    clients = (
        Client.query.filter(
            or_(
                Client.raison_sociale.ilike(like),
                Client.code.ilike(like),
                Client.telephone.ilike(like),
                Client.ville.ilike(like),
                Client.email.ilike(like),
                Client.contact.ilike(like),
                Client.nif_stat.ilike(like),
            )
        )
        .order_by(Client.raison_sociale)
        .limit(PER_SECTION)
        .all()
    )

    produits = (
        Produit.query.filter(
            or_(
                Produit.designation.ilike(like),
                Produit.reference.ilike(like),
                Produit.description.ilike(like),
            )
        )
        .order_by(Produit.designation)
        .limit(PER_SECTION)
        .all()
    )

    factures = (
        Facture.query.join(Client, Facture.client_id == Client.id)
        .filter(
            or_(
                Facture.numero.ilike(like),
                Client.raison_sociale.ilike(like),
                Client.code.ilike(like),
            )
        )
        .options(joinedload(Facture.client))
        .order_by(Facture.date_emission.desc())
        .limit(PER_SECTION)
        .all()
    )

    bons = (
        BonLivraison.query.join(Client, BonLivraison.client_id == Client.id)
        .filter(
            or_(
                BonLivraison.numero.ilike(like),
                BonLivraison.adresse_livraison.ilike(like),
                Client.raison_sociale.ilike(like),
                Client.code.ilike(like),
            )
        )
        .options(joinedload(BonLivraison.client))
        .order_by(BonLivraison.date_livraison.desc())
        .limit(PER_SECTION)
        .all()
    )

    proformas = (
        Proforma.query.join(Client, Proforma.client_id == Client.id)
        .filter(
            or_(
                Proforma.numero.ilike(like),
                Client.raison_sociale.ilike(like),
                Client.code.ilike(like),
                Proforma.notes.ilike(like),
            )
        )
        .options(joinedload(Proforma.client))
        .order_by(Proforma.date_emission.desc())
        .limit(PER_SECTION)
        .all()
    )

    fournisseurs = (
        Fournisseur.query.filter(
            or_(
                Fournisseur.raison_sociale.ilike(like),
                Fournisseur.code.ilike(like),
                Fournisseur.telephone.ilike(like),
                Fournisseur.email.ilike(like),
                Fournisseur.ville.ilike(like),
                Fournisseur.contact.ilike(like),
            )
        )
        .order_by(Fournisseur.raison_sociale)
        .limit(PER_SECTION)
        .all()
    )

    out['clients'] = clients
    out['produits'] = produits
    out['factures'] = factures
    out['bons_livraison'] = bons
    out['proformas'] = proformas
    out['fournisseurs'] = fournisseurs
    out['counts'] = {
        'clients': len(clients),
        'produits': len(produits),
        'factures': len(factures),
        'bons_livraison': len(bons),
        'proformas': len(proformas),
        'fournisseurs': len(fournisseurs),
        'total': len(clients)
        + len(produits)
        + len(factures)
        + len(bons)
        + len(proformas)
        + len(fournisseurs),
    }
    out['truncated'] = (
        len(clients) >= PER_SECTION
        or len(produits) >= PER_SECTION
        or len(factures) >= PER_SECTION
        or len(bons) >= PER_SECTION
        or len(proformas) >= PER_SECTION
        or len(fournisseurs) >= PER_SECTION
    )
    return out


@recherche_bp.route('/recherche')
@login_required
def index():
    ctx = _run_search(request.args.get('q'))
    ctx['per_section'] = PER_SECTION
    return render_template('recherche/resultats.html', **ctx)


@recherche_bp.route('/api/recherche')
@login_required
def api_suggest():
    """Indices pour une future auto-complétion (JSON)."""

    ctx = _run_search(request.args.get('q'))
    if ctx['too_short']:
        return jsonify({'q': ctx['q'], 'results': [], 'too_short': True})

    results: List[Dict[str, Any]] = []

    for c in ctx['clients'][:10]:
        results.append(
            {
                'type': 'client',
                'label': c.raison_sociale,
                'detail': c.code or '',
                'url': url_for('clients.detail', id=c.id),
            }
        )
    for p in ctx['produits'][:10]:
        results.append(
            {
                'type': 'produit',
                'label': p.designation,
                'detail': p.reference,
                'url': url_for('stock.detail_produit', id=p.id),
            }
        )
    for f in ctx['factures'][:8]:
        results.append(
            {
                'type': 'facture',
                'label': f.numero,
                'detail': f.client.raison_sociale if f.client else '',
                'url': url_for('ventes.facture_detail', id=f.id),
            }
        )

    return jsonify({'q': ctx['q'], 'results': results[:25], 'counts': ctx['counts']})
