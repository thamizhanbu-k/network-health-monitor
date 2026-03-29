# Stage 1: Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim
WORKDIR /app

# Install the Linux tool that contains the 'free' command
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Create non-root user (security best practice)
RUN useradd -m -u 1001 appuser
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# Run application
CMD ["python", "-m", "flask", "--app", "app.main", "run", "--host=0.0.0.0", "--port=5000"]