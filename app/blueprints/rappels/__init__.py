from flask import Blueprint

rappels_bp = Blueprint('rappels', __name__, template_folder='../../templates/rappels')
from . import routes  # noqa: E402, F401
