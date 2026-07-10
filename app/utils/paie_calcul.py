"""Calcul bulletin de paie — IPRES + CSS (taux par employé ou défaut Sénégal)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

# Valeurs par défaut (en %) si non renseignées sur l'employé
DEFAULT_TAUX_IPRES_SALARIAL = Decimal('5.6')
DEFAULT_TAUX_CSS_SALARIAL = Decimal('7.0')
DEFAULT_TAUX_IPRES_PATRONAL = Decimal('8.4')
DEFAULT_TAUX_CSS_PATRONAL = Decimal('14.0')
DEFAULT_SEUIL_IRPP = Decimal('30000')
DEFAULT_TAUX_IRPP = Decimal('10.0')

MOIS_FR = (
    '',
    'Janvier',
    'Février',
    'Mars',
    'Avril',
    'Mai',
    'Juin',
    'Juillet',
    'Août',
    'Septembre',
    'Octobre',
    'Novembre',
    'Décembre',
)


def _q2(value: float | Decimal) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _pct(value: float | Decimal) -> Decimal:
    """Convertit un taux en % (5.6) en fraction décimale."""
    return Decimal(str(value or 0)) / Decimal('100')


def libelle_periode_paie(mois: int, annee: int) -> str:
    if 1 <= mois <= 12:
        return f'{MOIS_FR[mois]} {annee}'
    return f'{mois:02d}/{annee}'


def calculer_bulletin_paie(
    salaire_base: float | Decimal,
    *,
    primes: float | Decimal = 0,
    heures_sup: float | Decimal = 0,
    deductions: float | Decimal = 0,
    taux_ipres_salarial: float | Decimal = DEFAULT_TAUX_IPRES_SALARIAL,
    taux_css_salarial: float | Decimal = DEFAULT_TAUX_CSS_SALARIAL,
    taux_ipres_patronal: float | Decimal = DEFAULT_TAUX_IPRES_PATRONAL,
    taux_css_patronal: float | Decimal = DEFAULT_TAUX_CSS_PATRONAL,
    seuil_irpp: float | Decimal = DEFAULT_SEUIL_IRPP,
    taux_irpp: float | Decimal = DEFAULT_TAUX_IRPP,
) -> dict[str, Decimal]:
    base = _q2(salaire_base)
    pr = _q2(primes)
    hs = _q2(heures_sup)
    ded = _q2(deductions)

    brut = _q2(base + pr + hs)

    ipres_salarial = _q2(brut * _pct(taux_ipres_salarial))
    css_salarial = _q2(brut * _pct(taux_css_salarial))
    cotisations_sociales = _q2(ipres_salarial + css_salarial)

    ipres_patronal = _q2(brut * _pct(taux_ipres_patronal))
    css_patronal = _q2(brut * _pct(taux_css_patronal))
    charges_patronales = _q2(ipres_patronal + css_patronal)

    base_imposable = _q2(brut - cotisations_sociales)

    seuil = _q2(seuil_irpp)
    irpp = Decimal('0.00')
    if base_imposable > seuil:
        irpp = _q2((base_imposable - seuil) * _pct(taux_irpp))

    net_a_payer = _q2(base_imposable - irpp - ded)
    cout_total_employeur = _q2(brut + charges_patronales)

    return {
        'montant_brut': brut,
        'ipres_salarial': ipres_salarial,
        'css_salarial': css_salarial,
        'cotisations_sociales': cotisations_sociales,
        'ipres_patronal': ipres_patronal,
        'css_patronal': css_patronal,
        'charges_patronales': charges_patronales,
        'base_imposable': base_imposable,
        'irpp': irpp,
        'net_a_payer': net_a_payer,
        'cout_total_employeur': cout_total_employeur,
    }
