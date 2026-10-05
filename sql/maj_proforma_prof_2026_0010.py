#!/usr/bin/env python3
"""Remplace les lignes de PROF-2026-0010 (Hôpital Ndamatou de Touba).

Prix repris du proforma actuel :
  - implant souple avec injecteur : 7 000
  - implant rigide : 4 000
  - visqueux 1,8 % PFS 1 ml : 10 000
  - visqueux 2,4 % PFS 1 ml : 12 000
  - visqueux 3,0 % : prix catalogue s'il existe, sinon 14 000

Usage (console PythonAnywhere, sans source .env) :
  cd ~/AvalonPharmaInterne
  unset DATABASE_URL MYSQL_USER MYSQL_PASSWORD MYSQL_HOST MYSQL_DATABASE
  ~/.virtualenvs/avalon-interne/bin/python sql/maj_proforma_prof_2026_0010.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NUMERO = "PROF-2026-0010"
PRIX_SOUPLE = Decimal("7000")
PRIX_RIGIDE = Decimal("4000")
PRIX_V18 = Decimal("10000")
PRIX_V24 = Decimal("12000")
PRIX_V30_DEFAUT = Decimal("14000")

SOUPLE = {}
for n in range(8, 31):
    if n <= 18 or 26 <= n <= 29:
        SOUPLE[n] = 30
    elif n == 30:
        SOUPLE[n] = 20
    else:
        SOUPLE[n] = 50

RIGIDE = {}
for n in range(8, 31):
    if n <= 15:
        RIGIDE[n] = 30
    elif n == 30:
        RIGIDE[n] = 20
    else:
        RIGIDE[n] = 50

VISQUEUX = [
    ("1.8", 100, PRIX_V18, "Visqueux 1.8% PFS 1ml"),
    ("2.4", 100, PRIX_V24, "Visqueux 2.4% PFS 1ml"),
    ("3.0", 100, None, "Visqueux 3.0% PFS 1ml"),
]


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def a_puissance(designation: str, n: int) -> bool:
    compact = norm(designation).replace(" ", "")
    if re.search(rf"(?<!\d){n}dp(?!\d)", compact):
        return True
    # D19, D08, y compris collé au mot précédent (« injecteurd19 »)
    if re.search(rf"d0*{n}(?!\d)", compact):
        return True
    return False


def a_concentration(designation: str, conc: str) -> bool:
    compact = norm(designation).replace(" ", "")
    dotted = conc.replace(".", "")
    if conc.replace(".", "") in ("18", "24", "30"):
        if re.search(rf"{conc[0]}[.,]{conc[2]}", designation.replace(" ", "").lower()):
            return True
        if re.search(rf"(?<!\d){dotted}(?!\d)", compact) and "%" in designation:
            return True
    return conc in designation or conc.replace(".", ",") in designation


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").upper()
    return text[:40] or "X"


def trouver_famille(produits, famille: str, n: int | None = None, conc: str | None = None):
    candidats = []
    for p in produits:
        d = norm(p.designation)
        if famille == "souple":
            if "souple" not in d or "inject" not in d:
                continue
            if n is not None and not a_puissance(p.designation, n):
                continue
            if n is None and re.search(r"\d", d):
                continue
        elif famille == "rigide":
            if "implant" not in d or "souple" in d or "inject" in d:
                continue
            if n is not None and not a_puissance(p.designation, n):
                continue
            if n is None and re.search(r"\d", d):
                continue
        elif famille == "visqueux":
            if "visqueux" not in d:
                continue
            if conc and not a_concentration(p.designation, conc):
                continue
        else:
            continue
        candidats.append(p)
    if not candidats:
        return None
    candidats.sort(key=lambda p: (0 if p.est_actif else 1, len(p.designation)))
    return candidats[0]


def assurer_produit(Produit, Stock, db, produits, categorie_id, designation, prix):
    existant = trouver_exact(produits, designation)
    if existant:
        return existant
    ref = "PRD-" + slugify(designation)[:24]
    base = ref
    i = 1
    while Produit.query.filter_by(reference=ref).first():
        i += 1
        ref = f"{base}-{i}"
    pu = money(prix)
    produit = Produit(
        reference=ref,
        designation=designation,
        categorie_id=categorie_id,
        forme="dispositif",
        unite="unité",
        prix_achat_ht=money(pu * Decimal("0.7")),
        prix_vente_ht=pu,
        tva=Decimal("0"),
        prix_vente_ttc=pu,
        seuil_alerte_stock=5,
        est_actif=True,
    )
    db.session.add(produit)
    db.session.flush()
    db.session.add(Stock(produit_id=produit.id, quantite_disponible=0, quantite_reservee=0))
    produits.append(produit)
    print(f"  + produit {designation} @ {pu}")
    return produit


def trouver_exact(produits, designation: str):
    key = norm(designation)
    for p in produits:
        if norm(p.designation) == key:
            return p
    return None


def prix_ligne_famille(lignes, famille: str, conc: str | None = None):
    for ligne in lignes:
        d = ligne.produit.designation if ligne.produit else ""
        if famille == "souple" and "souple" in norm(d):
            return money(ligne.prix_unitaire_ht)
        if famille == "rigide" and "implant" in norm(d) and "souple" not in norm(d):
            return money(ligne.prix_unitaire_ht)
        if famille == "visqueux" and conc and "visqueux" in norm(d) and a_concentration(d, conc):
            return money(ligne.prix_unitaire_ht)
    return None


def main() -> None:
    from app import create_app
    from app.extensions import db
    from app.models.produit import Produit
    from app.models.proforma import LigneProforma, Proforma
    from app.models.stock import Stock
    from app.models.facture import Facture

    app = create_app()
    with app.app_context():
        proforma = (
            Proforma.query.filter_by(numero=NUMERO).first()
        )
        if not proforma:
            raise SystemExit(f"{NUMERO} introuvable.")
        if proforma.statut == "converti" or Facture.query.filter_by(proforma_id=proforma.id).first():
            raise SystemExit(f"{NUMERO} déjà converti : aucune modification.")

        produits = Produit.query.order_by(Produit.id).all()
        lignes = list(proforma.lignes)
        prix_souple = prix_ligne_famille(lignes, "souple") or PRIX_SOUPLE
        prix_rigide = prix_ligne_famille(lignes, "rigide") or PRIX_RIGIDE
        cat_id = None
        for ligne in lignes:
            if ligne.produit:
                cat_id = ligne.produit.categorie_id
                break
        if cat_id is None:
            raise SystemExit("Catégorie produit introuvable sur le proforma.")

        specs = []
        for n in range(8, 31):
            designation = f"Implant souple avec injecteur {n}DP"
            produit = trouver_famille(produits, "souple", n=n) or trouver_exact(produits, designation)
            if not produit:
                produit = assurer_produit(Produit, Stock, db, produits, cat_id, designation, prix_souple)
            specs.append((produit, SOUPLE[n], prix_souple))

        for n in range(8, 31):
            designation = f"Implant rigide {n}DP"
            produit = trouver_famille(produits, "rigide", n=n) or trouver_exact(produits, designation)
            if not produit:
                produit = assurer_produit(Produit, Stock, db, produits, cat_id, designation, prix_rigide)
            specs.append((produit, RIGIDE[n], prix_rigide))

        for conc, qty, prix_defaut, designation in VISQUEUX:
            prix = prix_ligne_famille(lignes, "visqueux", conc)
            produit = trouver_famille(produits, "visqueux", conc=conc) or trouver_exact(produits, designation)
            if prix is None and produit is not None:
                prix = money(produit.prix_vente_ht)
            if prix is None:
                prix = prix_defaut if prix_defaut is not None else PRIX_V30_DEFAUT
                if conc == "3.0":
                    print(f"  ! Visqueux 3.0% absent du proforma : prix {prix} FCFA (à corriger si besoin).")
            if not produit:
                produit = assurer_produit(Produit, Stock, db, produits, cat_id, designation, prix)
            specs.append((produit, qty, prix))

        LigneProforma.query.filter_by(proforma_id=proforma.id).delete(synchronize_session=False)
        total_ht = Decimal("0")
        tva = Decimal("0")
        for produit, qty, pu in specs:
            pu = money(pu)
            montant = money(pu * qty)
            taux = Decimal(str(produit.tva or 0))
            total_ht += montant
            tva += money(montant * taux / Decimal("100"))
            db.session.add(
                LigneProforma(
                    proforma_id=proforma.id,
                    produit_id=produit.id,
                    quantite=qty,
                    prix_unitaire_ht=pu,
                    remise=Decimal("0"),
                    montant_ht=montant,
                )
            )
        rem = Decimal(str(proforma.remise_globale or 0))
        total_ht = money(total_ht * (1 - rem / Decimal("100")))
        tva = money(tva * (1 - rem / Decimal("100")))
        proforma.total_ht = total_ht
        proforma.tva_montant = tva
        proforma.total_ttc = money(total_ht + tva)
        db.session.commit()
        print(f"{NUMERO} mis à jour : {len(specs)} lignes, total {proforma.total_ttc} FCFA")


if __name__ == "__main__":
    main()
