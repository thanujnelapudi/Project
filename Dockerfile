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

# Copy requirements first
COPY requirements.txt .

# 1. Install CPU-ONLY versions of Torch and Paddle (Saves ~4GB of space)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# 2. Install the rest of the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# Environment variables for production
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Expose port and start
EXPOSE 5000
CMD ["python", "app.py"]
