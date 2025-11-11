# Dockerfile for FractalChain

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install FractalChain
RUN pip install -e .

# Create data directory
RUN mkdir -p /root/.fractalchain

# Expose ports
EXPOSE 8333 8545 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run node
CMD ["python3", "main.py"]
