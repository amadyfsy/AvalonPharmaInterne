"""Création automatique d'une dépense lors du paiement d'un salaire."""

from __future__ import annotations

from datetime import date

from ..extensions import db
from ..models.depense import CategorieDepense, Depense
from ..models.employe import Paie
from .categorie_depense_registry import CODE_SOCIALE_IPRES, get_categorie_by_code
from .depense_reference import prochaine_reference_depense

_MOIS_FR = (
    '',
    'janvier',
    'février',
    'mars',
    'avril',
    'mai',
    'juin',
    'juillet',
    'août',
    'septembre',
    'octobre',
    'novembre',
    'décembre',
)

_MODES_AUTORISES = frozenset({'espece', 'cheque', 'virement', 'carte'})


def _categorie_salaires() -> CategorieDepense | None:
    cat = get_categorie_by_code(CODE_SOCIALE_IPRES)
    if cat:
        return cat
    return CategorieDepense.query.filter(
        CategorieDepense.nom.ilike('salaires')
    ).first()


def libelle_depense_paie(paie: Paie) -> str:
    emp = paie.employe
    mois = _MOIS_FR[paie.mois] if 1 <= paie.mois <= 12 else str(paie.mois)
    nom = f'{emp.nom} {emp.prenom}'.strip() if emp else 'Employé'
    return f'Salaire {nom} — {mois} {paie.annee} (paie #{paie.id})'


def creer_depense_paie(
    paie: Paie,
    *,
    mode_paiement: str,
    date_paiement: date,
    created_by: int,
) -> Depense:
    if paie.depense_id:
        exist = Depense.query.get(paie.depense_id)
        if exist:
            return exist

    categorie = _categorie_salaires()
    if not categorie:
        raise ValueError(
            'Catégorie « Salaires » introuvable. Vérifiez les catégories de dépenses.'
        )

    mode = (mode_paiement or 'virement').strip().lower()
    if mode not in _MODES_AUTORISES:
        raise ValueError('Mode de paiement invalide.')

    montant = float(paie.net_a_payer or 0)
    if montant <= 0:
        raise ValueError('Le montant net à payer doit être supérieur à zéro.')

    type_depense = getattr(categorie.type_depense, 'value', categorie.type_depense) or 'fixe'
    reference = prochaine_reference_depense(date_paiement)

    depense = Depense(
        reference=reference,
        categorie_id=categorie.id,
        type_depense=type_depense,
        libelle=libelle_depense_paie(paie),
        montant_ht=montant,
        tva=0,
        montant_ttc=montant,
        date_depense=date_paiement,
        mode_paiement=mode,
        fournisseur_id=None,
        justificatif=None,
        statut='en_attente',
        created_by=created_by,
    )
    db.session.add(depense)
    db.session.flush()
    paie.depense_id = depense.id
    return depense
