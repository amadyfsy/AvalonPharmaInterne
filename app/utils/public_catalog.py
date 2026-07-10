"""Sérialisation catalogue pour le site public."""
from __future__ import annotations

from ..models.produit import CategorieProduit, Produit
from .produit_metier import effective_metier_code, specialites_form_grouped
from .parametres_pdf import DEFAULT_COMPANY_EMAIL, resolve_company_email


def _specialite(produit: Produit) -> str | None:
    dm = produit.donnees_metier if isinstance(produit.donnees_metier, dict) else {}
    val = (dm.get('specialite') or '').strip()
    return val or None


def produit_public_summary(produit: Produit, *, external_urls: bool = True) -> dict:
    cat = produit.categorie
    return {
        'id': produit.id,
        'reference': produit.reference,
        'designation': produit.designation,
        'description': (produit.description or '')[:300] or None,
        'categorie_id': produit.categorie_id,
        'categorie': cat.nom if cat else None,
        'code_formulaire': effective_metier_code(cat) if cat else None,
        'specialite': _specialite(produit),
        'forme': produit.forme,
        'unite': produit.unite,
        'prix_vente_ht': float(produit.prix_vente_ht or 0),
        'prix_vente_ttc': float(produit.prix_vente_ttc or 0),
        'tva': float(produit.tva or 0),
        'photos': produit_photos_payload(
            produit, external_urls=external_urls, public_route=True
        ),
    }


def produit_public_detail(produit: Produit, *, external_urls: bool = True) -> dict:
    cat = produit.categorie
    dm = produit.donnees_metier if isinstance(produit.donnees_metier, dict) else {}
    return {
        **produit_public_summary(produit, external_urls=external_urls),
        'description': produit.description,
        'donnees_metier': dm,
        'code_formulaire': effective_metier_code(cat) if cat else None,
    }


def categorie_public_payload(cat: CategorieProduit) -> dict:
    return {
        'id': cat.id,
        'nom': cat.nom,
        'description': cat.description,
        'code_formulaire': effective_metier_code(cat),
    }


def specialites_public_payload() -> list[dict]:
    return [
        {'groupe': label, 'specialites': list(lst)}
        for label, lst in specialites_form_grouped()
    ]


def entreprise_public_payload(row, *, external_urls: bool = True) -> dict:
    _ = external_urls
    return {
        'raison_sociale': (row.raison_sociale if row else '') or 'Avalon Pharma Senegal',
        'slogan': (row.slogan if row else '') or 'Serving those who care for others',
        'site_web': (row.site_web if row else '') or 'https://avalonpharmasenegal.com',
        'adresse': (row.adresse_ligne if row else '') or '',
        'telephone': (row.telephone if row else '') or '',
        'email': resolve_company_email(row),
        'rc': (row.rc if row else '') or '',
        'ninea': (row.ninea if row else '') or '',
        'pied_de_page': (row.pied_de_page if row else '') or None,
    }
