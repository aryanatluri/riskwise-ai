FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app

RUN useradd --create-home --uid 10001 riskwise
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
RUN mkdir -p /app/data/uploads && chown -R riskwise /app/data
USER riskwise

# Cloud Run sets $PORT. Migrations run as a separate step (see README), not on every boot.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
