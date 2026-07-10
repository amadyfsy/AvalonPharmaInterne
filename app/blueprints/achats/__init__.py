from flask import Blueprint
achats_bp = Blueprint('achats', __name__, template_folder='../../templates/achats')
from . import routes
