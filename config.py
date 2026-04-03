import os
import secrets
import platform

SECRET_KEY = os.environ.get("SECRET_KEY", "postal-ocr-fixed-key-2024")

# 'oracle' or 'sqlite'
DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "sqlite")
DB_PATH = os.environ.get("DB_PATH", "database/app.sqlite")

DB_CONFIG = {
    "user": "system",
    "password": "Admin1234",
    "dsn": "localhost/XE"
}

# Tesseract path with Linux fallback
if platform.system() == "Windows":
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    TESSERACT_PATH = os.environ.get("TESSERACT_PATH", "tesseract")

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}