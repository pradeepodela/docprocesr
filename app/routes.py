from flask import Blueprint, render_template, send_from_directory, jsonify
import os
from datetime import datetime

routes_bp = Blueprint("routes", __name__, template_folder="../templates", url_prefix="")

# Temporary uploads directory for previews exposed during processing
UPLOADS_TMP = 'uploads_tmp'
os.makedirs(UPLOADS_TMP, exist_ok=True)

@routes_bp.route('/', endpoint='index')
def index():
    # Render dashboard as home
    return render_template('dashboard.html')

@routes_bp.route('/invoices', endpoint='invoices_page')
def invoices_page():
    # Render invoices UI (moved from old index.html)
    return render_template('invoices.html')

@routes_bp.route('/bank-statements', endpoint='bank_statements_page')
def bank_statements_page():
    # Placeholder page for future bank statement processing
    return render_template('bank_statements.html')

@routes_bp.route('/kyc', endpoint='kyc_page')
def kyc_page():
    # Placeholder page for future KYC processing
    return render_template('kyc.html')

@routes_bp.route('/uploads_tmp/<path:filename>', endpoint='serve_temp_upload')
def serve_temp_upload(filename):
    # Serve temporary uploaded files for preview (images or PDFs)
    return send_from_directory(UPLOADS_TMP, filename)

@routes_bp.route('/api/health', endpoint='api_health')
def api_health():
    return jsonify({
        'status': 'ok',
        'time': datetime.utcnow().isoformat() + 'Z'
    }), 200
