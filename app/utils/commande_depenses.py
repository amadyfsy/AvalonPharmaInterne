"""Dépenses liées aux commandes fournisseur (marqueur dans le libellé)."""
from __future__ import annotations

from ..models.depense import Depense


def marqueur_achat(numero_commande: str) -> str:
    return f"(achat {numero_commande})"


def libelle_depense_achat(libelle_base: str, numero_commande: str) -> str:
    base = (libelle_base or "").strip()
    marker = marqueur_achat(numero_commande)
    if marker in base:
        return base[:255]
    suffix = f" {marker}"
    max_len = 255 - len(suffix)
    if len(base) > max_len:
        base = base[:max_len].rstrip()
    return f"{base}{suffix}"


def libelle_base_depense_achat(libelle: str, numero_commande: str) -> str:
    suffix = f" {marqueur_achat(numero_commande)}"
    txt = (libelle or "").strip()
    if txt.endswith(suffix):
        return txt[: -len(suffix)].strip()
    return txt


def depense_liee_a_commande(depense: Depense, numero_commande: str) -> bool:
    return marqueur_achat(numero_commande) in (depense.libelle or "")


def notes_commande_sans_frais(notes: str | None) -> str:
    if not notes:
        return ""
    marker = "--- Dépenses (wizard approvisionnement) ---"
    if marker in notes:
        return notes.split(marker, 1)[0].strip()
    return notes.strip()
