# Utiliser une image officielle Python
FROM python:3.12-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers de dépendances et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le contenu du projet dans le conteneur
COPY . .

# Exposer le port sur lequel Flask tournera
EXPOSE 5000

# Définir la variable d'environnement pour Flask
ENV FLASK_APP=scripts/run.py
ENV FLASK_ENV=production

# Lancer l'application
CMD ["python", "scripts/run.py"]