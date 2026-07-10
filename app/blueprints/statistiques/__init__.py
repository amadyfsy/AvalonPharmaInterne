from flask import Blueprint

statistiques_bp = Blueprint(
    'statistiques',
    __name__,
    template_folder='../../templates/statistiques',
)
from . import routes  # noqa: E402, F401
