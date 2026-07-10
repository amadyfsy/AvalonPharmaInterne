"""Actions admin sur les comptes utilisateurs (partagé profil / sécurité)."""

from __future__ import annotations

from flask import flash, redirect, request, url_for
from flask_login import current_user

from ..extensions import bcrypt, db
from ..models.employe import Employe
from ..models.user import PasswordHistory, User
from .auth_identifiant import format_phone_storage, phones_match

ROLE_OPTIONS: tuple[str, ...] = (
    'admin',
    'manager',
    'comptable',
    'commercial',
    'rh',
    'magasinier',
)

ROLE_DESCRIPTIONS: dict[str, str] = {
    'admin': 'Accès complet — sécurité, paramètres PDF, tous les modules.',
    'manager': 'Direction — ventes, achats, stock, RH, validation des dépenses.',
    'comptable': 'Finance — dépenses, trésorerie, lecture des opérations commerciales.',
    'commercial': 'Ventes — clients, proformas, factures, bons de livraison.',
    'rh': 'Ressources humaines — employés, paies, congés.',
    'magasinier': 'Stock & logistique — inventaire, réceptions, bons de livraison.',
}


def _telephone_deja_utilise(phone: str | None, exclude_user_id: int | None = None) -> bool:
    stored = format_phone_storage(phone)
    if not stored:
        return False
    for u in User.query.filter(User.telephone.isnot(None)).all():
        if exclude_user_id and u.id == exclude_user_id:
            continue
        if phones_match(stored, u.telephone):
            return True
    return False


def handle_profile_telephone_post(*, redirect_endpoint: str):
    """Enregistre le téléphone de l'utilisateur connecté (connexion par numéro)."""
    if request.method != 'POST':
        return None
    if (request.form.get('profile_action') or '').strip() != 'update_telephone':
        return None

    raw = (request.form.get('telephone') or '').strip()
    phone = format_phone_storage(raw) if raw else None
    if raw and not phone:
        flash('Numéro de téléphone invalide (ex. 77 123 45 67).', 'danger')
        return redirect(url_for(redirect_endpoint))
    if phone and _telephone_deja_utilise(phone, exclude_user_id=current_user.id):
        flash('Ce numéro de téléphone est déjà utilisé par un autre compte.', 'warning')
        return redirect(url_for(redirect_endpoint))

    current_user.telephone = phone
    emp = Employe.query.filter_by(user_id=current_user.id).first()
    if emp:
        emp.telephone = phone
    db.session.commit()
    flash(
        'Numéro de téléphone enregistré. Vous pouvez vous connecter avec ce numéro.'
        if phone
        else 'Numéro de téléphone supprimé.',
        'success',
    )
    return redirect(url_for(redirect_endpoint))


def handle_admin_user_post(*, redirect_endpoint: str):
    """
    Traite admin_action depuis un formulaire POST.
    Retourne une redirect si une action a été traitée, sinon None.
    """
    if current_user.role != 'admin':
        return None
    if request.method != 'POST':
        return None
    action = (request.form.get('admin_action') or '').strip()
    if not action:
        return None

    if action == 'create_user':
        email = (request.form.get('new_email') or '').strip().lower()
        first_name = (request.form.get('new_first_name') or '').strip()
        last_name = (request.form.get('new_last_name') or '').strip()
        new_role = (request.form.get('new_role') or '').strip()
        is_active_new = request.form.get('new_is_active') == 'on'
        pwd_plain = (request.form.get('new_password') or '').strip()
        new_phone = format_phone_storage(request.form.get('new_telephone'))
        if not email or '@' not in email:
            flash('Email invalide.', 'danger')
            return redirect(url_for(redirect_endpoint))
        if not first_name or not last_name:
            flash('Le prénom et le nom sont obligatoires.', 'danger')
            return redirect(url_for(redirect_endpoint))
        if User.query.filter_by(email=email).first():
            flash('Un compte existe déjà avec cet email.', 'warning')
            return redirect(url_for(redirect_endpoint))
        if new_role not in ROLE_OPTIONS:
            flash('Rôle invalide.', 'danger')
            return redirect(url_for(redirect_endpoint))
        if new_phone and _telephone_deja_utilise(new_phone):
            flash('Ce numéro de téléphone est déjà utilisé par un autre compte.', 'warning')
            return redirect(url_for(redirect_endpoint))
        used_default_pwd = False
        if not pwd_plain:
            pwd_plain = 'passer123'
            used_default_pwd = True
        u = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=bcrypt.generate_password_hash(pwd_plain, rounds=12).decode('utf-8'),
            role=new_role,
            is_active=is_active_new,
            telephone=new_phone,
        )
        db.session.add(u)
        db.session.commit()
        msg = f'Utilisateur créé : {email}.'
        msg += (
            ' Mot de passe par défaut : passer123.'
            if used_default_pwd
            else ' Mot de passe défini lors de la création.'
        )
        flash(msg, 'success')
        return redirect(url_for(redirect_endpoint))

    user_id = request.form.get('user_id', type=int)
    target_user = User.query.get(user_id) if user_id else None
    if not target_user:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for(redirect_endpoint))

    if action == 'update_user':
        email = (request.form.get('edit_email') or '').strip().lower()
        first_name = (request.form.get('edit_first_name') or '').strip()
        last_name = (request.form.get('edit_last_name') or '').strip()
        new_role = (request.form.get('edit_role') or '').strip()
        edit_active = request.form.get('edit_is_active') == 'on'
        pwd_plain = (request.form.get('edit_password') or '').strip()
        edit_phone = format_phone_storage(request.form.get('edit_telephone'))
        if not email or '@' not in email:
            flash('Email invalide.', 'danger')
            return redirect(url_for(redirect_endpoint))
        if not first_name or not last_name:
            flash('Le prénom et le nom sont obligatoires.', 'danger')
            return redirect(url_for(redirect_endpoint))
        existing = User.query.filter(User.email == email, User.id != target_user.id).first()
        if existing:
            flash('Cet email est déjà utilisé par un autre compte.', 'danger')
            return redirect(url_for(redirect_endpoint))
        if new_role not in ROLE_OPTIONS:
            flash('Rôle invalide.', 'danger')
            return redirect(url_for(redirect_endpoint))
        if edit_phone and _telephone_deja_utilise(edit_phone, exclude_user_id=target_user.id):
            flash('Ce numéro de téléphone est déjà utilisé par un autre compte.', 'warning')
            return redirect(url_for(redirect_endpoint))
        if target_user.id == current_user.id and not edit_active:
            flash('Vous ne pouvez pas désactiver votre propre compte.', 'warning')
            return redirect(url_for(redirect_endpoint))
        target_user.first_name = first_name
        target_user.last_name = last_name
        target_user.email = email
        target_user.role = new_role
        target_user.is_active = edit_active
        target_user.telephone = edit_phone
        emp = Employe.query.filter_by(user_id=target_user.id).first()
        if emp and edit_phone:
            emp.telephone = edit_phone
        if pwd_plain:
            db.session.add(
                PasswordHistory(user_id=target_user.id, password_hash=target_user.password_hash)
            )
            target_user.password_hash = bcrypt.generate_password_hash(pwd_plain, rounds=12).decode('utf-8')
        db.session.commit()
        flash(f'Utilisateur {email} mis à jour.', 'success')
        return redirect(url_for(redirect_endpoint))

    if action == 'toggle_access':
        if target_user.id == current_user.id and target_user.is_active:
            flash('Vous ne pouvez pas désactiver votre propre compte.', 'warning')
            return redirect(url_for(redirect_endpoint))
        target_user.is_active = not target_user.is_active
        db.session.commit()
        etat = 'activé' if target_user.is_active else 'désactivé'
        flash(f'Accès {etat} pour {target_user.email}.', 'success')
        return redirect(url_for(redirect_endpoint))

    if action == 'activate_default':
        default_password = 'passer123'
        old_hash = target_user.password_hash
        target_user.password_hash = bcrypt.generate_password_hash(default_password, rounds=12).decode('utf-8')
        target_user.is_active = True
        if old_hash:
            db.session.add(PasswordHistory(user_id=target_user.id, password_hash=old_hash))
        db.session.commit()
        flash(
            f'Compte activé pour {target_user.email}. Mot de passe par défaut : {default_password}.',
            'success',
        )
        return redirect(url_for(redirect_endpoint))

    return None
