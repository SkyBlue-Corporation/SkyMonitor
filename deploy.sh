#!/bin/bash

echo "🚀 Déploiement de l'application de monitoring..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

echo "📦 Construction des images..."
docker-compose build

echo "🛑 Arrêt des services existants..."
docker-compose down

echo "🎯 Démarrage des services..."
docker-compose up -d

echo "⏳ Attente du démarrage..."
sleep 20

echo "🔍 Vérification du statut..."
docker-compose ps

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "🌐 URLs d'accès:"
echo "   - Application: http://localhost:5000"
echo "   - Grafana:    http://localhost:3000"
echo "   - InfluxDB:   http://localhost:8086"
echo ""
echo "🔑 Identifiants:"
echo "   Grafana: admin / admin123"
echo "   InfluxDB: admin / admin123"
