"""Génération automatique des rappels récurrents."""

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from ..extensions import db
from ..models.rappel import RAPPEL_FREQUENCES, Rappel, RappelRecurrence

_FREQ_DELTA = {
    'mensuelle': relativedelta(months=1),
    'trimestrielle': relativedelta(months=3),
    'semestrielle': relativedelta(months=6),
    'annuelle': relativedelta(years=1),
}


def prochaine_date_prevue(base: date, frequence: str) -> date:
    delta = _FREQ_DELTA.get(frequence)
    if delta is None:
        raise ValueError(f'Fréquence inconnue: {frequence}')
    return base + delta


def _dernier_rappel(recurrence_id: int) -> Rappel | None:
    return (
        Rappel.query.filter_by(recurrence_id=recurrence_id)
        .order_by(Rappel.date_prevue.desc(), Rappel.id.desc())
        .first()
    )


def _a_rappel_en_cours(recurrence_id: int) -> bool:
    return (
        Rappel.query.filter_by(recurrence_id=recurrence_id, statut='en_cours').count() > 0
    )


def creer_rappel_depuis_modele(
    modele: RappelRecurrence,
    date_prevue: date,
    created_by: int,
) -> Rappel:
    date_limite = date_prevue + timedelta(days=modele.delai_limite_jours or 0)
    rappel = Rappel(
        titre=modele.titre,
        description=modele.description,
        categorie=modele.categorie,
        importance=modele.importance,
        date_prevue=date_prevue,
        date_limite=date_limite,
        statut='en_cours',
        recurrence_id=modele.id,
        created_by=created_by,
    )
    db.session.add(rappel)
    return rappel


def generer_prochain_rappel(
    modele: RappelRecurrence,
    apres_date: date | None = None,
    created_by: int | None = None,
) -> Rappel | None:
    """Crée la prochaine occurrence si le modèle est actif et qu'il n'y a pas déjà un rappel en cours."""
    if not modele.actif:
        return None
    if _a_rappel_en_cours(modele.id):
        return None

    dernier = _dernier_rappel(modele.id)
    base = apres_date or (dernier.date_prevue if dernier else modele.date_reference)
    prochaine = prochaine_date_prevue(base, modele.frequence)

    auteur = created_by or modele.created_by
    return creer_rappel_depuis_modele(modele, prochaine, auteur)


def synchroniser_rappels_recurrents() -> int:
    """Assure qu'un rappel en cours existe pour chaque modèle récurrent actif."""
    crees = 0
    for modele in RappelRecurrence.query.filter_by(actif=True).all():
        if _a_rappel_en_cours(modele.id):
            continue
        dernier = _dernier_rappel(modele.id)
        if dernier is None:
            creer_rappel_depuis_modele(modele, modele.date_reference, modele.created_by)
            crees += 1
            continue
        if generer_prochain_rappel(modele, apres_date=dernier.date_prevue):
            crees += 1
    if crees:
        db.session.commit()
    return crees
