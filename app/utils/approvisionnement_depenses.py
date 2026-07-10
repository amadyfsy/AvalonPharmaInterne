"""
Création d'enregistrements Depense à partir du JSON « frais » du wizard commande fournisseur.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import func

from ..extensions import db
from ..models.depense import CategorieDepense, Depense
from .categorie_depense_registry import (
    CODE_APPRO_ACHATS,
    CODE_APPRO_DOUANE,
    CODE_APPRO_IMPOT_DOUANE,
    get_categorie_by_code,
)
from .commande_depenses import libelle_depense_achat
from .depense_justificatif import allowed_justificatif, upload_depense_justificatif
from .depense_reference import prochaine_reference_depense


def _norm_mode_paiement(raw: str | None) -> str:
    m = (raw or '').strip().lower()
    allowed = {'espece', 'cheque', 'virement', 'carte'}
    if m in allowed:
        return m
    if m in ('especes', 'espèce', 'espece'):
        return 'espece'
    return 'virement'


def _categorie_achats() -> CategorieDepense | None:
    c = get_categorie_by_code(CODE_APPRO_ACHATS)
    if c:
        return c
    return (
        CategorieDepense.query.filter(
            func.lower(CategorieDepense.nom).like('%achat%')
        ).first()
    )


def _categorie_transport() -> CategorieDepense | None:
    return _categorie_achats()


def _categorie_douane() -> CategorieDepense | None:
    for code in (CODE_APPRO_DOUANE, CODE_APPRO_IMPOT_DOUANE):
        c = get_categorie_by_code(code)
        if c:
            return c
    c = CategorieDepense.query.filter(func.lower(CategorieDepense.nom) == 'douane').first()
    if c:
        return c
    for pattern in ('%impôt%douane%', '%impot%douane%', '%douane%'):
        c = CategorieDepense.query.filter(func.lower(CategorieDepense.nom).like(pattern)).first()
        if c:
            return c
    return None


def _float_amount(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fichier_justificatif_ok(fichier) -> bool:
    return bool(fichier and getattr(fichier, 'filename', None) and allowed_justificatif(fichier.filename))


def _transport_complet(t: Mapping[str, Any] | None) -> bool:
    if not t or not isinstance(t, dict):
        return False
    m = _float_amount(t.get('montant'))
    return bool(
        str(t.get('depart', '')).strip()
        and str(t.get('arrivee', '')).strip()
        and str(t.get('transporteur', '')).strip()
        and str(t.get('numero_transporteur', '')).strip()
        and m > 0
        and str(t.get('mode_paiement', '')).strip()
    )


def _douane_complet(d: Mapping[str, Any] | None) -> bool:
    if not d or not isinstance(d, dict):
        return False
    m = _float_amount(d.get('montant'))
    return bool(str(d.get('bureau', '')).strip() and m > 0 and str(d.get('mode_paiement', '')).strip())


def _depense_autre_complet(block: Mapping[str, Any] | None) -> bool:
    if not block or not isinstance(block, dict):
        return False
    m = _float_amount(block.get('montant'))
    return bool(block.get('categorie_id') and str(block.get('libelle', '')).strip() and m > 0 and str(block.get('mode_paiement', '')).strip())


def parse_frais_json(raw: str) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def valider_frais_justificatifs(frais_data: dict[str, Any], justificatifs: dict[str, Any] | None) -> str | None:
    """Le justificatif est facultatif : aucune erreur bloquante."""
    _ = frais_data, justificatifs
    return None


def sync_depenses_from_wizard_payload(
    commande,
    frais_data: dict[str, Any],
    user_id: int,
    justificatifs: dict[str, Any] | None = None,
) -> list[str]:
    """
    Crée des Depense liées à la commande (libellé + fournisseur + justificatif).
    Retourne une liste de messages d'avertissement (ex. catégorie manquante).
    """
    warnings: list[str] = []
    if not user_id or not frais_data:
        return warnings

    err = valider_frais_justificatifs(frais_data, justificatifs)
    if err:
        raise ValueError(err)

    date_dep = commande.date_commande
    numero = commande.numero
    fid = commande.fournisseur_id
    justificatifs = justificatifs or {}

    def _add_depense(*, cat, libelle_base, montant, mode, justif_file):
        ref = prochaine_reference_depense(date_dep)
        justif = upload_depense_justificatif(justif_file, cat.nom, ref)
        db.session.add(
            Depense(
                reference=ref,
                categorie_id=cat.id,
                type_depense=cat.type_depense,
                libelle=libelle_depense_achat(libelle_base, numero),
                montant_ht=montant,
                tva=Decimal('0'),
                montant_ttc=montant,
                date_depense=date_dep,
                mode_paiement=mode,
                fournisseur_id=fid,
                justificatif=justif,
                created_by=user_id,
            )
        )
        db.session.flush()

    t = frais_data.get('transport')
    if _transport_complet(t):
        cat = _categorie_transport()
        if not cat:
            warnings.append(
                'Transport saisi : créez ou conservez la catégorie système « Dépenses liées aux achats ».'
            )
        else:
            montant = Decimal(str(round(_float_amount(t.get('montant')), 2)))
            libelle = (
                f"Transport {t.get('depart', '').strip()} → {t.get('arrivee', '').strip()} — "
                f"{t.get('transporteur', '').strip()} (N° {t.get('numero_transporteur', '').strip()})"
            )[:255]
            extra = []
            if t.get('reference'):
                extra.append(f"Réf. {t['reference']}")
            if t.get('notes'):
                extra.append(str(t['notes'])[:200])
            if extra:
                libelle = (libelle + ' — ' + ' | '.join(extra))[:255]
            _add_depense(
                cat=cat,
                libelle_base=libelle,
                montant=montant,
                mode=_norm_mode_paiement(t.get('mode_paiement')),
                justif_file=justificatifs.get('transport'),
            )

    d = frais_data.get('douane')
    if _douane_complet(d):
        cat = _categorie_douane()
        if not cat:
            warnings.append(
                'Douane saisie : créez une catégorie « Douane » ou « Impôt douane » pour enregistrer la dépense.'
            )
        else:
            montant = Decimal(str(round(_float_amount(d.get('montant')), 2)))
            libelle = f"Douane — {d.get('bureau', '').strip()}"[:255]
            if d.get('reference'):
                libelle = (libelle + f" (décl. {d['reference']})")[:255]
            _add_depense(
                cat=cat,
                libelle_base=libelle,
                montant=montant,
                mode=_norm_mode_paiement(d.get('mode_paiement')),
                justif_file=justificatifs.get('douane'),
            )

    autre = frais_data.get('depense_autre') or frais_data.get('depense_wizard')
    if _depense_autre_complet(autre):
        try:
            cid = int(autre.get('categorie_id'))
        except (TypeError, ValueError):
            cid = None
        cat = db.session.get(CategorieDepense, cid) if cid else None
        if not cat:
            warnings.append('Dépense complémentaire : catégorie introuvable.')
        else:
            montant = Decimal(str(round(_float_amount(autre.get('montant')), 2)))
            libelle = str(autre.get('libelle', '')).strip()[:255]
            _add_depense(
                cat=cat,
                libelle_base=libelle,
                montant=montant,
                mode=_norm_mode_paiement(autre.get('mode_paiement')),
                justif_file=justificatifs.get('autre'),
            )

    return warnings
