from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session, send_from_directory
import os
import tempfile
import json
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from models import InvoiceData, LineItem
from ocr_processing import ocr_pdf, ocr_image
from llm_wrappers import _mistral_parse, _openrouter_parse, _create_invoice_extraction_prompt
from csv_conversion import convert_invoices_to_csv, create_summary_csv

app = Flask(
    __name__,
    static_folder='public',
    static_url_path='/public',
    template_folder='templates'
)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('temp_files', exist_ok=True)

# Temporary uploads directory for previews exposed during processing
UPLOADS_TMP = 'uploads_tmp'
os.makedirs(UPLOADS_TMP, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Ensure template exists and render
    return render_template('index.html')

@app.route('/uploads_tmp/<path:filename>')
def serve_temp_upload(filename):
    # Serve temporary uploaded files for preview (images or PDFs)
    return send_from_directory(UPLOADS_TMP, filename)

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
            filename = secure_filename(file.filename)
            # Save both to processing dir (existing) and temp public dir for preview
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            temp_public_path = os.path.join(UPLOADS_TMP, filename)
            file.save(file_path)
            try:
                # Also save a temp public copy for UI preview
                file.stream.seek(0)
            except Exception:
                pass
            try:
                with open(temp_public_path, 'wb') as ftmp:
                    file.stream.seek(0)
                    ftmp.write(file.read())
            except Exception:
                # If stream seek/read fails (already consumed), copy from saved file_path
                import shutil
                shutil.copyfile(file_path, temp_public_path)

            app.logger.info(f"Saved file to {file_path} and temp preview to {temp_public_path}")
            
            # OCR processing
            md = None
            preview_url = None
            if filename.lower().endswith('.pdf'):
                app.logger.info(f"Processing PDF file: {filename}")
                md, preview_url = ocr_pdf(file_path)
            else:
                app.logger.info(f"Processing Image file: {filename}")
                md, preview_url = ocr_image(file_path)
            if md is None:
                raise ValueError("OCR returned no metadata")
            # Persist a lightweight preview into public/previews for reliable UI preview
            try:
                os.makedirs(os.path.join(app.static_folder, 'previews'), exist_ok=True)
                saved_preview_path = None
                if isinstance(preview_url, str) and preview_url.startswith('data:image'):
                    # data URL -> save to file
                    import base64, re
                    m = re.match(r'data:image/(png|jpeg|jpg);base64,(.*)', preview_url)
                    ext = m.group(1) if m else 'png'
                    b64 = m.group(2) if m else preview_url.split(',', 1)[-1]
                    data = base64.b64decode(b64)
                    safe_base = os.path.splitext(filename)[0]
                    saved_preview_path = os.path.join(app.static_folder, 'previews', f'{safe_base}.preview.{ext}')
                    with open(saved_preview_path, 'wb') as out:
                        out.write(data)
                else:
                    # If original is an image and still exists, copy as preview
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and os.path.exists(file_path):
                        import shutil
                        safe_base = os.path.splitext(filename)[0]
                        ext = os.path.splitext(filename)[1].lstrip('.').lower() or 'png'
                        saved_preview_path = os.path.join(app.static_folder, 'previews', f'{safe_base}.preview.{ext}')
                        shutil.copyfile(file_path, saved_preview_path)
                if saved_preview_path and os.path.exists(saved_preview_path):
                    # Expose as /public/previews/<file>
                    md['preview_public_url'] = '/public/previews/' + os.path.basename(saved_preview_path)
                elif preview_url and isinstance(preview_url, str) and preview_url.startswith('data:image'):
                    # fallback keep original data url
                    md['preview_public_url'] = preview_url
                else:
                    app.logger.warning("No preview available to persist for UI")
            except Exception as p_err:
                app.logger.warning(f"Preview persistence failed: {p_err}")
            
            # LLM extraction
            prompt = _create_invoice_extraction_prompt(md)
            app.logger.debug(f"Prompt created, length={len(prompt) if isinstance(prompt,str) else 'n/a'}")
            
            invoice_data = None
            try:
                if llm_choice == 'Mistral':
                    from mistralai import TextChunk, ImageURLChunk
                    chunks = [TextChunk(text=prompt)]
                    if preview_url and isinstance(preview_url, str) and preview_url.startswith("data:image"):
                        chunks = [ImageURLChunk(image_url=preview_url)] + chunks
                    invoice_data = _mistral_parse(chunks)
                else:  # OpenRouter
                    img_arg = preview_url if (isinstance(preview_url, str) and preview_url.startswith("data:image")) else None
                    invoice_data = _openrouter_parse(prompt, img_arg)
            except Exception as llm_err:
                app.logger.exception(f"LLM extraction failed for {filename}: {llm_err}")
                errors.append(f"LLM extraction failed for {filename}: {str(llm_err)}")
                invoice_data = None
            
            # Validate and clean the extracted data
            if not isinstance(invoice_data, dict):
                raise ValueError("Invalid data structure returned from LLM")
            
            # Clean numeric fields
            numeric_fields = ['subtotal', 'tax_amount', 'discount_amount', 'total_amount']
            for field in numeric_fields:
                if field in invoice_data:
                    try:
                        invoice_data[field] = float(invoice_data[field]) if invoice_data[field] is not None else 0.0
                    except (ValueError, TypeError):
                        invoice_data[field] = 0.0
            
            # Clean line items
            if 'line_items' in invoice_data and isinstance(invoice_data['line_items'], list):
                cleaned_items = []
                for item in invoice_data['line_items']:
                    if isinstance(item, dict):
                        # Clean numeric fields in line items
                        item_numeric_fields = ['quantity', 'unit_price', 'total_price', 'tax_rate']
                        for field in item_numeric_fields:
                            if field in item:
                                try:
                                    item[field] = float(item[field]) if item[field] is not None else 0.0
                                except (ValueError, TypeError):
                                    item[field] = 0.0
                        cleaned_items.append(item)
                invoice_data['line_items'] = cleaned_items
            
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
    
    # Calculate summary statistics
    total_line_items = sum(len(inv.get('line_items', [])) for inv in all_invoices)
    total_amount = sum(inv.get('total_amount', 0) for inv in all_invoices)
    
    # Store file paths in session for download
    session['temp_files'] = temp_file_paths
    
    result = {
        'success': True,
        'invoices': all_invoices,
        'csv_files': csv_files,
        'stats': {
            'total_invoices': len(all_invoices),
            'total_line_items': total_line_items,
            'total_amount': total_amount,
            'average_amount': total_amount / len(all_invoices) if all_invoices else 0
        },
        'errors': errors
    }
    
    # Schedule cleanup of temp previews once response is sent
    try:
        # Note: Simple immediate cleanup after building response could race with client loading preview.
        # We delay cleanup slightly using a background thread.
        import threading, time
        temp_preview_files = []
        try:
            temp_preview_files = [os.path.join(UPLOADS_TMP, inv.get('source_file', '')) for inv in all_invoices if inv.get('source_file')]
        except Exception:
            temp_preview_files = []

        def delayed_cleanup(paths, delay=120):
            time.sleep(delay)
            for p in paths:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    app.logger.warning(f"Failed to remove temp preview {p}: {e}")

        threading.Thread(target=delayed_cleanup, args=(temp_preview_files,), daemon=True).start()
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
