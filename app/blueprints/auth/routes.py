import secrets
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from ...extensions import bcrypt, db, mail
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message

from flask import current_app, flash, redirect, render_template, request, url_for

from ...models.user import (
    LoginAttempt,
    PasswordHistory,
    PasswordResetToken,
    User,
)
from ...models.notification import Notification
from ...models.bon_livraison import BonLivraison
from ...models.facture import Facture
from ...models.produit import Produit
from ...models.stock import Stock
from ...models.employe import Employe
from ...utils.auth_identifiant import find_user_by_login
from ...utils.user_admin import (
    ROLE_OPTIONS,
    handle_admin_user_post,
    handle_profile_telephone_post,
)
from . import auth_bp
from .forms import (
    ChangePasswordForm,
    ForgotPasswordForm,
    LoginForm,
    ResetPasswordForm,
)


def _normalize_email(value: str) -> str:
    return (value or '').strip().lower()


def _safe_next_url(next_url: str, fallback_endpoint: str = 'dashboard.index') -> str:
    if not next_url:
        return url_for(fallback_endpoint)
    parsed = urlparse(next_url)
    if parsed.netloc:
        return url_for(fallback_endpoint)
    return next_url


def _send_reset_email(user_email: str, reset_link: str) -> None:
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or 'noreply@avalon-pharma.sn'
    msg = Message(
        "Réinitialisation de votre mot de passe",
        sender=sender,
        recipients=[user_email],
    )
    msg.body = (
        "Vous avez demandé la réinitialisation de votre mot de passe.\n\n"
        f"Cliquez sur ce lien sécurisé : {reset_link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n"
        "Ce lien expire automatiquement."
    )
    mail.send(msg)


def _create_login_notifications(user: User, ip_addr: str) -> None:
    """
    Crée des notifications persistantes au moment de la connexion.
    On évite les doublons proches via source_key + fenêtre temporelle.
    """
    now = datetime.utcnow()
    dedup_since = now - timedelta(hours=12)

    def push(kind: str, icon: str, title: str, text: str, url: str, source_key: str) -> None:
        exists = (
            Notification.query.filter_by(user_id=user.id, source_key=source_key)
            .filter(Notification.created_at >= dedup_since)
            .first()
        )
        if exists:
            return
        db.session.add(
            Notification(
                user_id=user.id,
                kind=kind,
                icon=icon,
                title=title,
                text=text,
                url=url,
                source_key=source_key,
                is_read=False,
            )
        )

    # Message sécurité : connexion réussie.
    push(
        "message",
        "bi-person-check",
        "Connexion réussie",
        f"Connexion détectée depuis IP {ip_addr or 'inconnue'}.",
        url_for("auth.profil"),
        f"login-success-{ip_addr or 'na'}",
    )

    # Message sécurité : échecs récents.
    recent_fail_count = (
        LoginAttempt.query.filter_by(user_id=user.id, success=False)
        .filter(LoginAttempt.timestamp >= now - timedelta(days=2))
        .count()
    )
    if recent_fail_count:
        push(
            "message",
            "bi-shield-lock",
            "Tentatives échouées détectées",
            f"{recent_fail_count} tentative(s) de connexion échouée(s) sur 48h.",
            url_for("auth.profil"),
            f"login-fails-{recent_fail_count}",
        )

    # Notifications métier globales utiles.
    low_stock_count = (
        db.session.query(Stock)
        .join(Produit, Produit.id == Stock.produit_id)
        .filter(
            Produit.est_actif.is_(True),
            Stock.quantite_disponible <= Produit.seuil_alerte_stock,
        )
        .count()
    )
    if low_stock_count:
        push(
            "notification",
            "bi-exclamation-triangle",
            "Stock bas",
            f"{low_stock_count} produit(s) à surveiller.",
            url_for("stock.index"),
            f"stock-low-{low_stock_count}",
        )

    bl_pending_count = BonLivraison.query.filter(
        BonLivraison.statut.in_(["prepare", "partiellement_livre"])
    ).count()
    if bl_pending_count:
        push(
            "notification",
            "bi-truck",
            "Livraisons en attente",
            f"{bl_pending_count} BL à traiter.",
            url_for("ventes.bons_livraison"),
            f"bl-pending-{bl_pending_count}",
        )

    factures_open_count = Facture.query.filter(
        Facture.statut.in_(["emise", "partiellement_payee"])
    ).count()
    if factures_open_count:
        push(
            "notification",
            "bi-receipt",
            "Factures ouvertes",
            f"{factures_open_count} facture(s) non soldée(s).",
            url_for("ventes.factures"),
            f"fact-open-{factures_open_count}",
        )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        login_ident = (form.email.data or '').strip()
        user = find_user_by_login(login_ident)
        
        ip_addr = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        consecutive_fails = 0

        if user and user.is_active:
            recent_fails = (
                LoginAttempt.query.filter_by(user_id=user.id, success=False)
                .order_by(LoginAttempt.timestamp.desc())
                .limit(5)
                .all()
            )
            if len(recent_fails) == 5:
                time_diff = datetime.utcnow() - recent_fails[0].timestamp
                if time_diff.total_seconds() < 900:  # 15 minutes
                    flash(
                        'Compte temporairement bloqué après plusieurs tentatives. '
                        'Réessayez dans quelques minutes ou contactez un administrateur.',
                        'danger',
                    )
                    return render_template('auth/login.html', form=form)

            consecutive_fails = 0
            all_recent = (
                LoginAttempt.query.filter_by(user_id=user.id)
                .order_by(LoginAttempt.timestamp.desc())
                .limit(5)
                .all()
            )
            for attempt in all_recent:
                if not attempt.success:
                    consecutive_fails += 1
                else:
                    break

            if consecutive_fails > 0:
                delay = min(2 ** (consecutive_fails - 1), 8)
                time.sleep(delay)

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash('Ce compte est désactivé.', 'warning')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            
            attempt = LoginAttempt(user_id=user.id, email=user.email, ip_address=ip_addr, success=True, user_agent=user_agent)
            db.session.add(attempt)
            _create_login_notifications(user, ip_addr)
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            attempt = LoginAttempt(
                user_id=user.id if user else None, 
                email=login_ident, 
                ip_address=ip_addr, 
                success=False, 
                user_agent=user_agent
            )
            db.session.add(attempt)
            db.session.commit()
            
            # Lockout condition reached
            if user and consecutive_fails + 1 >= 5:
                try:
                    msg = Message("Alerte de sécurité : Compte bloqué", sender="noreply@meddistrib.com", recipients=["admin@meddistrib.com"])
                    msg.body = f"Le compte de l'utilisateur {user.email} a été verrouillé après 5 tentatives échouées depuis l'IP {ip_addr}."
                    mail.send(msg)
                except:
                    pass # Ignore if SMTP not configured yet

            flash('Identifiant ou mot de passe incorrect.', 'danger')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/notifications/open/<int:notification_id>')
@login_required
def open_notification(notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    target = _safe_next_url(notif.url, fallback_endpoint='dashboard.index')
    return redirect(target)


@auth_bp.route('/notifications/read-all')
@login_required
def read_all_notifications():
    kind = (request.args.get('kind') or '').strip().lower()
    next_url = _safe_next_url(request.args.get('next'), fallback_endpoint='dashboard.index')
    query = Notification.query.filter_by(user_id=current_user.id, is_read=False)
    if kind in ('notification', 'message'):
        query = query.filter_by(kind=kind)
    query.update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    return redirect(next_url)

@auth_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    form = ChangePasswordForm()

    phone_resp = handle_profile_telephone_post(redirect_endpoint='auth.profil')
    if phone_resp is not None:
        return phone_resp

    if current_user.role == 'admin':
        admin_resp = handle_admin_user_post(redirect_endpoint='auth.profil')
        if admin_resp is not None:
            return admin_resp

    if form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password_hash, form.old_password.data):
            flash('L\'ancien mot de passe est incorrect.', 'danger')
            return redirect(url_for('auth.profil'))
            
        # Check password history
        recent_passwords = PasswordHistory.query.filter_by(user_id=current_user.id).order_by(PasswordHistory.created_at.desc()).limit(5).all()
        for history in recent_passwords:
            if bcrypt.check_password_hash(history.password_hash, form.new_password.data):
                flash('Vous ne pouvez pas réutiliser vos 5 derniers mots de passe.', 'danger')
                return redirect(url_for('auth.profil'))
                
        # Update password
        new_hash = bcrypt.generate_password_hash(form.new_password.data, rounds=12).decode('utf-8')
        
        # Save old password to history
        hist = PasswordHistory(user_id=current_user.id, password_hash=current_user.password_hash)
        db.session.add(hist)
        
        current_user.password_hash = new_hash
        db.session.commit()
        
        flash('Votre mot de passe a été mis à jour avec succès.', 'success')
        return redirect(url_for('auth.profil'))

    users = []
    employes_by_user_id = {}
    if current_user.role == 'admin':
        users = User.query.order_by(User.created_at.desc()).all()
        employes = Employe.query.filter(Employe.user_id.isnot(None)).all()
        employes_by_user_id = {e.user_id: e for e in employes}

    return render_template(
        'auth/profil.html',
        form=form,
        users=users,
        role_options=ROLE_OPTIONS,
        employes_by_user_id=employes_by_user_id,
    )

@auth_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = _normalize_email(form.email.data)
        user = User.query.filter_by(email=email).first()
        if user:
            # Un seul lien valide à la fois : invalide tous les anciens jetons encore actifs.
            PasswordResetToken.query.filter_by(user_id=user.id, used=False).update(
                {'used': True}, synchronize_session=False
            )

            token = secrets.token_urlsafe(32)
            token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
            token_hours = int(current_app.config.get('PASSWORD_RESET_TOKEN_HOURS', 1))
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(hours=token_hours)
            )
            db.session.add(reset_token)
            db.session.commit()

            reset_link = url_for(
                'auth.reset_password',
                token=token,
                rid=reset_token.id,
                _external=True,
            )
            try:
                _send_reset_email(user.email, reset_link)
            except Exception as e:
                # Journaliser côté serveur sans divulguer d'information côté client.
                current_app.logger.warning(
                    "Echec envoi email de reset vers %s: %s",
                    user.email,
                    str(e),
                )

        # Always show success to prevent email enumeration
        flash('Un email avec les instructions pour réinitialiser votre mot de passe a été envoyé.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reinitialiser-mot-de-passe', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    token = request.args.get('token')
    rid = request.args.get('rid', type=int)
    
    if not token or not rid:
        flash('Lien de réinitialisation invalide.', 'danger')
        return redirect(url_for('auth.login'))

    valid_token_record = (
        PasswordResetToken.query.filter_by(id=rid, used=False)
        .filter(PasswordResetToken.expires_at > datetime.utcnow())
        .first()
    )
    if not valid_token_record or not bcrypt.check_password_hash(valid_token_record.token_hash, token):
        flash('Le lien de réinitialisation est invalide ou a expiré.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.get(valid_token_record.user_id)
    if not user:
        flash('Le lien de réinitialisation est invalide ou a expiré.', 'danger')
        return redirect(url_for('auth.login'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Check history
        recent_passwords = PasswordHistory.query.filter_by(user_id=user.id).order_by(PasswordHistory.created_at.desc()).limit(5).all()
        for history in recent_passwords:
            if bcrypt.check_password_hash(history.password_hash, form.new_password.data):
                flash('Vous ne pouvez pas réutiliser vos 5 derniers mots de passe.', 'danger')
                return render_template('auth/reset_password.html', form=form)
                
        new_hash = bcrypt.generate_password_hash(form.new_password.data, rounds=12).decode('utf-8')
        
        hist = PasswordHistory(user_id=user.id, password_hash=user.password_hash)
        db.session.add(hist)
        
        user.password_hash = new_hash
        valid_token_record.used = True
        # Révocation de tous les autres liens de reset encore valides.
        PasswordResetToken.query.filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != valid_token_record.id,
            PasswordResetToken.used.is_(False),
        ).update({'used': True}, synchronize_session=False)
        db.session.commit()
        
        flash('Votre mot de passe a été réinitialisé. Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', form=form)
