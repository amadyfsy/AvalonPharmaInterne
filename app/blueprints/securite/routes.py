from datetime import datetime, timedelta

from sqlalchemy import func

from ...extensions import db
from ...models.audit import AuditLog
from ...models.employe import Employe
from ...models.user import LoginAttempt, User
from ...utils.decorators import ROLE_PERMISSIONS, role_required
from ...utils.user_admin import (
    ROLE_DESCRIPTIONS,
    ROLE_OPTIONS,
    handle_admin_user_post,
)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from flask import render_template, request

from . import securite_bp


class SecuriteForm(FlaskForm):
    pass


@securite_bp.route('/audit')
@login_required
@role_required('admin')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    module = (request.args.get('module') or '').strip()
    action = (request.args.get('action') or '').strip()

    query = AuditLog.query
    if module:
        query = query.filter(AuditLog.module.ilike(f'%{module}%'))
    if action:
        query = query.filter(AuditLog.action == action)

    pagination = (
        query.order_by(AuditLog.timestamp.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )
    filtres_url = {}
    if module:
        filtres_url['module'] = module
    if action:
        filtres_url['action'] = action

    return render_template(
        'securite/audit.html',
        logs=pagination.items,
        pagination=pagination,
        module_filtre=module,
        action_filtre=action,
        filtres_url=filtres_url,
    )


@securite_bp.route('/utilisateurs', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def utilisateurs():
    redirect_resp = handle_admin_user_post(redirect_endpoint='securite.utilisateurs')
    if redirect_resp is not None:
        return redirect_resp

    form = SecuriteForm()
    users = User.query.order_by(User.created_at.desc()).all()
    employes = Employe.query.filter(Employe.user_id.isnot(None)).all()
    employes_by_user_id = {e.user_id: e for e in employes}

    nb_actifs = sum(1 for u in users if u.is_active)
    nb_inactifs = len(users) - nb_actifs
    par_role = dict(
        db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    )
    jamais_connectes = [u for u in users if u.is_active and not u.last_login]

    since = datetime.utcnow() - timedelta(days=14)
    echecs_connexion = (
        LoginAttempt.query.filter_by(success=False)
        .filter(LoginAttempt.timestamp >= since)
        .order_by(LoginAttempt.timestamp.desc())
        .limit(25)
        .all()
    )
    nb_echecs_14j = (
        LoginAttempt.query.filter_by(success=False)
        .filter(LoginAttempt.timestamp >= since)
        .count()
    )

    activite_recente = (
        AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    )

    return render_template(
        'securite/utilisateurs.html',
        form=form,
        users=users,
        employes_by_user_id=employes_by_user_id,
        role_options=ROLE_OPTIONS,
        role_descriptions=ROLE_DESCRIPTIONS,
        role_permissions=ROLE_PERMISSIONS,
        nb_actifs=nb_actifs,
        nb_inactifs=nb_inactifs,
        par_role=par_role,
        jamais_connectes=jamais_connectes,
        echecs_connexion=echecs_connexion,
        nb_echecs_14j=nb_echecs_14j,
        activite_recente=activite_recente,
        current_user_id=current_user.id,
    )
