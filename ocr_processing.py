import base64
import mimetypes
import os
from mistralai import Mistral, DocumentURLChunk, ImageURLChunk
from mistralai.models import OCRResponse
from config import Config

# Initialize Mistral client
mistral_client = Mistral(api_key=Config.MISTRAL_API_KEY) if Config.MISTRAL_API_KEY else None

def _merge_md(resp: OCRResponse) -> str:
    """Merge markdown pages from OCR response"""
    md_pages = []
    for p in resp.pages:
        imgs = {i.id: i.image_base64 for i in p.images}
        md = p.markdown
        for iid, b64 in imgs.items():
            md = md.replace(f"![{iid}]({iid})", f"![{iid}]({b64})")
        md_pages.append(md)
    return "\n\n".join(md_pages)

def ocr_pdf(path: str) -> tuple[str, str]:
    """Process PDF file with OCR and return merged markdown and data URL"""
    if not mistral_client:
        raise RuntimeError("Mistral API key not configured")
    
    with open(path, "rb") as f: 
        data = f.read()
    b64 = base64.b64encode(data).decode()
    url = f"data:application/pdf;base64,{b64}"
    
    resp = mistral_client.ocr.process(
        document=DocumentURLChunk(document_url=url),
        model=Config.OCR_MODEL,
        include_image_base64=False,
    )
    return (_merge_md(resp), url)

def ocr_image(uploaded_file_or_path) -> tuple[str, str]:
    """Process image file with OCR and return merged markdown and data URL.
    Accepts either a Werkzeug file-like object OR a filesystem path string.
    """
    if not mistral_client:
        raise RuntimeError("Mistral API key not configured")

    # Determine if we received a path (str) or a file-like object
    if isinstance(uploaded_file_or_path, str):
        # Treat as filesystem path
        path = uploaded_file_or_path
        with open(path, "rb") as f:
            data = f.read()
        filename = os.path.basename(path)
    else:
        # Treat as file-like object from Flask
        fobj = uploaded_file_or_path
        data = fobj.read()
        try:
            fobj.seek(0)
        except Exception:
            pass
        filename = getattr(fobj, "filename", "image.jpg")

    b64 = base64.b64encode(data).decode()
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
    url = f"data:{mime};base64,{b64}"

    resp = mistral_client.ocr.process(
        document=ImageURLChunk(image_url=url),
        model=Config.OCR_MODEL,
        include_image_base64=False,
    )
    return (_merge_md(resp), url)
