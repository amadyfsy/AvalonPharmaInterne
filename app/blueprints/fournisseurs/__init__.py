from flask import Blueprint
fournisseurs_bp = Blueprint('fournisseurs', __name__, template_folder='../../templates/fournisseurs')
from . import routes
