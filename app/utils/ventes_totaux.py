"""Règles d'affichage des totaux ventes (facture, proforma)."""

from __future__ import annotations

from typing import Any


def _num_gt_zero(x: Any) -> bool:
    if x is None:
        return False
    try:
        return float(x) > 1e-9
    except (TypeError, ValueError):
        return False


def document_affiche_tva(doc: Any, lignes: list | None = None) -> bool:
    """
    True si les totaux doivent afficher HT / TVA / TTC.
    Pas de TVA affichée lorsque le montant est nul ou que tous les produits sont à 0 %.
    """
    if not _num_gt_zero(getattr(doc, "tva_montant", None)):
        return False

    ls = lignes if lignes is not None else (getattr(doc, "lignes", None) or [])
    if not ls:
        return True

    for ligne in ls:
        produit = getattr(ligne, "produit", None)
        if produit is not None and _num_gt_zero(getattr(produit, "tva", None)):
            return True
    return False


def montant_document_lettres(doc: Any, devise: str = "francs", total_ht_attr: str = "total_ht") -> str:
    """Montant en lettres : TTC si TVA affichée, sinon HT."""
    from .nombre_lettres import montant_fcfa_en_lettres

    if document_affiche_tva(doc):
        amount = getattr(doc, "total_ttc", None) or 0
    else:
        amount = getattr(doc, total_ht_attr, None) or 0
    return montant_fcfa_en_lettres(amount, devise)
