# Nutze ein schlankes Python-Image für geringere Build-Zeiten und Sicherheit
FROM python:3.11-slim

# Verhindert, dass Python .pyc-Dateien schreibt und puffert die Ausgabe (wichtig für Logs)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Arbeitsverzeichnis im Container
WORKDIR /app

# System-Abhängigkeiten installieren (falls nötig für einige Python-Pakete)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Den gesamten Projektcode in den Container kopieren
COPY . .

# Den PYTHONPATH setzen, damit 'app' als Modul erkannt wird
ENV PYTHONPATH=/app

# Standard-Port für Render (wird oft automatisch über die Umgebungsvariable PORT gesteuert)
EXPOSE 8000

# Startbefehl: Wir nutzen Uvicorn als ASGI-Server für FastAPI
# --proxy-headers ist wichtig für Render, damit HTTPS-Weiterleitungen korrekt erkannt werden
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
