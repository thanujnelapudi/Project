FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
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
ENV PYTHONUNBUFFERED=1

# Expose port and start
EXPOSE 5000
CMD ["python", "app.py"]
