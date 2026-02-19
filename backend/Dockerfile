# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create necessary directories
RUN mkdir -p sessions/archive knowledge storage memory/logs

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
