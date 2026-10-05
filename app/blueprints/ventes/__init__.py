from flask import Blueprint

ventes_bp = Blueprint('ventes', __name__, template_folder='../../templates/ventes')


@ventes_bp.app_template_filter("pages_lignes_document")
def pages_lignes_document(lignes):
    from ...utils.pdf_documents_reportlab import _chunk_facture_lines

    return _chunk_facture_lines(list(lignes or []))


@ventes_bp.app_template_global("lignes_par_page_document")
def lignes_par_page_document():
    from ...utils.pdf_documents_reportlab import _FACTURE_LINES_PER_PAGE

    return _FACTURE_LINES_PER_PAGE


from . import routes
