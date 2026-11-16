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
    from .avoir_service import quantite_nette_livraison, quantites_avoir_par_produit

    avoirs = quantites_avoir_par_produit(facture.id)
    LigneBL.query.filter_by(bl_id=bl.id).delete(synchronize_session=False)
    for lf in _lignes_facture(facture):
        qty = quantite_nette_livraison(int(lf.quantite or 0), int(lf.produit_id), avoirs)
        if qty <= 0:
            continue
        db.session.add(
            LigneBL(
                bl_id=bl.id,
                produit_id=lf.produit_id,
                lot_id=getattr(lf, "lot_id", None),
                quantite_commandee=qty,
                quantite_livree=qty if livre else 0,
            )
        )


def quantites_nettes_facture(facture: Facture) -> dict[int, int]:
    """Produit → quantité facturée nette d’avoirs (uniquement > 0)."""
    from .avoir_service import quantite_nette_livraison, quantites_avoir_par_produit

    avoirs = quantites_avoir_par_produit(facture.id)
    out: dict[int, int] = {}
    for lf in _lignes_facture(facture):
        net = quantite_nette_livraison(int(lf.quantite or 0), int(lf.produit_id), avoirs)
        if net > 0:
            out[int(lf.produit_id)] = net
    return out


def bl_est_desaligne(
    facture: Facture, bl: BonLivraison | None
) -> tuple[bool, list[str]]:
    """Indique si le BL manque ou n’est plus aligné sur la facture."""
    reasons: list[str] = []
    if bl is None:
        return True, ["BL absent"]

    if int(bl.client_id or 0) != int(facture.client_id or 0):
        nom_f = getattr(facture.client, "raison_sociale", None) or f"id={facture.client_id}"
        nom_b = getattr(bl.client, "raison_sociale", None) or f"id={bl.client_id}"
        reasons.append(f"client différent (facture={nom_f} / BL={nom_b})")
    if (bl.numero or "") != (facture.numero or ""):
        # Pas bloquant s’il y a un conflit de numéro ailleurs, mais à signaler
        reasons.append(f"numéro BL={bl.numero!r} ≠ facture={facture.numero!r}")

    f_map = quantites_nettes_facture(facture)
    b_map = {
        int(lb.produit_id): int(lb.quantite_commandee or 0)
        for lb in (bl.lignes or [])
        if int(lb.quantite_commandee or 0) > 0
    }
    if f_map != b_map:
        reasons.append("quantités / produits différents")

    return (len(reasons) > 0), reasons


def aligner_bl_sur_facture(
    facture: Facture,
    bl: BonLivraison | None = None,
    *,
    adresse_override: str | None = None,
    sync_adresse_si_client_change: bool = True,
) -> BonLivraison:
    """Aligne (ou crée) le BL sur la facture — même logique qu’après un avoir.

    Inclut toujours le **client** de la facture (``client_id``), et met à jour
    l’adresse de livraison si le client change ou si une adresse est fournie.

    - BL absent → création « préparé ».
    - BL « préparé » → réécriture complète des lignes.
    - BL déjà livré / partiel → ajuste les quantités commandées (plafonne le livré)
      et ajoute les produits nouvellement facturés.
    """
    from .avoir_service import quantite_nette_livraison, quantites_avoir_par_produit

    if bl is None:
        bl = BonLivraison.query.filter_by(facture_id=facture.id).first()
    if bl is None:
        return assurer_bl_pour_facture(
            facture,
            statut="prepare",
            adresse_override=adresse_override,
        )

    old_client_id = int(bl.client_id or 0)
    new_client_id = int(facture.client_id or 0)
    client_changed = old_client_id != new_client_id

    # Client : toujours celui de la facture
    bl.client_id = facture.client_id

    override = (adresse_override or "").strip() or None
    if override:
        bl.adresse_livraison = adresse_livraison_depuis_client(
            facture.client, override
        )
    elif sync_adresse_si_client_change and (
        client_changed or not (bl.adresse_livraison or "").strip()
    ):
        # Changement de client (ou adresse vide) → reprendre l'adresse du nouveau client
        bl.adresse_livraison = adresse_livraison_depuis_client(facture.client, None)

    if bl.numero != facture.numero:
        conflit = BonLivraison.query.filter(
            BonLivraison.numero == facture.numero,
            BonLivraison.id != bl.id,
        ).first()
        if not conflit:
            bl.numero = facture.numero

    if bl.statut == "prepare":
        _ecrire_lignes_bl(facture, bl, livre=False)
        return bl

    avoirs = quantites_avoir_par_produit(facture.id)
    lignes_facture = {
        int(lf.produit_id): int(lf.quantite or 0) for lf in _lignes_facture(facture)
    }
    bl_par_produit = {int(lb.produit_id): lb for lb in list(bl.lignes or [])}

    for produit_id, qte_facture in lignes_facture.items():
        net = quantite_nette_livraison(qte_facture, produit_id, avoirs)
        ligne = bl_par_produit.get(produit_id)
        if ligne is None:
            if net <= 0:
                continue
            db.session.add(
                LigneBL(
                    bl_id=bl.id,
                    produit_id=produit_id,
                    quantite_commandee=net,
                    quantite_livree=0,
                )
            )
            continue
        ligne.quantite_commandee = net
        if int(ligne.quantite_livree or 0) > net:
            ligne.quantite_livree = net

    for produit_id, ligne in bl_par_produit.items():
        if produit_id in lignes_facture:
            continue
        net = quantite_nette_livraison(0, produit_id, avoirs)
        ligne.quantite_commandee = net
        if int(ligne.quantite_livree or 0) > net:
            ligne.quantite_livree = net

    return bl


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
        # Toujours coller le client de la facture
        client_changed = int(existing.client_id or 0) != int(facture.client_id or 0)
        existing.client_id = facture.client_id
        if adresse_override is not None:
            existing.adresse_livraison = adresse_livraison_depuis_client(
                facture.client, adresse_override
            )
        elif client_changed or not (existing.adresse_livraison or "").strip():
            existing.adresse_livraison = adresse_livraison_depuis_client(
                facture.client, None
            )
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
