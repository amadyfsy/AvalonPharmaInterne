from flask import Blueprint

parametres_bp = Blueprint("parametres", __name__)

from . import routes  # noqa: E402, F401
