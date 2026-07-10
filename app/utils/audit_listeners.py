from ..extensions import db
from ..models.audit import AuditLog
from flask_login import current_user
from sqlalchemy import event

from flask import has_request_context, request


def get_current_user_id():
    if has_request_context() and current_user and current_user.is_authenticated:
        return current_user.id
    return None

def get_request_info():
    if has_request_context():
        return request.remote_addr, request.headers.get('User-Agent', '')[:255]
    return None, None

def dict_from_obj(obj, changes_only=False):
    # Retrieve model state and dict representation
    from sqlalchemy.orm import object_mapper
    try:
        mapper = object_mapper(obj)
    except:
        return {}
        
    state = db.inspect(obj)
    data = {}
    
    def safe_serialize(val):
        """Helper to ensure value is JSON serializable for SQLAlchemy."""
        import json
        try:
            json.dumps(val)
            return val
        except TypeError:
            return str(val)

    for attr in mapper.column_attrs:
        field = attr.key
        if field in ('id', 'created_at', 'updated_at', 'password_hash'):
            continue
            
        history = state.attrs.get(field).history
        if history.has_changes():
            if changes_only:
                old_val = safe_serialize(history.deleted[0] if history.deleted else None)
                new_val = safe_serialize(history.added[0] if history.added else None)
                data[field] = {'old': old_val, 'new': new_val}
            else:
                data[field] = safe_serialize(getattr(obj, field))
        elif not changes_only:
            data[field] = safe_serialize(getattr(obj, field))
                
    return data

def setup_audit_listeners(app):
    @event.listens_for(db.session, 'after_flush')
    def receive_after_flush(session, flush_context):
        # We process new, dirty and deleted objects
        audit_logs = []
        user_id = get_current_user_id()
        ip_address, user_agent = get_request_info()

        for obj in session.new:
            if isinstance(obj, AuditLog) or getattr(obj, '__tablename__', '') in ('login_attempts', 'password_history', 'password_reset_tokens'):
                continue
            
            entite = obj.__class__.__name__
            nouvelles_valeurs = dict_from_obj(obj)
            module = getattr(obj, '__module__', 'unknown').split('.')[-1]
            
            log = AuditLog(
                user_id=user_id,
                action='CREATE',
                module=module,
                entite=entite,
                entite_id=getattr(obj, 'id', None),
                nouvelles_valeurs=nouvelles_valeurs,
                ip_address=ip_address,
                user_agent=user_agent
            )
            audit_logs.append(log)

        for obj in session.dirty:
            if isinstance(obj, AuditLog) or getattr(obj, '__tablename__', '') in ('login_attempts', 'password_history', 'password_reset_tokens'):
                continue
                
            entite = obj.__class__.__name__
            changes = dict_from_obj(obj, changes_only=True)
            if not changes:
                continue
                
            anciennes = {k: v['old'] for k, v in changes.items()}
            nouvelles = {k: v['new'] for k, v in changes.items()}
            module = getattr(obj, '__module__', 'unknown').split('.')[-1]

            log = AuditLog(
                user_id=user_id,
                action='UPDATE',
                module=module,
                entite=entite,
                entite_id=getattr(obj, 'id', None),
                anciennes_valeurs=anciennes,
                nouvelles_valeurs=nouvelles,
                ip_address=ip_address,
                user_agent=user_agent
            )
            audit_logs.append(log)

        for obj in session.deleted:
            if isinstance(obj, AuditLog) or getattr(obj, '__tablename__', '') in ('login_attempts', 'password_history', 'password_reset_tokens'):
                continue
                
            entite = obj.__class__.__name__
            anciennes_valeurs = dict_from_obj(obj)
            module = getattr(obj, '__module__', 'unknown').split('.')[-1]

            log = AuditLog(
                user_id=user_id,
                action='DELETE',
                module=module,
                entite=entite,
                entite_id=getattr(obj, 'id', None),
                anciennes_valeurs=anciennes_valeurs,
                ip_address=ip_address,
                user_agent=user_agent
            )
            audit_logs.append(log)

        if audit_logs:
            # We add logs to the session but we don't commit them here (they'll be flushed with the rest)
            for log in audit_logs:
                session.add(log)
