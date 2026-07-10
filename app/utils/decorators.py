from functools import wraps
from typing import Any

from flask import abort, request, current_app
from flask_login import current_user

# Matrice RBAC (identique à permission_required) — réutilisable pour l’UI (masquer des actions).
ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    'admin': {'all': ['all']},
    'manager': {
        'dashboard': ['all'],
        'rh': ['all'],
        'stock': ['all'],
        'ventes': ['all'],
        'achats': ['all'],
        'depenses': ['valider'],
        'rappels': ['all'],
        'rapports': ['all'],
    },
    'comptable': {
        'dashboard': ['read'],
        'rh': ['read'],
        'stock': ['read'],
        'ventes': ['read'],
        'achats': ['valider'],
        'depenses': ['saisir', 'read'],
        'rappels': ['create', 'read', 'valider'],
        'tresorerie': ['saisir', 'read'],
        'rapports': ['finance'],
    },
    'commercial': {
        'dashboard': ['ventes'],
        'ventes': ['create', 'read'],
        'rappels': ['create', 'read'],
        'rapports': ['ventes'],
    },
    'rh': {'dashboard': ['rh'], 'rh': ['all'], 'rappels': ['create', 'read'], 'rapports': ['rh']},
    'magasinier': {
        'dashboard': ['stock'],
        'stock': ['all'],
        'ventes': ['bl'],
        'achats': ['reception'],
        'rappels': ['create', 'read'],
        'rapports': ['stock'],
    },
}


def user_has_permission(user: Any, module: str, action: str) -> bool:
    """True si le rôle de ``user`` autorise ``action`` sur ``module`` (hors requête HTTP)."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    role = getattr(user, 'role', None)
    if role == 'admin':
        return True
    role_perms = ROLE_PERMISSIONS.get(str(role), {})
    mod_perms = role_perms.get(module, [])
    return 'all' in mod_perms or action in mod_perms


def role_required(*roles):
    """Decorator to require a certain role for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles and current_user.role != 'admin':
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(module, action):
    """Decorator to enforce RBAC module/action rules."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            role = current_user.role
            if role == 'admin':
                return f(*args, **kwargs)

            role_perms = ROLE_PERMISSIONS.get(role, {})
            mod_perms = role_perms.get(module, [])

            if 'all' in mod_perms or action in mod_perms:
                return f(*args, **kwargs)
                
            abort(403)
        return decorated_function
    return decorator
