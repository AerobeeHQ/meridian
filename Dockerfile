# Codex - Adobe Analytics Configuration Viewer
FROM python:3.13-slim

WORKDIR /app

# Install build tools for pip package compilation
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY exports/ exports/
COPY config.json config.json

# Create directories
RUN mkdir -p cache exports

# Expose port
EXPOSE 5010

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5010"]
