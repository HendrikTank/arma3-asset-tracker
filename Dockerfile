FROM python:3.11-slim

# Set build arguments for production optimization
ARG FLASK_ENV=production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=${FLASK_ENV}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/reports /app/logs && \
    chmod -R 755 /app/reports /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

EXPOSE 5000

# Use waitress for production WSGI server with optimized settings
CMD ["waitress-serve", \
    "--host=0.0.0.0", \
    "--port=5000", \
    "--threads=4", \
    "--channel-timeout=60", \
    "--connection-limit=1000", \
    "--cleanup-interval=30", \
    "--log-untrusted-proxy-headers", \
    "wsgi:app"]