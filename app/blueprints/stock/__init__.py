from flask import Blueprint

stock_bp = Blueprint('stock', __name__, template_folder='../../templates/stock')

from . import routes
