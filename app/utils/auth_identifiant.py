"""Recherche utilisateur par email ou numéro de téléphone (connexion)."""

from __future__ import annotations

from ..extensions import db
from ..models.employe import Employe
from ..models.user import User


def phone_digits(value: str | None) -> str:
    """Extrait les chiffres ; retire le préfixe international sénégalais courant."""
    digits = ''.join(c for c in (value or '') if c.isdigit())
    if digits.startswith('00221'):
        digits = digits[5:]
    elif digits.startswith('221') and len(digits) > 9:
        digits = digits[3:]
    return digits


def phone_key(value: str | None) -> str:
    """Clé de comparaison — 9 derniers chiffres (ex. 771234567)."""
    digits = phone_digits(value)
    if len(digits) >= 9:
        return digits[-9:]
    return digits


def phones_match(a: str | None, b: str | None) -> bool:
    ka = phone_key(a)
    kb = phone_key(b)
    return bool(ka and kb and ka == kb)


def format_phone_storage(value: str | None) -> str | None:
    """Format stocké en base (9 chiffres locaux)."""
    key = phone_key(value)
    return key or None


def is_email_identifier(value: str) -> bool:
    return '@' in (value or '')


def find_user_by_login(identifier: str) -> User | None:
    """Retrouve un utilisateur par email ou téléphone."""
    ident = (identifier or '').strip()
    if not ident:
        return None

    if is_email_identifier(ident):
        return User.query.filter(
            db.func.lower(User.email) == ident.lower()
        ).first()

    key = phone_key(ident)
    if not key:
        return None

    for user in User.query.filter(User.telephone.isnot(None)).all():
        if phones_match(ident, user.telephone):
            return user

    for emp in Employe.query.filter(
        Employe.telephone.isnot(None),
        Employe.user_id.isnot(None),
    ).all():
        if phones_match(ident, emp.telephone):
            return User.query.get(emp.user_id)

    return None
