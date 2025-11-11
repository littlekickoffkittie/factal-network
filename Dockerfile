# Multi-stage Dockerfile for FractalChain
# Optimized for production with security enhancements

# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash fractalchain

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/fractalchain/.local

# Copy application code
COPY --chown=fractalchain:fractalchain . .

# Create data directories with proper permissions
RUN mkdir -p /home/fractalchain/.fractalchain/mainnet && \
    chown -R fractalchain:fractalchain /home/fractalchain/.fractalchain

# Switch to non-root user
USER fractalchain

# Add local Python packages to PATH
ENV PATH=/home/fractalchain/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose ports
# 8333: P2P network
# 8545: JSON-RPC API
# 8080: Web explorer
EXPOSE 8333 8545 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8545', timeout=5)" || exit 1

# Volume for blockchain data
VOLUME ["/home/fractalchain/.fractalchain"]

# Run node
CMD ["python3", "main.py"]
