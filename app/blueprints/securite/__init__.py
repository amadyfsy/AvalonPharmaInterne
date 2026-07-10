from flask import Blueprint
securite_bp = Blueprint('securite', __name__, template_folder='../../templates/securite')
from . import routes
