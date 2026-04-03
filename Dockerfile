# Build stage for caching models
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement file first to leverage docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# Environment variables for production
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV DATABASE_TYPE=sqlite
ENV DB_PATH=/app/database/app.sqlite
ENV TESSERACT_PATH=tesseract

# Pre-cache models so they are baked into the container
# This reduces first-run latency on Railway significantly
RUN python -c "from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer; \
    model_name = 'microsoft/trocr-base-handwritten'; \
    VisionEncoderDecoderModel.from_pretrained(model_name); \
    ViTImageProcessor.from_pretrained(model_name); \
    AutoTokenizer.from_pretrained(model_name)"

# Pre-cache PaddleOCR models (Simplified trigger)
# Note: PaddleOCR downloads to ~/.paddlex or ~/.paddleocr by default
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en')"

# Expose port and start
EXPOSE 5000
CMD ["python", "app.py"]
