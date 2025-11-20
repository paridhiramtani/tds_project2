FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for Playwright and data tools
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    default-jre \
    ffmpeg \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to cache pip install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
