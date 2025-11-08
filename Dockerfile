FROM python:3.11-slim

WORKDIR /app

# Install Tesseract
RUN apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-eng && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 10000

CMD gunicorn server:app --bind 0.0.0.0:$PORT
