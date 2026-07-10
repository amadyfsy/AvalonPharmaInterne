"""
Catégories de dépenses par défaut + codes système (liaisons Achats / Ventes).
Création / mise à jour idempotente au démarrage de l’application.
"""

from sqlalchemy import func, inspect, text

from ..extensions import db
from ..models.depense import CategorieDepense, Depense
from .categorie_depense_registry import (
    CODE_APPRO_ACHATS,
    CODE_APPRO_DOUANE,
    CODE_APPRO_IMPOT_DOUANE,
    CODE_APPRO_TRANSPORT,
    CODE_RH_TRANSPORT_PERSONNEL,
    CODE_SOCIALE_IPRES,
    CODE_VENTE_LIEE,
    get_categorie_by_code,
)

# Ordre = logique métier (appro → vente → social → général)
DEFAULT_CATEGORIES: tuple[dict, ...] = (
    {
        'nom': 'Dépenses liées aux achats',
        'code_systeme': CODE_APPRO_ACHATS,
        'type_depense': 'variable',
        'description': (
            'Frais rattachés aux commandes fournisseurs : transport marchandises, logistique, '
            'manutention et autres coûts d’approvisionnement (assistant commandes).'
        ),
        'icone': 'bi-bag-check',
    },
    {
        'nom': 'Transport du personnel',
        'code_systeme': CODE_RH_TRANSPORT_PERSONNEL,
        'type_depense': 'variable',
        'description': (
            'Déplacements des salariés : remboursements, titres de transport, indemnités kilométriques, etc.'
        ),
        'icone': 'bi-car-front',
    },
    {
        'nom': 'Douane',
        'code_systeme': CODE_APPRO_DOUANE,
        'type_depense': 'variable',
        'description': 'Frais et formalités douanières hors droits de douane purs (assistant commandes).',
        'icone': 'bi-building',
    },
    {
        'nom': 'Impôt douane',
        'code_systeme': CODE_APPRO_IMPOT_DOUANE,
        'type_depense': 'variable',
        'description': 'Droits de douane, taxes à l’import et redevances (assistant commandes).',
        'icone': 'bi-patch-check',
    },
    {
        'nom': 'Dépenses liées aux ventes',
        'code_systeme': CODE_VENTE_LIEE,
        'type_depense': 'variable',
        'description': 'Transport client, manutention ou autres coûts rattachés à une vente / livraison.',
        'icone': 'bi-cart-check',
    },
    {
        'nom': 'Salaires',
        'code_systeme': CODE_SOCIALE_IPRES,
        'type_depense': 'fixe',
        'description': 'Masse salariale et charges employeur (dont IPRES et autres déclarations sociales).',
        'icone': 'bi-wallet2',
    },
    {
        'nom': 'Frais bancaires & agios',
        'code_systeme': None,
        'type_depense': 'variable',
        'description': 'Commissions, agios, tenue de compte (hors trésorerie interne).',
        'icone': 'bi-bank',
    },
    {
        'nom': 'Maintenance & réparations',
        'code_systeme': None,
        'type_depense': 'variable',
        'description': 'Entretien matériel, véhicules, locaux ou équipements.',
        'icone': 'bi-tools',
    },
    {
        'nom': 'Télécoms & informatique',
        'code_systeme': None,
        'type_depense': 'fixe',
        'description': 'Internet, téléphonie, licences logicielles récurrentes.',
        'icone': 'bi-wifi',
    },
)

# Anciens libellés exacts → code (bases déjà en production sans code_systeme)
LEGACY_NOM_TO_CODE: dict[str, str] = {
    'Transport': CODE_APPRO_ACHATS,
    'Transport employé': CODE_RH_TRANSPORT_PERSONNEL,
    'Transport du personnel': CODE_RH_TRANSPORT_PERSONNEL,
    'Dépenses liées aux achats': CODE_APPRO_ACHATS,
    'Douane': CODE_APPRO_DOUANE,
    'Impôt douane': CODE_APPRO_IMPOT_DOUANE,
    'Impot douane': CODE_APPRO_IMPOT_DOUANE,
    'IPRES employeur': CODE_SOCIALE_IPRES,
    'Salaires': CODE_SOCIALE_IPRES,
    'Dépenses liées aux ventes': CODE_VENTE_LIEE,
}

_PERSONNEL_NOM_KEYS = frozenset({
    'transport employé',
    'transport employe',
    'transport du personnel',
})

_OBSOLETE_NOM_KEYS = frozenset({
    'salaire amady',
    'salaires amady',
    'transport',
    'transports',
})


def _is_salaire_amady(nom: str | None) -> bool:
    n = (nom or '').strip().casefold()
    return 'amady' in n and 'salaire' in n


def _is_obsolete_transport_label(nom: str | None, code: str | None) -> bool:
    """Libellés transport obsolètes (hors catégories système conservées)."""
    if (code or '').strip() in (
        CODE_APPRO_ACHATS,
        CODE_APPRO_TRANSPORT,
        CODE_RH_TRANSPORT_PERSONNEL,
    ):
        return False
    n = (nom or '').strip().casefold()
    return n in {'transport', 'transports'}


def ensure_code_systeme_column() -> None:
    """Ajoute la colonne code_systeme si la table existe déjà sans cette colonne (SQLite / déploiement sans migration)."""
    bind = db.engine
    insp = inspect(bind)
    if not insp.has_table('categories_depenses'):
        return
    cols = {c['name'] for c in insp.get_columns('categories_depenses')}
    if 'code_systeme' in cols:
        return
    db.session.execute(
        text('ALTER TABLE categories_depenses ADD COLUMN code_systeme VARCHAR(50) NULL')
    )
    db.session.commit()


def _reassign_depenses(from_cat_id: int, to_cat_id: int) -> None:
    if from_cat_id == to_cat_id:
        return
    Depense.query.filter_by(categorie_id=from_cat_id).update({'categorie_id': to_cat_id})


def _categorie_salaires() -> CategorieDepense | None:
    return get_categorie_by_code(CODE_SOCIALE_IPRES) or CategorieDepense.query.filter(
        func.lower(CategorieDepense.nom) == 'salaires'
    ).first()


def _migrate_legacy_appro_transport() -> bool:
    """Ancien code appro_transport → Dépenses liées aux achats (appro_achats)."""
    legacy = get_categorie_by_code(CODE_APPRO_TRANSPORT)
    if not legacy:
        return False

    achats = get_categorie_by_code(CODE_APPRO_ACHATS)
    if achats and achats.id != legacy.id:
        _reassign_depenses(legacy.id, achats.id)
        db.session.delete(legacy)
        return True

    legacy.code_systeme = CODE_APPRO_ACHATS
    legacy.nom = 'Dépenses liées aux achats'
    legacy.type_depense = 'variable'
    legacy.description = (
        'Frais rattachés aux commandes fournisseurs : transport marchandises, logistique, '
        'manutention et autres coûts d’approvisionnement (assistant commandes).'
    )
    legacy.icone = 'bi-bag-check'
    return True


def _cleanup_obsolete_categories() -> bool:
    """Supprime doublons / catégories obsolètes et harmonise le transport personnel."""
    changed = False
    salaires = _categorie_salaires()
    achats = get_categorie_by_code(CODE_APPRO_ACHATS)
    personnel = get_categorie_by_code(CODE_RH_TRANSPORT_PERSONNEL)

    for cat in list(CategorieDepense.query.all()):
        nom_key = (cat.nom or '').strip().casefold()
        code = (cat.code_systeme or '').strip()

        if _is_salaire_amady(cat.nom):
            if salaires and cat.id != salaires.id:
                _reassign_depenses(cat.id, salaires.id)
            db.session.delete(cat)
            changed = True
            continue

        if _is_obsolete_transport_label(cat.nom, code):
            target = personnel or achats
            if target and cat.id != target.id:
                _reassign_depenses(cat.id, target.id)
            db.session.delete(cat)
            changed = True
            continue

        if nom_key in _OBSOLETE_NOM_KEYS and nom_key not in ('transport', 'transports'):
            if salaires and cat.id != salaires.id:
                _reassign_depenses(cat.id, salaires.id)
            db.session.delete(cat)
            changed = True

    personnel = get_categorie_by_code(CODE_RH_TRANSPORT_PERSONNEL)
    personnel_candidates = []
    for cat in CategorieDepense.query.order_by(CategorieDepense.id.asc()).all():
        nom_key = (cat.nom or '').strip().casefold()
        code = (cat.code_systeme or '').strip()
        if code in (CODE_APPRO_ACHATS, CODE_APPRO_TRANSPORT):
            continue
        if nom_key in _PERSONNEL_NOM_KEYS or code == CODE_RH_TRANSPORT_PERSONNEL:
            personnel_candidates.append(cat)

    if len(personnel_candidates) >= 2:
        to_remove = personnel_candidates[0]
        keeper = personnel_candidates[1]
        for extra in personnel_candidates[2:]:
            _reassign_depenses(extra.id, keeper.id)
            db.session.delete(extra)
            changed = True
        _reassign_depenses(to_remove.id, keeper.id)
        db.session.delete(to_remove)
        personnel = keeper
        changed = True
    elif len(personnel_candidates) == 1:
        personnel = personnel_candidates[0]

    if personnel:
        fields = {
            'nom': 'Transport du personnel',
            'code_systeme': CODE_RH_TRANSPORT_PERSONNEL,
            'type_depense': 'variable',
            'description': (
                'Déplacements des salariés : remboursements, titres de transport, '
                'indemnités kilométriques, etc.'
            ),
            'icone': 'bi-car-front',
        }
        for key, value in fields.items():
            if getattr(personnel, key, None) != value:
                setattr(personnel, key, value)
                changed = True

    return changed


def _backfill_legacy_codes() -> bool:
    changed = False
    for nom, code in LEGACY_NOM_TO_CODE.items():
        row = CategorieDepense.query.filter_by(nom=nom).first()
        if row and not (getattr(row, 'code_systeme', None) or '').strip():
            existing = get_categorie_by_code(code)
            if existing and existing.id != row.id:
                _reassign_depenses(row.id, existing.id)
                db.session.delete(row)
            else:
                row.code_systeme = code
            changed = True
    return changed


def _apply_default_row(row: dict) -> bool:
    """True si une ligne a été ajoutée ou modifiée."""
    code = row.get('code_systeme')
    nom = (row['nom'] or '').strip()
    if not nom:
        return False

    if code:
        if CategorieDepense.query.filter_by(code_systeme=code).first():
            return False

    found_nom = CategorieDepense.query.filter_by(nom=nom).first()
    if found_nom:
        if code and not (getattr(found_nom, 'code_systeme', None) or '').strip():
            existing = get_categorie_by_code(code)
            if existing and existing.id != found_nom.id:
                _reassign_depenses(found_nom.id, existing.id)
                db.session.delete(found_nom)
                return True
            found_nom.code_systeme = code
            return True
        return False

    db.session.add(
        CategorieDepense(
            nom=nom,
            type_depense=row['type_depense'],
            description=(row.get('description') or '').strip() or None,
            icone=row.get('icone') or 'bi-tag',
            code_systeme=code,
        )
    )
    return True


def _sync_system_category_display() -> bool:
    """Harmonise libellés / icônes des catégories à code (bases déjà peuplées)."""
    targets: tuple[tuple[str, dict[str, str]], ...] = (
        (
            CODE_APPRO_ACHATS,
            {
                'nom': 'Dépenses liées aux achats',
                'icone': 'bi-bag-check',
                'description': (
                    'Frais rattachés aux commandes fournisseurs : transport marchandises, logistique, '
                    'manutention et autres coûts d’approvisionnement (assistant commandes).'
                ),
            },
        ),
        (
            CODE_RH_TRANSPORT_PERSONNEL,
            {
                'nom': 'Transport du personnel',
                'icone': 'bi-car-front',
                'description': (
                    'Déplacements des salariés : remboursements, titres de transport, '
                    'indemnités kilométriques, etc.'
                ),
            },
        ),
        (
            CODE_SOCIALE_IPRES,
            {
                'nom': 'Salaires',
                'icone': 'bi-wallet2',
                'description': (
                    'Masse salariale et charges employeur (dont IPRES et autres déclarations sociales).'
                ),
            },
        ),
    )
    changed = False
    for code, fields in targets:
        cat = CategorieDepense.query.filter_by(code_systeme=code).first()
        if not cat:
            continue
        for k, v in fields.items():
            if getattr(cat, k, None) != v:
                setattr(cat, k, v)
                changed = True
    return changed


def ensure_default_depense_categories():
    """Insère les catégories manquantes et rattache les codes système (idempotent)."""
    if not inspect(db.engine).has_table('categories_depenses'):
        return
    ensure_code_systeme_column()
    changed = False
    if _migrate_legacy_appro_transport():
        changed = True
    if any(_apply_default_row(row) for row in DEFAULT_CATEGORIES):
        changed = True
    if _backfill_legacy_codes():
        changed = True
    if _cleanup_obsolete_categories():
        changed = True
    if _sync_system_category_display():
        changed = True
    if changed:
        db.session.commit()
