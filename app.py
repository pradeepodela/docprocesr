from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session
import os
import tempfile
import json
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from models import InvoiceData, LineItem
from csv_conversion import convert_invoices_to_csv, create_summary_csv
# Modularized imports
from app.routes import routes_bp
from app.services import (
    allowed_file,
    save_upload_and_preview,
    run_ocr,
    persist_preview_to_public,
    clean_invoice_numbers,
    extract_with_llm,
    build_result_payload,
    delayed_cleanup_temp_previews,
)

app = Flask(
    __name__,
    static_folder='public',
    static_url_path='/public',
    template_folder='templates'
)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Register blueprint for static page routes and health
# Preserve original endpoint names without requiring 'routes.' prefix
app.register_blueprint(routes_bp, url_prefix="")


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('temp_files', exist_ok=True)

# Temporary uploads directory for previews exposed during processing
UPLOADS_TMP = 'uploads_tmp'
os.makedirs(UPLOADS_TMP, exist_ok=True)

# Using allowed_file from services module

# Routes for index, invoices, bank-statements, kyc, uploads_tmp served by blueprint in app/routes.py

@app.route('/upload', methods=['POST'])
def upload_files():
    app.logger.info("Received file upload request")
    if 'files' not in request.files:
        app.logger.warning("No files field in request")
        return jsonify({'success': False, 'errors': ['No files selected. Make sure to select PDF/JPG/PNG files.']}), 400
    
    files = request.files.getlist('files')
    app.logger.info(f"Number of files uploaded: {len(files)}")
    llm_choice = request.form.get('llm_choice', 'Mistral')
    include_detailed_csv = request.form.get('include_detailed_csv') == 'on'
    include_summary_csv = request.form.get('include_summary_csv') == 'on'
    confidence_threshold = request.form.get('confidence_threshold')
    app.logger.info(f"LLM choice: {llm_choice}, Detailed CSV: {include_detailed_csv}, Summary CSV: {include_summary_csv}, Confidence: {confidence_threshold}")
    
    if not files or files[0].filename == '':
        app.logger.warning("Files present but first filename empty")
        return jsonify({'success': False, 'errors': ['No files selected']}), 400
    
    all_invoices = []
    errors = []
    
    for file in files:
        if not (file and allowed_file(file.filename)):
            errors.append(f"Unsupported file type: {getattr(file, 'filename', 'unknown')}")
            continue
        try:
            # Save both to processing dir (existing) and temp public dir for preview
            file_path, temp_public_path = save_upload_and_preview(file)
            filename = os.path.basename(file_path)

            app.logger.info(f"Saved file to {file_path} and temp preview to {temp_public_path}")
            
            # OCR processing
            md = None
            preview_url = None
            app.logger.info(f"Processing file: {filename}")
            md, preview_url = run_ocr(file_path)
            if md is None:
                raise ValueError("OCR returned no metadata")
            # Persist a lightweight preview into public/previews for reliable UI preview
            try:
                public_url = persist_preview_to_public(preview_url, filename, file_path)
                if isinstance(md, dict) and public_url:
                    md['preview_public_url'] = public_url
                elif isinstance(md, dict) and (preview_url and isinstance(preview_url, str) and preview_url.startswith('data:image')):
                    md['preview_public_url'] = preview_url
                else:
                    app.logger.warning("No preview available to persist for UI")
            except Exception as p_err:
                app.logger.warning(f"Preview persistence failed: {p_err}")
            
            # LLM extraction
            invoice_data = extract_with_llm(md, preview_url, llm_choice)
            if invoice_data is None:
                app.logger.exception(f"LLM extraction failed for {filename}")
                errors.append(f"LLM extraction failed for {filename}: see logs")
            
            # Validate and clean the extracted data
            if not isinstance(invoice_data, dict):
                raise ValueError("Invalid data structure returned from LLM")
            
            # Clean numeric fields
            invoice_data = clean_invoice_numbers(invoice_data)
            
            # Add metadata
            invoice_data['source_file'] = filename
            # Attach preview URL preference:
            # 1) If OCR persisted an image preview in /public -> use it
            if isinstance(md, dict) and 'preview_public_url' in md:
                invoice_data['preview_url'] = md['preview_public_url']
            else:
                # 2) Otherwise expose the temp uploaded file for UI
                # For images, browser will render directly; for PDFs, iframe loads it.
                invoice_data['preview_url'] = f'/uploads_tmp/{secure_filename(filename)}'
            invoice_data['processed_at'] = datetime.now().isoformat()
            if confidence_threshold:
                invoice_data['confidence_threshold'] = confidence_threshold
            
            all_invoices.append(invoice_data)
            app.logger.info(f"Processed invoice from {filename}")
            
        except Exception as e:
            app.logger.exception(f"Error processing {getattr(file, 'filename', 'unknown')}: {e}")
            errors.append(f"Error processing {getattr(file, 'filename', 'unknown')}: {str(e)}")
        finally:
            # Clean up uploaded file
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as rm_err:
                app.logger.warning(f"Failed to remove temp file {file_path}: {rm_err}")
            # Do NOT remove temp_public_path here; leave it for preview until end of request
    
    if not all_invoices:
        return jsonify({
            'success': False,
            'errors': errors or ['No invoices were successfully processed']
        }), 200
    
    # Generate CSV files and store them temporarily
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_files = {}
    temp_file_paths = {}
    
    try:
        if include_detailed_csv:
            detailed_df = convert_invoices_to_csv(all_invoices)
            detailed_csv_path = f'temp_files/invoices_detailed_{timestamp}.csv'
            detailed_df.to_csv(detailed_csv_path, index=False)
            csv_files['detailed'] = detailed_df.to_csv(index=False)
            temp_file_paths['detailed'] = detailed_csv_path
    except Exception as csv_err:
        app.logger.exception(f"Failed to generate detailed CSV: {csv_err}")
        errors.append(f"Failed to generate detailed CSV: {str(csv_err)}")
    
    try:
        if include_summary_csv:
            summary_df = create_summary_csv(all_invoices)
            summary_csv_path = f'temp_files/invoices_summary_{timestamp}.csv'
            summary_df.to_csv(summary_csv_path, index=False)
            csv_files['summary'] = summary_df.to_csv(index=False)
            temp_file_paths['summary'] = summary_csv_path
    except Exception as csv_err:
        app.logger.exception(f"Failed to generate summary CSV: {csv_err}")
        errors.append(f"Failed to generate summary CSV: {str(csv_err)}")
    
    # Store JSON file
    try:
        json_path = f'temp_files/invoices_raw_{timestamp}.json'
        with open(json_path, 'w') as f:
            json.dump(all_invoices, f, indent=2)
        temp_file_paths['json'] = json_path
    except Exception as json_err:
        app.logger.exception(f"Failed to write raw JSON: {json_err}")
        errors.append(f"Failed to write raw JSON: {str(json_err)}")
    
    # Store file paths in session for download
    session['temp_files'] = temp_file_paths

    # Build result payload
    result = build_result_payload(all_invoices, errors)
    # Inject CSV strings into payload
    result['csv_files'] = csv_files
    
    # Schedule cleanup of temp previews once response is sent
    try:
        delayed_cleanup_temp_previews(all_invoices, delay_seconds=120)
    except Exception as e:
        app.logger.warning(f"Failed to schedule temp previews cleanup: {e}")

    return jsonify(result)

@app.route('/download/<file_type>')
def download_file(file_type):
    if file_type not in ['detailed', 'summary', 'json']:
        flash('Invalid file type')
        return redirect(url_for('index'))
    
    # Get file path from session
    temp_files = session.get('temp_files', {})
    file_path = temp_files.get(file_type)
    
    if not file_path or not os.path.exists(file_path):
        flash('File not found. Please process invoices first.')
        return redirect(url_for('index'))
    
    try:
        # Determine filename and MIME type
        filename = os.path.basename(file_path)
        if file_type == 'json':
            mime_type = 'application/json'
        else:
            mime_type = 'text/csv'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
    except Exception as e:
        flash(f'Error downloading file: {str(e)}')
        return redirect(url_for('index'))

@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'ok',
        'time': datetime.utcnow().isoformat() + 'Z'
    }), 200

if __name__ == '__main__':
    # Ensure folders exist before run
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs('temp_files', exist_ok=True)
    except Exception as e:
        app.logger.warning(f"Folder creation warning: {e}")
    app.run(debug=True)
