"""Avoirs : écart entre la quantité facturée et la quantité réellement livrée."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from ..extensions import db
from ..models.avoir import Avoir, LigneAvoir
from ..models.bon_livraison import BonLivraison, LigneBL
from ..models.facture import Facture, LigneFacture
from ..models.paiement_client import PaiementClient
from ..models.produit import Lot, Produit
from ..models.stock import MouvementStock, Stock


def _q2(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def total_avoirs_ttc(facture_id: int) -> Decimal:
    total = (
        db.session.query(func.coalesce(func.sum(Avoir.total_ttc), 0))
        .filter(Avoir.facture_id == facture_id)
        .scalar()
    )
    return _q2(total)


def ajuster_solde_facture(facture: Facture) -> None:
    """Reste à payer = total TTC − avoirs − paiements."""
    if not facture or facture.statut in ("brouillon", "annulee"):
        return
    total_paye = (
        db.session.query(func.coalesce(func.sum(PaiementClient.montant), 0))
        .filter(PaiementClient.facture_id == facture.id)
        .scalar()
    )
    total_paye = _q2(total_paye)
    avoirs = total_avoirs_ttc(facture.id)
    net = _q2(Decimal(facture.total_ttc or 0) - avoirs)
    if net < 0:
        net = Decimal("0.00")
    facture.montant_paye = total_paye
    reste = max(Decimal("0.00"), _q2(net - total_paye))
    facture.reste_a_payer = reste
    if reste <= Decimal("0.00"):
        facture.statut = "payee"
    elif total_paye > Decimal("0.00"):
        facture.statut = "partiellement_payee"
    else:
        facture.statut = "emise"


def _prochain_numero_avoir(d: date) -> str:
    prefix = f"AV-{d.year}-"
    rows = (
        db.session.query(Avoir.numero)
        .filter(Avoir.numero.like(f"{prefix}%"))
        .all()
    )
    max_seq = 0
    for (numero,) in rows:
        if not numero or not str(numero).startswith(prefix):
            continue
        try:
            max_seq = max(max_seq, int(str(numero)[len(prefix) :]))
        except ValueError:
            continue
    return f"{prefix}{max_seq + 1:04d}"


def _prix_facture(facture: Facture, produit_id: int) -> tuple[Decimal, Decimal]:
    ligne = (
        LigneFacture.query.filter_by(facture_id=facture.id, produit_id=produit_id)
        .order_by(LigneFacture.id.asc())
        .first()
    )
    produit = Produit.query.get(produit_id)
    pu = Decimal(ligne.prix_unitaire_ht if ligne else (produit.prix_vente_ht if produit else 0))
    tva = Decimal(produit.tva if produit else 0)
    return pu, tva


def _sync_stock_produit(produit_id: int) -> None:
    total = (
        db.session.query(func.coalesce(func.sum(Lot.quantite_disponible), 0))
        .filter(Lot.produit_id == produit_id)
        .scalar()
        or 0
    )
    stock = Stock.query.filter_by(produit_id=produit_id).first()
    if not stock:
        stock = Stock(produit_id=produit_id, quantite_disponible=0, quantite_reservee=0)
        db.session.add(stock)
    stock.quantite_disponible = int(total)
    from datetime import datetime

    stock.dernier_mouvement = datetime.utcnow()


def sortir_stock(ligne: LigneBL, qte: int, reference: str, user_id: int) -> None:
    if qte <= 0:
        return
    allocations = []
    if ligne.lot_id:
        lot = Lot.query.filter_by(id=ligne.lot_id, produit_id=ligne.produit_id).first()
        if not lot:
            raise ValueError("Lot invalide sur une ligne du bon de livraison.")
        if int(lot.quantite_disponible or 0) < qte:
            nom = lot.numero_lot or ligne.produit_id
            raise ValueError(f"Stock insuffisant sur le lot {nom}.")
        allocations.append((lot, qte))
    else:
        lots = (
            Lot.query.filter(Lot.produit_id == ligne.produit_id, Lot.quantite_disponible > 0)
            .order_by(Lot.date_peremption.asc(), Lot.id.asc())
            .all()
        )
        reste = qte
        for lot in lots:
            dispo = int(lot.quantite_disponible or 0)
            if dispo <= 0:
                continue
            take = min(dispo, reste)
            if take > 0:
                allocations.append((lot, take))
                reste -= take
            if reste <= 0:
                break
        if reste > 0:
            raise ValueError(
                f"Stock insuffisant pour livrer {qte} unité(s) "
                f"(il en manque {reste}). Saisissez la quantité réellement disponible : un avoir sera créé pour l'écart."
            )
    for lot, part in allocations:
        lot.quantite_disponible = int(lot.quantite_disponible or 0) - int(part)
        db.session.add(
            MouvementStock(
                produit_id=ligne.produit_id,
                lot_id=lot.id,
                type_mouvement="sortie",
                quantite=int(part),
                motif="Livraison client",
                reference_document=reference,
                utilisateur_id=user_id,
            )
        )
    _sync_stock_produit(ligne.produit_id)


def retour_stock(ligne: LigneBL, qte: int, reference: str, user_id: int) -> None:
    if qte <= 0:
        return
    lot = None
    if ligne.lot_id:
        lot = Lot.query.filter_by(id=ligne.lot_id, produit_id=ligne.produit_id).first()
    if lot is None:
        mvt = (
            MouvementStock.query.filter_by(
                produit_id=ligne.produit_id,
                reference_document=reference,
                type_mouvement="sortie",
            )
            .order_by(MouvementStock.id.desc())
            .first()
        )
        if mvt and mvt.lot_id:
            lot = Lot.query.get(mvt.lot_id)
    if lot is None:
        lot = (
            Lot.query.filter_by(produit_id=ligne.produit_id)
            .order_by(Lot.id.desc())
            .first()
        )
    if lot is None:
        raise ValueError("Aucun lot pour réintégrer la quantité non livrée.")
    lot.quantite_disponible = int(lot.quantite_disponible or 0) + int(qte)
    db.session.add(
        MouvementStock(
            produit_id=ligne.produit_id,
            lot_id=lot.id,
            type_mouvement="retour",
            quantite=int(qte),
            motif="Avoir — quantité facturée non livrée",
            reference_document=reference,
            utilisateur_id=user_id,
        )
    )
    _sync_stock_produit(ligne.produit_id)


def quantites_avoir_par_produit(facture_id: int) -> dict[int, int]:
    rows = (
        db.session.query(
            LigneAvoir.produit_id,
            func.coalesce(func.sum(LigneAvoir.quantite), 0),
        )
        .join(Avoir, LigneAvoir.avoir_id == Avoir.id)
        .filter(Avoir.facture_id == facture_id, LigneAvoir.quantite > 0)
        .group_by(LigneAvoir.produit_id)
        .all()
    )
    return {int(pid): int(q or 0) for pid, q in rows}


def quantite_nette_livraison(qte_facture: int, produit_id: int, avoirs: dict[int, int]) -> int:
    return max(0, int(qte_facture or 0) - int(avoirs.get(produit_id, 0)))


def repercuter_avoirs_sur_bl(facture: Facture) -> None:
    """Aligne un BL déjà existant. N'en crée pas un nouveau."""
    bl = BonLivraison.query.filter_by(facture_id=facture.id).first()
    if bl is None:
        return
    if bl.statut == "prepare":
        from .bl_from_facture import _ecrire_lignes_bl

        _ecrire_lignes_bl(facture, bl, livre=False)
        return
    avoirs = quantites_avoir_par_produit(facture.id)
    lignes_facture = {int(lf.produit_id): int(lf.quantite or 0) for lf in facture.lignes}
    for ligne in list(bl.lignes):
        qte_facture = lignes_facture.get(int(ligne.produit_id), 0)
        net = quantite_nette_livraison(qte_facture, int(ligne.produit_id), avoirs)
        ligne.quantite_commandee = net
        if int(ligne.quantite_livree or 0) > net:
            ligne.quantite_livree = net


def creer_avoir_depuis_facture(
    facture: Facture,
    qtes: dict[int, int],
    user_id: int,
    motif: str | None = None,
) -> Avoir:
    """Crée un avoir à partir des quantités choisies. Le BL n'est pas généré ici."""
    if facture.statut in ("brouillon", "annulee"):
        raise ValueError("Un avoir ne peut pas être émis sur cette facture.")
    deja = quantites_avoir_par_produit(facture.id)
    remise = Decimal(facture.remise_globale or 0)
    if remise < 0 or remise > 100:
        remise = Decimal("0")

    lignes = []
    for lf in facture.lignes:
        qte = int(qtes.get(lf.id, 0) or 0)
        if qte <= 0:
            continue
        reste = int(lf.quantite or 0) - int(deja.get(int(lf.produit_id), 0))
        if qte > reste:
            nom = lf.produit.designation if lf.produit else lf.produit_id
            raise ValueError(f"Quantité d'avoir trop élevée pour {nom} (maximum {reste}).")
        pu, tva_taux = _prix_facture(facture, lf.produit_id)
        brut = _q2(pu * Decimal(qte))
        ht = _q2(brut * (Decimal("1") - remise / Decimal("100")))
        tva = _q2(ht * tva_taux / Decimal("100"))
        lignes.append((lf.produit_id, qte, pu, ht, tva))
    if not lignes:
        raise ValueError("Indiquez une quantité supérieure à 0 pour au moins un produit.")

    bl = BonLivraison.query.filter_by(facture_id=facture.id).first()
    today = date.today()
    avoir = Avoir(
        numero=_prochain_numero_avoir(today),
        facture_id=facture.id,
        bl_id=bl.id if bl else None,
        client_id=facture.client_id,
        date_emission=today,
        motif=(motif or "").strip() or "Quantité facturée non livrée",
        total_ht=Decimal("0.00"),
        tva_montant=Decimal("0.00"),
        total_ttc=Decimal("0.00"),
        created_by=user_id,
    )
    db.session.add(avoir)
    db.session.flush()
    total_ht = Decimal("0.00")
    total_tva = Decimal("0.00")
    for produit_id, qte, pu, ht, tva in lignes:
        db.session.add(
            LigneAvoir(
                avoir_id=avoir.id,
                produit_id=produit_id,
                quantite=qte,
                prix_unitaire_ht=pu,
                montant_ht=ht,
                tva_montant=tva,
            )
        )
        total_ht += ht
        total_tva += tva
    avoir.total_ht = _q2(total_ht)
    avoir.tva_montant = _q2(total_tva)
    avoir.total_ttc = _q2(total_ht + total_tva)
    repercuter_avoirs_sur_bl(facture)
    ajuster_solde_facture(facture)
    from ..blueprints.clients.routes import _recompute_client_solde

    _recompute_client_solde(facture.client_id)
    return avoir


def quantite_avoir_produit(bl: BonLivraison, produit_id: int) -> int:
    total = (
        db.session.query(func.coalesce(func.sum(LigneAvoir.quantite), 0))
        .join(Avoir, LigneAvoir.avoir_id == Avoir.id)
        .filter(Avoir.bl_id == bl.id, LigneAvoir.produit_id == produit_id)
        .scalar()
    )
    return int(total or 0)


def enregistrer_livraison_avec_avoir(
    bl: BonLivraison,
    qtes_livrees: dict[int, int],
    user_id: int,
    motif: str | None = None,
) -> Avoir | None:
    """
    Met à jour les quantités livrées.
    L'écart avec la quantité facturée (commandée) devient un avoir.
    """
    if bl.statut == "retourne":
        raise ValueError("Ce bon de livraison est retourné.")
    facture = Facture.query.get(bl.facture_id) if bl.facture_id else None
    if facture is None:
        raise ValueError("Un avoir ne peut être émis que pour un BL lié à une facture.")
    if facture.statut == "annulee":
        raise ValueError("La facture liée est annulée.")

    remise = Decimal(facture.remise_globale or 0)
    if remise < 0:
        remise = Decimal("0")
    if remise > 100:
        remise = Decimal("0")

    avoir_lignes = []
    for ligne in bl.lignes:
        commandee = int(ligne.quantite_commandee or 0)
        if ligne.id not in qtes_livrees:
            cible = int(ligne.quantite_livree or 0) if bl.statut != "prepare" else commandee
        else:
            cible = int(qtes_livrees[ligne.id])
        if cible < 0 or cible > commandee:
            raise ValueError("La quantité livrée doit être comprise entre 0 et la quantité facturée.")
        actuel = int(ligne.quantite_livree or 0)
        delta = cible - actuel
        if delta > 0:
            sortir_stock(ligne, delta, bl.numero, user_id)
        elif delta < 0:
            retour_stock(ligne, -delta, bl.numero, user_id)
        ligne.quantite_livree = cible

        deja = quantite_avoir_produit(bl, ligne.produit_id)
        manque = commandee - cible
        if manque < deja:
            raise ValueError(
                "La quantité livrée est supérieure à ce qui reste après les avoirs déjà émis."
            )
        delta_avoir = manque - deja
        if delta_avoir > 0:
            pu, tva_taux = _prix_facture(facture, ligne.produit_id)
            brut = _q2(pu * Decimal(delta_avoir))
            ht = _q2(brut * (Decimal("1") - remise / Decimal("100")))
            tva = _q2(ht * tva_taux / Decimal("100"))
            avoir_lignes.append((ligne.produit_id, delta_avoir, pu, ht, tva))

    toutes_livrees = all(
        int(l.quantite_livree or 0) >= int(l.quantite_commandee or 0) for l in bl.lignes
    )
    aucune = all(int(l.quantite_livree or 0) == 0 for l in bl.lignes)
    if toutes_livrees:
        bl.statut = "livre"
    elif aucune and not avoir_lignes and not Avoir.query.filter_by(bl_id=bl.id).first():
        bl.statut = "prepare"
    else:
        bl.statut = "partiellement_livre"

    avoir = None
    if avoir_lignes:
        today = date.today()
        avoir = Avoir(
            numero=_prochain_numero_avoir(today),
            facture_id=facture.id,
            bl_id=bl.id,
            client_id=bl.client_id,
            date_emission=today,
            motif=(motif or "").strip() or "Quantité facturée non disponible à la livraison",
            total_ht=Decimal("0.00"),
            tva_montant=Decimal("0.00"),
            total_ttc=Decimal("0.00"),
            created_by=user_id,
        )
        db.session.add(avoir)
        db.session.flush()
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")
        for produit_id, qte, pu, ht, tva in avoir_lignes:
            db.session.add(
                LigneAvoir(
                    avoir_id=avoir.id,
                    produit_id=produit_id,
                    quantite=qte,
                    prix_unitaire_ht=pu,
                    montant_ht=ht,
                    tva_montant=tva,
                )
            )
            total_ht += ht
            total_tva += tva
        avoir.total_ht = _q2(total_ht)
        avoir.tva_montant = _q2(total_tva)
        avoir.total_ttc = _q2(total_ht + total_tva)

    ajuster_solde_facture(facture)
    from ..blueprints.clients.routes import _recompute_client_solde

    _recompute_client_solde(facture.client_id)
    return avoir
