"""Montants entiers en lettres (français) pour les PDF."""

from __future__ import annotations


def montant_fcfa_en_lettres(montant: int | float, devise: str = "francs") -> str:
    """
    Retourne une phrase du type « Trois cent soixante mille francs ».
    `montant` est arrondi à l'entier (FCFA).
    """
    try:
        n = int(round(float(montant)))
    except (TypeError, ValueError):
        n = 0
    if n < 0:
        n = abs(n)
    try:
        from num2words import num2words

        corps = num2words(n, lang="fr")
    except Exception:
        corps = str(n)
    corps = corps.strip()
    if not corps:
        corps = "zéro"
    # Première lettre en majuscule
    phrase = corps[0].upper() + corps[1:] if len(corps) > 1 else corps.upper()
    dev = (devise or "francs").strip()
    if dev:
        phrase = f"{phrase} {dev}"
    return phrase


def format_montant_espace(n) -> str:
    """Affichage type 360 000 (sans décimales si entier)."""
    try:
        x = float(n)
    except (TypeError, ValueError):
        return ""
    if abs(x - round(x)) < 1e-6:
        s = str(int(round(x)))
    else:
        s = f"{x:.2f}".replace(".", ",")
    if "," in s:
        ent, dec = s.split(",", 1)
    else:
        ent, dec = s, None
    ent = ent.replace("-", "")
    neg = float(n) < 0
    parts = []
    while len(ent) > 3:
        parts.insert(0, ent[-3:])
        ent = ent[:-3]
    if ent:
        parts.insert(0, ent)
    out = " ".join(parts)
    if dec is not None:
        out = f"{out},{dec}"
    return ("-" if neg else "") + out
