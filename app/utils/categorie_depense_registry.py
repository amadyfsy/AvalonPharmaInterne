"""
Codes stables des catégories de dépenses « système » (liaison Achats, Ventes, etc.).
Les catégories créées manuellement ont code_systeme = NULL.
"""

from __future__ import annotations

from typing import Any, Callable

from ..models.depense import CategorieDepense

# —— Codes réservés (ne pas réutiliser à la main en base) ——
CODE_APPRO_ACHATS = 'appro_achats'
CODE_APPRO_DOUANE = 'appro_douane'
CODE_APPRO_IMPOT_DOUANE = 'appro_impot_douane'
CODE_RH_TRANSPORT_PERSONNEL = 'rh_transport_personnel'
CODE_VENTE_LIEE = 'vente_liee'
CODE_SOCIALE_IPRES = 'sociale_ipres'

# Ancien code — migré automatiquement vers CODE_APPRO_ACHATS au démarrage
CODE_APPRO_TRANSPORT = 'appro_transport'

SYSTEM_CODE_ORDER: tuple[str, ...] = (
    CODE_APPRO_ACHATS,
    CODE_APPRO_DOUANE,
    CODE_APPRO_IMPOT_DOUANE,
    CODE_RH_TRANSPORT_PERSONNEL,
    CODE_VENTE_LIEE,
    CODE_SOCIALE_IPRES,
)

# Aide sous le nom dans la liste catégories (branche / automatisation)
LIAISON_MODULE_LABEL: dict[str, str] = {
    CODE_APPRO_ACHATS: 'Achats & commandes fournisseurs — fret, frais logistiques (assistant)',
    CODE_APPRO_DOUANE: 'Commandes fournisseurs — douane & formalités (assistant)',
    CODE_APPRO_IMPOT_DOUANE: 'Commandes fournisseurs — droits & taxes à l’import (assistant)',
    CODE_RH_TRANSPORT_PERSONNEL: 'Déplacements et remboursements du personnel',
    CODE_VENTE_LIEE: 'Module Ventes — frais rattachés à une livraison / vente',
    CODE_SOCIALE_IPRES: 'Salaires et charges employeur (IPRES, déclarations sociales, paie)',
}

GROUPE_ORDER: tuple[tuple[str, str, int], ...] = (
    ('appro', 'Achats & approvisionnement', 1),
    ('vente', 'Ventes & livraisons', 2),
    ('sociale', 'Salaires & charges sociales', 3),
    ('autre', 'Autres catégories', 4),
)


def get_categorie_by_code(code: str | None) -> CategorieDepense | None:
    if not code or not str(code).strip():
        return None
    return CategorieDepense.query.filter_by(code_systeme=str(code).strip()).first()


def groupe_key_for_category(cat: CategorieDepense) -> str:
    code = (getattr(cat, 'code_systeme', None) or '').strip()
    if code.startswith('appro_'):
        return 'appro'
    if code.startswith('vente_'):
        return 'vente'
    if code.startswith('sociale_') or code.startswith('rh_'):
        return 'sociale'
    return 'autre'


def _code_sort_rank(code: str | None) -> int:
    if not code:
        return 999
    if code == CODE_APPRO_TRANSPORT:
        return SYSTEM_CODE_ORDER.index(CODE_APPRO_ACHATS)
    try:
        return SYSTEM_CODE_ORDER.index(code)
    except ValueError:
        return 500


def sort_categories_for_display(categories: list[CategorieDepense]) -> list[CategorieDepense]:
    """Ordre d’affichage : groupe métier, puis codes système connus, puis nom."""

    def sort_key(c: CategorieDepense) -> tuple[int, int, str]:
        gk = groupe_key_for_category(c)
        gord = next((t[2] for t in GROUPE_ORDER if t[0] == gk), 99)
        code = (c.code_systeme or '').strip()
        return (gord, _code_sort_rank(code), (c.nom or '').casefold())

    return sorted(categories, key=sort_key)


def liaison_label_for_category(cat: CategorieDepense) -> str | None:
    code = (getattr(cat, 'code_systeme', None) or '').strip()
    if not code:
        return None
    if code == CODE_APPRO_TRANSPORT:
        return LIAISON_MODULE_LABEL.get(CODE_APPRO_ACHATS)
    return LIAISON_MODULE_LABEL.get(code)


def build_category_groups(
    categories: list[CategorieDepense],
    nb_depenses_par_cat: dict[int, int],
    type_str_fn: Callable[[CategorieDepense], str],
) -> list[dict[str, Any]]:
    """
    Regroupe les catégories pour l’UI (liste par famille métier).
    type_str_fn : callable(cat) -> 'fixe' | 'variable'
    """
    sorted_cats = sort_categories_for_display(categories)
    out: list[dict[str, Any]] = []
    for gkey, glabel, _ in GROUPE_ORDER:
        chunk = [c for c in sorted_cats if groupe_key_for_category(c) == gkey]
        if not chunk:
            continue
        rows = [
            {
                'cat': c,
                'type_str': type_str_fn(c),
                'nb_depenses': nb_depenses_par_cat.get(c.id, 0),
                'liaison': liaison_label_for_category(c),
            }
            for c in chunk
        ]
        out.append({'key': gkey, 'label': glabel, 'rows': rows})
    return out
