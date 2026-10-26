FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app --no-create-home app \
    && mkdir -p /data \
    && chown app:app /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--access-logfile", "-"]
