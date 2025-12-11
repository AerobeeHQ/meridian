# Codex - Adobe Analytics Configuration Viewer
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p cache exports

# Expose port
EXPOSE 5010

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5010", "--workers", "2", "app:create_app()"]

