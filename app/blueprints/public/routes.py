"""API publique — catalogue produits et présentation entreprise."""
from __future__ import annotations

import os

from flask import current_app, jsonify, request, send_file
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models.parametres_documents import ParametresDocuments
from ...models.produit import CategorieProduit, Produit
from ...utils.produit_metier import specialites_allowed_from_form, specialites_list_for_category
from ...utils.produit_photos import photo_abs_path
from ...utils.public_catalog import (
    categorie_public_payload,
    entreprise_public_payload,
    produit_public_detail,
    produit_public_summary,
    specialites_public_payload,
)
from . import public_bp


def _cors_origin() -> str | None:
    origins = current_app.config.get('PUBLIC_CORS_ORIGINS') or '*'
    if origins == '*':
        return '*'
    origin = request.headers.get('Origin', '')
    allowed = [o.strip() for o in origins.split(',') if o.strip()]
    if origin in allowed:
        return origin
    return allowed[0] if len(allowed) == 1 else None


@public_bp.after_request
def add_cors_headers(response):
    origin = _cors_origin()
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@public_bp.route('/entreprise')
def entreprise():
    row = ParametresDocuments.get_singleton()
    return jsonify(entreprise_public_payload(row))


@public_bp.route('/categories')
def categories():
    rows = CategorieProduit.query.order_by(CategorieProduit.nom).all()
    return jsonify([categorie_public_payload(c) for c in rows])


@public_bp.route('/specialites')
def specialites():
    return jsonify(specialites_public_payload())


@public_bp.route('/produits')
def produits_liste():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 24, type=int), 1), 60)
    categorie_id = request.args.get('categorie_id', type=int)
    specialite_raw = (request.args.get('specialite') or '').strip()
    q = (request.args.get('q') or '').strip()

    specialites_codes = specialites_allowed_from_form()
    cat_filtre = db.session.get(CategorieProduit, categorie_id) if categorie_id else None
    spec_list_cat = (
        specialites_list_for_category(cat_filtre) if cat_filtre is not None else None
    )

    specialite = ''
    if specialite_raw in specialites_codes:
        if cat_filtre is None:
            specialite = specialite_raw
        elif spec_list_cat and specialite_raw in spec_list_cat:
            specialite = specialite_raw

    query = (
        Produit.query.options(joinedload(Produit.categorie), joinedload(Produit.photos_galerie))
        .filter(Produit.est_actif.is_(True))
        .outerjoin(CategorieProduit, Produit.categorie_id == CategorieProduit.id)
    )

    if categorie_id:
        query = query.filter(Produit.categorie_id == categorie_id)
    if specialite:
        spec_json = func.json_extract(Produit.donnees_metier, '$.specialite')
        query = query.filter(spec_json == specialite)
    if q:
        like = f'%{q}%'
        spec_json = func.json_extract(Produit.donnees_metier, '$.specialite')
        query = query.filter(
            or_(
                Produit.designation.ilike(like),
                Produit.reference.ilike(like),
                Produit.description.ilike(like),
                spec_json.ilike(like),
            )
        )

    query = query.order_by(Produit.designation.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            'items': [produit_public_summary(p) for p in pagination.items],
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
        }
    )


@public_bp.route('/produits/<int:id>')
def produit_detail(id):
    produit = (
        Produit.query.options(
            joinedload(Produit.categorie),
            joinedload(Produit.photos_galerie),
        )
        .filter_by(id=id, est_actif=True)
        .first_or_404()
    )
    return jsonify(produit_public_detail(produit))


@public_bp.route('/photos/<path:stored_name>')
def photo_fichier(stored_name):
    safe = stored_name.replace('\\', '/').lstrip('/')
    if not safe.startswith('produits/') or '..' in safe:
        return jsonify({'error': 'Image introuvable'}), 404
    path = photo_abs_path(safe)
    if not path or not os.path.isfile(path):
        return jsonify({'error': 'Image introuvable'}), 404
    return send_file(path, as_attachment=False, download_name=os.path.basename(path))
