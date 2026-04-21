# Use the official slim Python image for a smaller footprint
FROM python:3.12-slim

# Prevent Python from writing obsolete .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install application dependencies FIRST for layer caching efficiency
COPY requirements.txt .

# Install pip requirements, Playwright Chromium, and system Chromium dependencies
# Done in a single RUN block, cleaning apt caches to minimize total image size
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache

# Copy application source code
COPY . .

# Enforce security best-practices: Run as non-root user
# Important for Serverless AWS (Fargate/ECS/AppRunner) deployments
RUN adduser --disabled-password --gecos "" scraperuser && \
    chown -R scraperuser:scraperuser /app

USER scraperuser

# Configuration mappings
EXPOSE 5000
ENV PORT=5000
ENV FLASK_DEBUG=false
ENV MAX_RETRIES=3
ENV SCRAPER_TIMEOUT=10

# Start via Gunicorn as a production-grade WSGI Server
# Note: 1 worker process is ideal to restrict memory usage. 
# Threading handles concurrent requests against the persistent Chromium instance.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "1", "--threads", "2"]
