# Dockerfile - version améliorée
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Installer utilitaires système (nmap + outils réseau)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      nmap \
      iproute2 \
      iputils-ping \
      net-tools \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer dépendances Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copier le code (après installation des dépendances pour cache Docker)
COPY . /app

# Créer dossier logs et un user non-root
RUN mkdir -p /app/logs && \
    groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app /app/logs

# Expose (utile pour doc)
EXPOSE 5000

# Utiliser un entrypoint pour initialisation (voir entrypoint.sh)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Lancer en tant qu'utilisateur non-root
USER appuser

ENTRYPOINT ["/entrypoint.sh"]
# Par défaut lance gunicorn ; si tu utilises SocketIO, utiliser eventlet/gevent
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
