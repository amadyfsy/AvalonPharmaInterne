"""Payload photos produit (API interne / futur site public)."""
from __future__ import annotations

from flask import url_for

from ..models.produit import Produit, ProduitPhoto


def photos_galerie_triees(produit: Produit) -> list[ProduitPhoto]:
    return sorted(produit.photos_galerie or [], key=lambda p: (p.ordre, p.id))


def url_photo_produit(stored: str | None, *, external: bool = False, public_route: bool = False) -> str | None:
    if not stored:
        return None
    endpoint = 'public.photo_fichier' if public_route else 'stock.produit_photo_fichier'
    return url_for(endpoint, stored_name=stored, _external=external)


def produit_photos_payload(produit: Produit, *, external_urls: bool = False, public_route: bool = False) -> dict:
    galerie = []
    for p in photos_galerie_triees(produit):
        galerie.append(
            {
                'id': p.id,
                'fichier': p.fichier,
                'url': url_photo_produit(p.fichier, external=external_urls, public_route=public_route),
                'ordre': p.ordre,
                'legende': p.legende,
            }
        )
    return {
        'photo_principale': produit.photo_principale,
        'photo_principale_url': url_photo_produit(
            produit.photo_principale, external=external_urls, public_route=public_route
        ),
        'galerie': galerie,
    }
