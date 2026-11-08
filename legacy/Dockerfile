FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY demo_sample/ demo_sample/

ENV PYTHONPATH=/app/backend
EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
