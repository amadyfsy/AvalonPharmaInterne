from flask import Blueprint
rapports_bp = Blueprint('rapports', __name__, template_folder='../../templates/rapports')
from . import routes
