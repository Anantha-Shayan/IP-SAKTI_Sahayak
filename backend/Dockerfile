FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal build deps for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest and install
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

ENV API_HOST=0.0.0.0
ENV API_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "backend.api.main"]
