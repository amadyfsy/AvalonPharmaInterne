from flask import Blueprint
rh_bp = Blueprint('rh', __name__, template_folder='../../templates/rh')
from . import routes
