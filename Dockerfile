# Backend Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for auto-review features
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    sqlalchemy \
    requests

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /data/tokenizers /data/repos /data/db /data/state

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PR_AGENT_DATA_DIR=/data

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "pr_agent.servers.web_platform"]
