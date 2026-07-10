from flask import Blueprint

recherche_bp = Blueprint('recherche', __name__, template_folder='../../templates/recherche')

from . import routes  # noqa: E402, F401
