from datetime import datetime

from flask_login import login_required

from flask import render_template, request, send_file

from ...utils.nombre_lettres import format_montant_espace
from ...utils.pdf_generator import generate_pdf
from ...utils.statistiques_export import export_filename, generate_statistiques_excel
from ...utils.statistiques_queries import build_statistiques_bundle, parse_periode_from_request
from . import statistiques_bp


def _filtres_query(periode) -> dict:
    q = {
        'annee': periode.annee,
        'granularite': periode.granularite,
    }
    if periode.mois:
        q['mois'] = periode.mois
    if periode.trimestre:
        q['trimestre'] = periode.trimestre
    return q


@statistiques_bp.route('/')
@login_required
def index():
    periode, annees = parse_periode_from_request(request.args)
    bundle = build_statistiques_bundle(periode)
    return render_template(
        'statistiques/index.html',
        annee=periode.annee,
        annees=annees,
        periode=periode,
        filtres_query=_filtres_query(periode),
        kpi=bundle['kpi'],
        alertes=bundle['alertes'],
        top_clients=bundle['top_clients'],
        chart_data=bundle['chart_data'],
        format_fcfa=format_montant_espace,
    )


@statistiques_bp.route('/export/excel')
@login_required
def export_excel():
    periode, _ = parse_periode_from_request(request.args)
    bundle = build_statistiques_bundle(periode)
    excel_io = generate_statistiques_excel(bundle)
    return send_file(
        excel_io,
        download_name=export_filename(periode, 'xlsx'),
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@statistiques_bp.route('/export/pdf')
@login_required
def export_pdf():
    periode, _ = parse_periode_from_request(request.args)
    bundle = build_statistiques_bundle(periode)
    html = render_template(
        'statistiques/export_pdf.html',
        periode=periode,
        kpi=bundle['kpi'],
        alertes=bundle['alertes'],
        top_clients=bundle['top_clients'],
        chart_data=bundle['chart_data'],
        format_fcfa=format_montant_espace,
        genere_le=datetime.now(),
    )
    pdf_io = generate_pdf(html)
    return send_file(
        pdf_io,
        download_name=export_filename(periode, 'pdf'),
        as_attachment=True,
        mimetype='application/pdf',
    )
