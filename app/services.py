import os
import json
import base64
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.utils import secure_filename
from flask import current_app as app

from ocr_processing import ocr_pdf, ocr_image
from llm_wrappers import _mistral_parse, _openrouter_parse, _create_invoice_extraction_prompt


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_upload_and_preview(file_storage) -> Tuple[str, str]:
    """
    Save the uploaded file to UPLOAD_FOLDER and a preview copy to uploads_tmp.
    Returns (file_path, temp_public_path).
    """
    filename = secure_filename(file_storage.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    uploads_tmp = 'uploads_tmp'
    os.makedirs(uploads_tmp, exist_ok=True)
    temp_public_path = os.path.join(uploads_tmp, filename)

    file_storage.save(file_path)
    try:
        # Also save a temp public copy for UI preview
        file_storage.stream.seek(0)
    except Exception:
        pass
    try:
        with open(temp_public_path, 'wb') as ftmp:
            file_storage.stream.seek(0)
            ftmp.write(file_storage.read())
    except Exception:
        # If stream seek/read fails (already consumed), copy from saved file_path
        import shutil
        shutil.copyfile(file_path, temp_public_path)

    return file_path, temp_public_path


def run_ocr(file_path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Run OCR based on file extension. Returns (metadata_dict, preview_url_or_data_url)
    """
    if file_path.lower().endswith('.pdf'):
        md, preview_url = ocr_pdf(file_path)
    else:
        md, preview_url = ocr_image(file_path)
    return md, preview_url


def persist_preview_to_public(preview_url: Optional[str], filename: str, file_path: str) -> Optional[str]:
    """
    Persist a reliable preview image under /public/previews for browser display.
    Returns a public URL if created, otherwise None.
    """
    try:
        os.makedirs(os.path.join(app.static_folder, 'previews'), exist_ok=True)
        saved_preview_path = None
        if isinstance(preview_url, str) and preview_url.startswith('data:image'):
            # data URL -> save to file
            m = re.match(r'data:image/(png|jpeg|jpg);base64,(.*)', preview_url)
            ext = m.group(1) if m else 'png'
            b64 = m.group(2) if m else preview_url.split(',', 1)[-1]
            data = base64.b64decode(b64)
            safe_base = os.path.splitext(os.path.basename(filename))[0]
            saved_preview_path = os.path.join(app.static_folder, 'previews', f'{safe_base}.preview.{ext}')
            with open(saved_preview_path, 'wb') as out:
                out.write(data)
        else:
            # If original is an image and still exists, copy as preview
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and os.path.exists(file_path):
                import shutil
                safe_base = os.path.splitext(os.path.basename(filename))[0]
                ext = os.path.splitext(filename)[1].lstrip('.').lower() or 'png'
                saved_preview_path = os.path.join(app.static_folder, 'previews', f'{safe_base}.preview.{ext}')
                shutil.copyfile(file_path, saved_preview_path)
        if saved_preview_path and os.path.exists(saved_preview_path):
            return '/public/previews/' + os.path.basename(saved_preview_path)
        return preview_url if (isinstance(preview_url, str) and preview_url.startswith('data:image')) else None
    except Exception:
        return None


def clean_invoice_numbers(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean numeric fields at root and within line items to be floats, defaulting to 0.0 when invalid.
    """
    numeric_fields = ['subtotal', 'tax_amount', 'discount_amount', 'total_amount']
    for field in numeric_fields:
        if field in invoice_data:
            try:
                invoice_data[field] = float(invoice_data[field]) if invoice_data[field] is not None else 0.0
            except (ValueError, TypeError):
                invoice_data[field] = 0.0

    if 'line_items' in invoice_data and isinstance(invoice_data['line_items'], list):
        cleaned_items = []
        for item in invoice_data['line_items']:
            if isinstance(item, dict):
                item_numeric_fields = ['quantity', 'unit_price', 'total_price', 'tax_rate']
                for field in item_numeric_fields:
                    if field in item:
                        try:
                            item[field] = float(item[field]) if item[field] is not None else 0.0
                        except (ValueError, TypeError):
                            item[field] = 0.0
                cleaned_items.append(item)
        invoice_data['line_items'] = cleaned_items
    return invoice_data


def extract_with_llm(md: Dict[str, Any], preview_url: Optional[str], llm_choice: str) -> Optional[Dict[str, Any]]:
    """
    Build prompt and call the selected LLM parser. Returns a dict or None on failure.
    """
    prompt = _create_invoice_extraction_prompt(md)
    invoice_data = None
    try:
        if llm_choice == 'Mistral':
            from mistralai import TextChunk, ImageURLChunk
            chunks = [TextChunk(text=prompt)]
            if preview_url and isinstance(preview_url, str) and preview_url.startswith("data:image"):
                chunks = [ImageURLChunk(image_url=preview_url)] + chunks
            invoice_data = _mistral_parse(chunks)
        else:
            img_arg = preview_url if (isinstance(preview_url, str) and preview_url.startswith("data:image")) else None
            invoice_data = _openrouter_parse(prompt, img_arg)
    except Exception:
        invoice_data = None
    return invoice_data


def build_result_payload(invoices: List[Dict[str, Any]], errors: List[str]) -> Dict[str, Any]:
    total_line_items = sum(len(inv.get('line_items', [])) for inv in invoices)
    total_amount = sum(inv.get('total_amount', 0) for inv in invoices)
    return {
        'success': True,
        'invoices': invoices,
        'csv_files': {},  # to be filled by CSV layer in app
        'stats': {
            'total_invoices': len(invoices),
            'total_line_items': total_line_items,
            'total_amount': total_amount,
            'average_amount': total_amount / len(invoices) if invoices else 0
        },
        'errors': errors
    }


def delayed_cleanup_temp_previews(all_invoices: List[Dict[str, Any]], delay_seconds: int = 120):
    """
    Remove uploads_tmp previews after a delay to avoid racing with client rendering.
    """
    import threading, time

    uploads_tmp = 'uploads_tmp'
    try:
        temp_preview_files = [os.path.join(uploads_tmp, inv.get('source_file', '')) for inv in all_invoices if inv.get('source_file')]
    except Exception:
        temp_preview_files = []

    def delayed_cleanup(paths, delay=120):
        time.sleep(delay)
        for p in paths:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    threading.Thread(target=delayed_cleanup, args=(temp_preview_files, delay_seconds), daemon=True).start()
