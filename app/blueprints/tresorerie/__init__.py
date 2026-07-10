from flask import Blueprint
tresorerie_bp = Blueprint('tresorerie', __name__, template_folder='../../templates/tresorerie')
from . import routes
