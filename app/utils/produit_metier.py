"""Champs spécifiques par type de catégorie produit (Médicaments, DM, Équipement)."""

from __future__ import annotations

from typing import Any, Iterable

# Codes reconnus dans CategorieProduit.code_formulaire
CODE_MEDICAMENTS = 'medicaments'
CODE_DISPOSITIFS = 'dispositifs'
CODE_EQUIPEMENT = 'equipement'

# Énumérations métier globales (UI + logique)
CATEGORIES_ENUM = (
    ('medicament', 'Médicament'),
    ('consommable', 'Consommable'),
    ('implant', 'Implant'),
    ('equipement', 'Équipement'),
)

SPECIALITES_BASE = [
    'Dentaire',
    'Ophtalmologie',
    'Cardiologie',
    'Oncologie',
    'Orthopédie',
    'Imagerie',
    'Chirurgie générale',
    'Neurologie',
    'Pneumologie',
    'ORL',
    'Gynécologie',
    'Urologie',
    'Dermatologie',
    'Laboratoire',
    'Urgences',
    'Réanimation',
    'Autre',
]


def ordered_specialites(names: Iterable[str]) -> tuple[str, ...]:
    """Tri alphabétique (casse ignorée), sans doublon, « Autre » toujours en dernier."""
    has_autre = False
    by_key: dict[str, str] = {}
    for n in names:
        s = str(n).strip()
        if not s:
            continue
        if s.casefold() == 'autre':
            has_autre = True
            continue
        k = s.casefold()
        by_key.setdefault(k, s)
    rest = sorted(by_key.values(), key=str.casefold)
    out = list(rest)
    if has_autre:
        out.append('Autre')
    return tuple(out)


MED_SPECIALITES = ordered_specialites(
    [
        'Ophtalmologie',
        'Oncologie',
        'Cardiologie',
        'Médecine interne',
        'Pédiatrie',
        'Neurologie',
        'Dermatologie',
        'ORL',
        'Gastro-entérologie',
        'Pneumologie',
        'Rhumatologie',
        'Endocrinologie',
        'Néphrologie',
        'Urologie',
        'Infectiologie',
        'Autre',
    ]
)

DM_SPECIALITES = ordered_specialites(
    [
        'Dentaire',
        'Orthopédie',
        'Ophtalmologie',
        'Chirurgie générale',
        'Cardiologie',
        'Bloc opératoire',
        'Stérilisation',
        'ORL',
        'Autre',
    ]
)

EQ_SPECIALITES = ordered_specialites(
    [
        'Imagerie',
        'Dentaire (Fauteuils)',
        'Bloc opératoire',
        'Laboratoire',
        'Urgences',
        'Réanimation',
        'Néonatologie',
        'Stérilisation',
        'Autre',
    ]
)


def specialites_form_grouped() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """
    Même listes que sur le formulaire création / édition produit
    (champ unifié ``specialite`` dans ``forms.py``).
    """
    return (
        ('Médicaments & solutions', tuple(MED_SPECIALITES)),
        ('Dispositifs médicaux', tuple(DM_SPECIALITES)),
        ('Équipement biomédical', tuple(EQ_SPECIALITES)),
    )


def specialites_allowed_from_form() -> frozenset[str]:
    """Ensemble des valeurs possibles pour la spécialité (comme sur le formulaire produit)."""
    return frozenset(
        s.strip()
        for _, lst in specialites_form_grouped()
        for s in lst
        if (s or "").strip()
    )


def specialite_choices_for_wtforms(category: Any | None) -> list:
    """
    Choix WTForms alignés sur le filtre de la liste produits (stock/index) :
    - sans catégorie (None ou id 0) : optgroups comme le filtre « Toutes » ;
    - avec catégorie : liste plate comme le filtre avec catégorie sélectionnée.
    """
    ph = '— Choisir une spécialité —'
    if category is None:
        return [
            ('\u00a0', [('', ph)]),
            *[(label, [(s, s) for s in lst]) for label, lst in specialites_form_grouped()],
        ]
    lst = specialites_list_for_category(category)
    if not lst:
        return [('', '— Non applicable pour cette catégorie —')]
    return [('', ph)] + [(s, s) for s in lst]


def specialites_list_for_category(category) -> list[str]:
    """
    Liste affichée à la création produit quand cette catégorie est choisie
    (un seul select Spécialité visible selon le code métier).
    """
    code = effective_metier_code(category) if category is not None else ''
    if code == CODE_MEDICAMENTS:
        return list(MED_SPECIALITES)
    if code == CODE_DISPOSITIFS:
        return list(DM_SPECIALITES)
    if code == CODE_EQUIPEMENT:
        return list(EQ_SPECIALITES)
    return []


KNOWN_FORMULAIRE = frozenset({CODE_MEDICAMENTS, CODE_DISPOSITIFS, CODE_EQUIPEMENT})
BUCKET_AUTRES = '_autres'


def _normalize_categorie_nom(nom: str | None) -> str:
    """Normalise le libellé catégorie pour heuristiques (accents, casse)."""
    if not nom:
        return ''
    n = nom.lower().strip()
    for a, b in (
        ('é', 'e'),
        ('è', 'e'),
        ('ê', 'e'),
        ('à', 'a'),
        ('ô', 'o'),
        ('î', 'i'),
        ('ù', 'u'),
        ('ç', 'c'),
        ('œ', 'oe'),
    ):
        n = n.replace(a, b)
    return n


def bucket_produit_categorie(code_formulaire: str | None, nom: str | None) -> str:
    """
    Regroupe une catégorie pour le select et la fiche métier.

    1) Utilise ``code_formulaire`` s'il vaut medicaments | dispositifs | equipement.
    2) Sinon, déduit du libellé (ex. « Consommables médicaux » → medicaments,
       « Matériel lourd » → equipement).
    """
    code = (code_formulaire or '').strip().lower()
    if code in KNOWN_FORMULAIRE:
        return code

    n = _normalize_categorie_nom(nom)
    if not n:
        return BUCKET_AUTRES

    # Dispositifs / instrumentation (avant les libellés très « médicaux » génériques)
    if any(
        p in n
        for p in (
            'dispositif medical',
            'dispositif',
            'implant',
            'instrumentation',
            'petite instrumentation',
            'lentille intra',
            'stent',
        )
    ):
        return CODE_DISPOSITIFS

    # Équipement lourd / biomédical
    if 'materiel lourd' in n or ('materiel' in n and 'lourd' in n):
        return CODE_EQUIPEMENT
    if any(
        p in n
        for p in (
            'equipement biomedical',
            'equipement',
            'biomedical',
            'imagerie medicale',
            'imagerie',
            'bloc operatoire',
            'sterilisateur',
            'respirateur',
            'monitoring',
            'fauteuil dentaire',
            'panoramique',
            'lampe a fente',
        )
    ):
        return CODE_EQUIPEMENT

    # Médicaments, consommables médicaux, solutions, etc.
    if any(
        p in n
        for p in (
            'consomm',
            'consomable',  # faute courante / variante
            'medicament',
            'pharmaceutique',
            'vaccin',
            'chimiotherapie',
            'injectable',
            'perfusion',
            'comprime',
            'gelule',
            'collyre',
        )
    ):
        return CODE_MEDICAMENTS

    return BUCKET_AUTRES


def effective_metier_code(category: Any) -> str:
    """
    Code métier utilisé pour fiche métier, JSON et JS (chaîne vide = pas de bloc dédié).
    Accepte un modèle ``CategorieProduit`` ou tout objet avec ``code_formulaire`` et ``nom``.
    """
    if category is None:
        return ''
    b = bucket_produit_categorie(
        getattr(category, 'code_formulaire', None),
        getattr(category, 'nom', None),
    )
    return '' if b == BUCKET_AUTRES else b


def _strip(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def build_donnees_metier(code: str | None, form) -> dict | None:
    """Construit le dict JSON à partir du formulaire selon le code catégorie."""
    if not code:
        return None
    c = code.strip().lower()
    spec_val = None
    if hasattr(form, 'specialite') and getattr(form, 'specialite', None) is not None:
        spec_val = _strip(form.specialite.data)
    if c == CODE_MEDICAMENTS:
        d = {
            'specialite': spec_val,
            'nom_commercial_dci': _strip(
                getattr(form, 'med_nom_commercial_dci', None) and form.med_nom_commercial_dci.data
            ),
            'indication_therapeutique': _strip(
                getattr(form, 'med_indication_therapeutique', None)
                and form.med_indication_therapeutique.data
            ),
            'code_ucd_cip': _strip(
                getattr(form, 'med_code_ucd_cip', None) and form.med_code_ucd_cip.data
            ),
            'mode_administration': _strip(
                getattr(form, 'med_mode_administration', None) and form.med_mode_administration.data
            ),
        }
    elif c == CODE_DISPOSITIFS:
        d = {
            'specialite': spec_val,
            'type_dispositif': _strip(
                getattr(form, 'dm_type_dispositif', None) and form.dm_type_dispositif.data
            ),
            'reference_sku': _strip(
                getattr(form, 'dm_reference_sku', None) and form.dm_reference_sku.data
            ),
            'taille_caracteristique': _strip(
                getattr(form, 'dm_taille_caracteristique', None)
                and form.dm_taille_caracteristique.data
            ),
            'conditionnement': _strip(
                getattr(form, 'dm_conditionnement', None) and form.dm_conditionnement.data
            ),
        }
    elif c == CODE_EQUIPEMENT:
        d = {
            'specialite': spec_val,
            'fonction_principale': _strip(
                getattr(form, 'eq_fonction_principale', None) and form.eq_fonction_principale.data
            ),
            'garantie_maintenance': _strip(
                getattr(form, 'eq_garantie_maintenance', None)
                and form.eq_garantie_maintenance.data
            ),
            'formation_requise': _strip(
                getattr(form, 'eq_formation_requise', None) and form.eq_formation_requise.data
            ),
        }
    else:
        return None

    if not any(d.values()):
        return None
    return d


def apply_donnees_metier_to_form(form, code: str | None, donnees: dict | None) -> None:
    """Pré-remplit les champs métier depuis le dict stocké (édition)."""
    if not code or not donnees:
        return
    c = code.strip().lower()
    dm = donnees if isinstance(donnees, dict) else {}
    if hasattr(form, 'specialite'):
        form.specialite.data = dm.get('specialite') or ''
    if c == CODE_MEDICAMENTS:
        if hasattr(form, 'med_nom_commercial_dci'):
            form.med_nom_commercial_dci.data = dm.get('nom_commercial_dci') or ''
        if hasattr(form, 'med_indication_therapeutique'):
            form.med_indication_therapeutique.data = dm.get('indication_therapeutique') or ''
        if hasattr(form, 'med_code_ucd_cip'):
            form.med_code_ucd_cip.data = dm.get('code_ucd_cip') or ''
        if hasattr(form, 'med_mode_administration'):
            form.med_mode_administration.data = dm.get('mode_administration') or ''
    elif c == CODE_DISPOSITIFS:
        if hasattr(form, 'dm_type_dispositif'):
            form.dm_type_dispositif.data = dm.get('type_dispositif') or ''
        if hasattr(form, 'dm_reference_sku'):
            form.dm_reference_sku.data = dm.get('reference_sku') or ''
        if hasattr(form, 'dm_taille_caracteristique'):
            form.dm_taille_caracteristique.data = dm.get('taille_caracteristique') or ''
        if hasattr(form, 'dm_conditionnement'):
            form.dm_conditionnement.data = dm.get('conditionnement') or ''
    elif c == CODE_EQUIPEMENT:
        if hasattr(form, 'eq_fonction_principale'):
            form.eq_fonction_principale.data = dm.get('fonction_principale') or ''
        if hasattr(form, 'eq_garantie_maintenance'):
            form.eq_garantie_maintenance.data = dm.get('garantie_maintenance') or ''
        if hasattr(form, 'eq_formation_requise'):
            form.eq_formation_requise.data = dm.get('formation_requise') or ''

