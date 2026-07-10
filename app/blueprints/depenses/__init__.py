from flask import Blueprint
depenses_bp = Blueprint('depenses', __name__, template_folder='../../templates/depenses')
from . import routes
