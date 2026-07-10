from flask import Blueprint
ventes_bp = Blueprint('ventes', __name__, template_folder='../../templates/ventes')
from . import routes
