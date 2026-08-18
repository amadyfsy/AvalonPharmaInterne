import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask

from config import config
from .extensions import bcrypt, db, login_manager, mail, migrate, talisman


def app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == 'production':
        if not (app.config.get('SECRET_KEY') or '').strip():
            raise RuntimeError('SECRET_KEY est obligatoire en production.')
        if not (app.config.get('SECURITY_PASSWORD_SALT') or '').strip():
            raise RuntimeError('SECURITY_PASSWORD_SALT est obligatoire en production.')
        if not (os.environ.get('ENCRYPTION_KEY') or '').strip():
            app.logger.warning(
                'ENCRYPTION_KEY non défini — chiffrement RH désactivé.'
            )

    upload_root = app.config.get("UPLOAD_FOLDER")
    if upload_root:
        os.makedirs(upload_root, exist_ok=True)
        os.makedirs(os.path.join(upload_root, "parametres"), exist_ok=True)
        os.makedirs(os.path.join(upload_root, "depenses"), exist_ok=True)
        os.makedirs(os.path.join(upload_root, "produits"), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    # Flask-Login: required to load the current user from the session
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        # user_id comes as a string from the session
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None
    
    # Configure Logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/erp.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Medical ERP startup')
    
    # Configure Talisman for security headers
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "cdn.jsdelivr.net", "'unsafe-inline'"],
        'style-src': ["'self'", "cdn.jsdelivr.net", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https://ui-avatars.com"],
        'font-src': ["'self'", "cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"]
    }
    talisman.init_app(
        app,
        content_security_policy=csp,
        force_https=app.config.get('TALISMAN_FORCE_HTTPS', True),
    )
    
    # Make config variables globally accessible in templates
    @app.context_processor
    def inject_company_info():
        import os
        from flask import url_for
        from flask_login import current_user
        
        info = {
            'company_name': os.environ.get('COMPANY_NAME', 'MedDistrib SARL'),
            'company_address': os.environ.get('COMPANY_ADDRESS', ''),
            'company_phone': os.environ.get('COMPANY_PHONE', ''),
            'company_email': os.environ.get('COMPANY_EMAIL', 'avalonpharmasenegal@gmail.com'),
            'company_nif': os.environ.get('COMPANY_NIF', ''),
            'global_logo_url': None,
            'header_notifications': [],
            'header_messages': [],
            'header_notifications_count': 0,
            'header_messages_count': 0,
        }
        
        try:
            from .utils.parametres_pdf import get_logo_filepath
            from .models.parametres_documents import ParametresDocuments
            p = ParametresDocuments.get_singleton()
            if p and p.logo_filename and get_logo_filepath():
                info['global_logo_url'] = url_for('parametres.logo_file', filename=p.logo_filename)
        except Exception as e:
            app.logger.debug(f"Could not load global logo: {e}")

        # Menus du header (notifications + messages) par utilisateur connecté.
        try:
            if current_user and current_user.is_authenticated:
                from sqlalchemy import func

                from .models.notification import Notification

                inbox = (
                    Notification.query.filter_by(user_id=current_user.id)
                    .order_by(Notification.is_read.asc(), Notification.created_at.desc())
                    .limit(24)
                    .all()
                )
                notif_rows = [n for n in inbox if n.kind == "notification"][:5]
                msg_rows = [n for n in inbox if n.kind == "message"][:5]
                info["header_notifications"] = [
                    {
                        "id": n.id,
                        "icon": n.icon,
                        "title": n.title,
                        "text": n.text,
                        "url": n.url or url_for("dashboard.index"),
                        "is_read": bool(n.is_read),
                    }
                    for n in notif_rows
                ]
                info["header_messages"] = [
                    {
                        "id": m.id,
                        "icon": m.icon,
                        "title": m.title,
                        "text": m.text,
                        "url": m.url or url_for("auth.profil"),
                        "is_read": bool(m.is_read),
                    }
                    for m in msg_rows
                ]
                counts = dict(
                    db.session.query(Notification.kind, func.count(Notification.id))
                    .filter(
                        Notification.user_id == current_user.id,
                        Notification.is_read.is_(False),
                    )
                    .group_by(Notification.kind)
                    .all()
                )
                info["header_notifications_count"] = int(counts.get("notification") or 0)
                info["header_messages_count"] = int(counts.get("message") or 0)
        except Exception as e:
            app.logger.debug(f"Could not build header notifications/messages: {e}")
            
        return info

    # Avoid blueprint import errors (will add blueprints later)
    from .blueprints.achats import achats_bp
    from .blueprints.auth import auth_bp
    from .blueprints.clients import clients_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.depenses import depenses_bp
    from .blueprints.fournisseurs import fournisseurs_bp
    from .blueprints.rapports import rapports_bp
    from .blueprints.rappels import rappels_bp
    from .blueprints.rh import rh_bp
    from .blueprints.statistiques import statistiques_bp
    from .blueprints.parametres import parametres_bp
    from .blueprints.public import public_bp
    from .blueprints.recherche import recherche_bp
    from .blueprints.securite import securite_bp
    from .blueprints.stock import stock_bp
    from .blueprints.tresorerie import tresorerie_bp
    from .blueprints.ventes import ventes_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(stock_bp, url_prefix='/stock')
    app.register_blueprint(ventes_bp, url_prefix='/ventes')
    app.register_blueprint(clients_bp, url_prefix='/clients')
    app.register_blueprint(achats_bp, url_prefix='/achats')
    app.register_blueprint(fournisseurs_bp, url_prefix='/fournisseurs')
    app.register_blueprint(depenses_bp, url_prefix='/depenses')
    app.register_blueprint(rappels_bp, url_prefix='/rappels')
    app.register_blueprint(tresorerie_bp, url_prefix='/tresorerie')
    app.register_blueprint(rh_bp, url_prefix='/rh')
    app.register_blueprint(rapports_bp, url_prefix='/rapports')
    app.register_blueprint(statistiques_bp, url_prefix='/statistiques')
    app.register_blueprint(securite_bp, url_prefix='/securite')
    app.register_blueprint(parametres_bp, url_prefix='/parametres')
    app.register_blueprint(public_bp, url_prefix='/api/public/v1')
    app.register_blueprint(recherche_bp)

    from flask import render_template, redirect, request, url_for

    @app.errorhandler(403)
    def handle_forbidden(_exc):
        return render_template('errors/403.html'), 403

    @app.errorhandler(401)
    def handle_unauthorized(_exc):
        return redirect(url_for('auth.login', next=request.url))

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return render_template('errors/404.html'), 404

    # Setup Audit Listeners
    # We must import inside the function to avoid circular imports 
    # since setup_audit_listeners needs db
    from .utils.audit_listeners import setup_audit_listeners
    setup_audit_listeners(app)

    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('dashboard.index'))

    @app.route('/ping')
    def ping():
        return "pong"

    # Catégories de dépenses par défaut (impôt douane, IPRES employeur, etc.)
    with app.app_context():
        try:
            from .utils.seed_expense_categories import ensure_default_depense_categories

            ensure_default_depense_categories()
        except Exception as exc:
            app.logger.warning('Catégories dépenses par défaut non initialisées: %s', exc)

        try:
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            if 'parametres_documents' in inspector.get_table_names():
                doc_columns = {c['name'] for c in inspector.get_columns('parametres_documents')}
                if 'slogan' not in doc_columns:
                    db.session.execute(
                        text("ALTER TABLE parametres_documents ADD COLUMN slogan VARCHAR(255) NOT NULL DEFAULT ''")
                    )
                if 'site_web' not in doc_columns:
                    db.session.execute(
                        text(
                            "ALTER TABLE parametres_documents ADD COLUMN site_web "
                            "VARCHAR(255) NOT NULL DEFAULT 'https://avalonpharmasenegal.com'"
                        )
                    )
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Colonnes slogan/site_web non initialisées sur parametres_documents: %s', exc)

        try:
            from .models.parametres_documents import ParametresDocuments

            row = ParametresDocuments.get_singleton()
            old_sites = (
                "",
                "https://avalonpharma.com",
                "http://avalonpharma.com",
                "avalonpharma.com",
            )
            site_changed = False
            if (row.site_web or "").strip() in old_sites:
                row.site_web = "https://avalonpharmasenegal.com"
                site_changed = True
            from .utils.parametres_pdf import DEFAULT_COMPANY_EMAIL

            email_changed = False
            if (row.email or "").strip().lower() != DEFAULT_COMPANY_EMAIL.lower():
                row.email = DEFAULT_COMPANY_EMAIL
                email_changed = True
            if site_changed or email_changed:
                db.session.commit()
        except Exception as exc:
            app.logger.warning('Paramètres documents non initialisés (migrer la table ?): %s', exc)

        try:
            from .models.notification import Notification
            Notification.__table__.create(bind=db.engine, checkfirst=True)
        except Exception as exc:
            app.logger.warning('Table notifications non initialisée: %s', exc)

        try:
            from .models.rappel import Rappel, RappelRecurrence

            RappelRecurrence.__table__.create(bind=db.engine, checkfirst=True)
            Rappel.__table__.create(bind=db.engine, checkfirst=True)
        except Exception as exc:
            app.logger.warning('Tables rappels non initialisées: %s', exc)

        try:
            from sqlalchemy import inspect, text

            from .models.rappel import Rappel

            inspector = inspect(db.engine)
            if 'rappels' in inspector.get_table_names():
                rappel_cols = {c['name'] for c in inspector.get_columns('rappels')}
                if 'recurrence_id' not in rappel_cols:
                    db.session.execute(
                        text('ALTER TABLE rappels ADD COLUMN recurrence_id INTEGER NULL')
                    )
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Colonne recurrence_id non initialisée sur rappels: %s', exc)

        try:
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            if 'paies' in inspector.get_table_names():
                paie_cols = {c['name'] for c in inspector.get_columns('paies')}
                if 'depense_id' not in paie_cols:
                    db.session.execute(
                        text('ALTER TABLE paies ADD COLUMN depense_id INTEGER NULL')
                    )
                if 'montant_brut' not in paie_cols:
                    db.session.execute(text('ALTER TABLE paies ADD COLUMN montant_brut DECIMAL(10,2) NULL'))
                if 'charges_patronales' not in paie_cols:
                    db.session.execute(text('ALTER TABLE paies ADD COLUMN charges_patronales DECIMAL(10,2) NULL DEFAULT 0'))
                if 'ipres_salarial' not in paie_cols:
                    db.session.execute(text('ALTER TABLE paies ADD COLUMN ipres_salarial DECIMAL(10,2) NULL DEFAULT 0'))
                if 'css_salarial' not in paie_cols:
                    db.session.execute(text('ALTER TABLE paies ADD COLUMN css_salarial DECIMAL(10,2) NULL DEFAULT 0'))
                if 'ipres_patronal' not in paie_cols:
                    db.session.execute(text('ALTER TABLE paies ADD COLUMN ipres_patronal DECIMAL(10,2) NULL DEFAULT 0'))
                if 'css_patronal' not in paie_cols:
                    db.session.execute(text('ALTER TABLE paies ADD COLUMN css_patronal DECIMAL(10,2) NULL DEFAULT 0'))
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Colonne depense_id non initialisée sur paies: %s', exc)

        try:
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            if 'employes' in inspector.get_table_names():
                emp_cols = {c['name'] for c in inspector.get_columns('employes')}
                if 'date_sortie' not in emp_cols:
                    db.session.execute(text('ALTER TABLE employes ADD COLUMN date_sortie DATE NULL'))
                if 'motif_sortie' not in emp_cols:
                    db.session.execute(text('ALTER TABLE employes ADD COLUMN motif_sortie VARCHAR(40) NULL'))
                if 'notes_sortie' not in emp_cols:
                    db.session.execute(text('ALTER TABLE employes ADD COLUMN notes_sortie TEXT NULL'))
                if 'taux_ipres_salarial' not in emp_cols:
                    db.session.execute(text(
                        'ALTER TABLE employes ADD COLUMN taux_ipres_salarial DECIMAL(6,3) NOT NULL DEFAULT 5.6'
                    ))
                if 'taux_css_salarial' not in emp_cols:
                    db.session.execute(text(
                        'ALTER TABLE employes ADD COLUMN taux_css_salarial DECIMAL(6,3) NOT NULL DEFAULT 7.0'
                    ))
                if 'taux_ipres_patronal' not in emp_cols:
                    db.session.execute(text(
                        'ALTER TABLE employes ADD COLUMN taux_ipres_patronal DECIMAL(6,3) NOT NULL DEFAULT 8.4'
                    ))
                if 'taux_css_patronal' not in emp_cols:
                    db.session.execute(text(
                        'ALTER TABLE employes ADD COLUMN taux_css_patronal DECIMAL(6,3) NOT NULL DEFAULT 14.0'
                    ))
                if 'seuil_irpp' not in emp_cols:
                    db.session.execute(text(
                        'ALTER TABLE employes ADD COLUMN seuil_irpp DECIMAL(12,2) NOT NULL DEFAULT 30000'
                    ))
                if 'taux_irpp' not in emp_cols:
                    db.session.execute(text(
                        'ALTER TABLE employes ADD COLUMN taux_irpp DECIMAL(6,3) NOT NULL DEFAULT 10.0'
                    ))
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Colonnes sortie non initialisées sur employes: %s', exc)

        try:
            from .models.paiement_client import PaiementClient

            PaiementClient.__table__.create(bind=db.engine, checkfirst=True)
        except Exception as exc:
            app.logger.warning('Table paiements_clients non initialisée: %s', exc)

        try:
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            if 'factures' in inspector.get_table_names():
                facture_columns = {c['name'] for c in inspector.get_columns('factures')}
                if 'bc' not in facture_columns:
                    db.session.execute(text("ALTER TABLE factures ADD COLUMN bc VARCHAR(80) NULL"))
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Colonne bc non initialisée sur factures: %s', exc)

        try:
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            user_columns = {c['name'] for c in inspector.get_columns('users')}
            if 'first_name' not in user_columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR(120) NULL"))
            if 'last_name' not in user_columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN last_name VARCHAR(120) NULL"))
            if 'telephone' not in user_columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN telephone VARCHAR(20) NULL"))
            db.session.commit()
            try:
                from .models.employe import Employe
                from .models.user import User
                from .utils.auth_identifiant import format_phone_storage

                synced = False
                for emp in Employe.query.filter(
                    Employe.user_id.isnot(None),
                    Employe.telephone.isnot(None),
                ).all():
                    u = db.session.get(User, emp.user_id)
                    if u and not u.telephone:
                        u.telephone = format_phone_storage(emp.telephone)
                        synced = True
                if synced:
                    db.session.commit()
            except Exception as sync_exc:
                db.session.rollback()
                app.logger.warning('Sync téléphone employés → users: %s', sync_exc)
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Colonnes prénom/nom non initialisées sur users: %s', exc)

        try:
            from sqlalchemy import inspect, text

            from .models.produit import ProduitPhoto

            inspector = inspect(db.engine)
            if 'produits' in inspector.get_table_names():
                prod_cols = {c['name'] for c in inspector.get_columns('produits')}
                if 'photo_principale' not in prod_cols:
                    db.session.execute(
                        text('ALTER TABLE produits ADD COLUMN photo_principale VARCHAR(255) NULL')
                    )
                db.session.commit()
            ProduitPhoto.__table__.create(bind=db.engine, checkfirst=True)
        except Exception as exc:
            db.session.rollback()
            app.logger.warning('Photos produit non initialisées: %s', exc)

    return app


# alias factory explicite
create_app = app
