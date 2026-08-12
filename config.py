import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def _database_uri() -> str:
    """Construit l'URI MySQL sans que bash mange le $ du nom de base PA (DMS07$…)."""
    explicit = (os.environ.get("DATABASE_URL") or "").strip()
    user = (os.environ.get("MYSQL_USER") or "").strip()
    password = os.environ.get("MYSQL_PASSWORD") or ""
    host = (os.environ.get("MYSQL_HOST") or "").strip()
    database = (os.environ.get("MYSQL_DATABASE") or "").strip()
    if user and host and database:
        return URL.create(
            drivername="mysql+pymysql",
            username=user,
            password=password,
            host=host,
            database=database,
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)
    if explicit:
        return explicit
    return "mysql+pymysql://root:root@localhost:3306/medical_erp?charset=utf8mb4"


class BaseConfig:
    """Configuration Flask / SQLAlchemy — GestAvalon ERP."""

    DEBUG = False
    APP_NAME = "Avalon ERP"

    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "")

    UPLOAD_FOLDER = os.path.join(BASEDIR, "instance", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@avalon-pharma.sn")
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "false").lower() == "true"

    PASSWORD_RESET_TOKEN_HOURS = int(os.environ.get("PASSWORD_RESET_TOKEN_HOURS", "1"))
    PASSWORD_RESET_MIN_INTERVAL_SECONDS = int(
        os.environ.get("PASSWORD_RESET_MIN_INTERVAL_SECONDS", "60")
    )
    PASSWORD_RESET_PER_IP_WINDOW_MINUTES = int(
        os.environ.get("PASSWORD_RESET_PER_IP_WINDOW_MINUTES", "15")
    )
    PASSWORD_RESET_PER_IP_MAX_REQUESTS = int(
        os.environ.get("PASSWORD_RESET_PER_IP_MAX_REQUESTS", "5")
    )

    PUBLIC_CORS_ORIGINS = os.environ.get(
        "PUBLIC_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    TALISMAN_FORCE_HTTPS = os.environ.get("TALISMAN_FORCE_HTTPS", "true").lower() == "true"

    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "connect_args": {"charset": "utf8mb4"},
        }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-not-for-production")
    SECURITY_PASSWORD_SALT = os.environ.get(
        "SECURITY_PASSWORD_SALT", "dev-only-reset-salt"
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "")


config = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
