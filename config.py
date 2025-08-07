import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    # LLM Settings
    DEFAULT_MODEL = "pixtral-12b-latest"
    OPENROUTER_MODEL = "google/gemini-flash-1.5"
    OCR_MODEL = "mistral-ocr-latest"