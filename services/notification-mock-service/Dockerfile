FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NOTIFICATION_DB=/data/notification.db
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app && mkdir -p /data && chown app:app /data
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py common.py ./
USER app
EXPOSE 8003
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=2)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
