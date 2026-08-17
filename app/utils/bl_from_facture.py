"""Chaque facture a un bon de livraison lié (même numéro, mêmes lignes)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models.bon_livraison import BonLivraison, LigneBL
from ..models.facture import Facture, LigneFacture
from .document_numero import numero_bl_pour_facture, prochain_numero_document


def adresse_livraison_depuis_client(client, override: str | None = None) -> str:
    txt = (override or "").strip() or ((client.adresse if client else None) or "").strip()
    return txt if txt else "Adresse non renseignée"


def _lignes_facture(facture: Facture) -> list[LigneFacture]:
    return (
        LigneFacture.query.filter_by(facture_id=facture.id)
        .order_by(LigneFacture.id)
        .all()
    )


def _ecrire_lignes_bl(facture: Facture, bl: BonLivraison, *, livre: bool) -> None:
    LigneBL.query.filter_by(bl_id=bl.id).delete(synchronize_session=False)
    for lf in _lignes_facture(facture):
        qty = int(lf.quantite or 0)
        db.session.add(
            LigneBL(
                bl_id=bl.id,
                produit_id=lf.produit_id,
                lot_id=getattr(lf, "lot_id", None),
                quantite_commandee=qty,
                quantite_livree=qty if livre else 0,
            )
        )


def assurer_bl_pour_facture(
    facture: Facture,
    *,
    statut: str | None = None,
    date_livraison=None,
    adresse_override: str | None = None,
    livreur: str | None = None,
    notes: str | None = None,
) -> BonLivraison:
    """
    Garantit un BL pour ``facture``.

    Si un BL existe déjà, les lignes sont réalignées tant qu’il est encore « préparé ».
    Sinon un BL est créé avec le même numéro que la facture.
    """
    existing = BonLivraison.query.filter_by(facture_id=facture.id).first()
    if existing:
        if existing.statut == "prepare":
            _ecrire_lignes_bl(facture, existing, livre=False)
        return existing

    d_liv = date_livraison or facture.date_emission or date.today()
    if statut is None:
        statut = "prepare"
    livre = statut == "livre"

    numero = numero_bl_pour_facture(facture) or prochain_numero_document(d_liv)
    conflit = BonLivraison.query.filter_by(numero=numero).first()
    if conflit is not None:
        if conflit.facture_id in (None, facture.id):
            conflit.facture_id = facture.id
            conflit.client_id = facture.client_id
            if conflit.statut == "prepare" or livre:
                if livre:
                    conflit.statut = "livre"
                _ecrire_lignes_bl(facture, conflit, livre=livre)
            return conflit
        numero = prochain_numero_document(d_liv)

    bl = BonLivraison(
        numero=numero,
        facture_id=facture.id,
        client_id=facture.client_id,
        date_livraison=d_liv,
        adresse_livraison=adresse_livraison_depuis_client(facture.client, adresse_override),
        livreur=(livreur or "").strip() or None,
        statut=statut,
        notes=(notes or "").strip() or None,
    )
    try:
        with db.session.begin_nested():
            db.session.add(bl)
            db.session.flush()
    except IntegrityError:
        numero = prochain_numero_document(d_liv)
        bl.numero = numero
        db.session.add(bl)
        db.session.flush()
    _ecrire_lignes_bl(facture, bl, livre=livre)
    return bl
