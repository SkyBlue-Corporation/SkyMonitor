# Dockerfile
FROM python:3.9-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    iputils-ping \
    net-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs /app/data

# Exposer le port de l'application
EXPOSE 5000

# Variables d'environnement par défaut
ENV FLASK_APP=run.py \
    FLASK_ENV=production \
    INFLUXDB_URL=http://influxdb:8086 \
    INFLUXDB_TOKEN=your-admin-token-here \
    INFLUXDB_ORG=skywatch \
    INFLUXDB_BUCKET=network_monitoring

# Commande de démarrage
CMD ["python", "start.py"]

CMD [ "python", "run.py"]