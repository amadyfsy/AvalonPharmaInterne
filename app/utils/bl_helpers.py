"""Helpers bon de livraison — quantités alignées sur la facture."""


def bl_quantite_document(ligne) -> int:
    """Quantité affichée sur BL / PDF (= quantité commandée, identique à la facture)."""
    return int(getattr(ligne, "quantite_commandee", None) or 0)
