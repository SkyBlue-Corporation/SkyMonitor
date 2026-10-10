#!/bin/bash

echo "🚀 Warning Déploiement de l'application de monitoring !!!"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

if [ ! -f .env ]; then
    echo "❌ Fichier .env manquant. Copiez .env.example vers .env et renseignez vos secrets avant de déployer."
    exit 1
fi

echo "📦 Construction des images..."
docker-compose build web

echo "🛑 Arrêt des services existants..."
docker-compose down --volumes --remove-orphans

echo "🎯 Démarrage des services..."
docker-compose up -d

echo "⏳ Attente du démarrage du service web..."
until curl -fsS http://localhost:5000 &> /dev/null; do
    echo "⏳ Web service pas encore prêt..."
    sleep 5
done

echo "🔍 Vérification du statut des containers..."
docker-compose ps

echo ""
echo "✅ Déploiement terminé !!!"
echo ""
echo "🌐 URLs d'accès:"
echo "   - Application: http://localhost:5000"
echo "   - Grafana:    http://localhost:3000"
echo "   - InfluxDB:   http://localhost:8086"
echo ""
echo "🔑 Identifiants: voir les valeurs définies dans votre fichier .env"
