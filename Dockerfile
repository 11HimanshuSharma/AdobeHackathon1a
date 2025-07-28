FROM --platform=linux/amd64 python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PyMuPDF
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python processing scripts
COPY process_pdfs.py .
COPY improved_extractor.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Set the default command to run the main processing script
CMD ["python", "process_pdfs.py"] 