# 🚀 SkyMonitor - Application de Monitoring

Application complète de monitoring avec **Flask**, **InfluxDB** et **Grafana**.

---

## 🛠️ Badges

![Docker Build](https://img.shields.io/docker/build/tondockerhub/sky-monitor?style=flat-square&logo=docker)
![Python Tests](https://img.shields.io/github/workflow/status/tongithub/sky-monitor/Python%20Tests?style=flat-square&logo=github)  
![Grype Scan](https://img.shields.io/badge/Grype-Secure-green?style=flat-square&logo=docker)

---

## ✨ Fonctionnalités

- ✅ **Interface SPA** - Navigation fluide entre les pages  
- ✅ **Monitoring temps réel** - Métriques système en direct  
- ✅ **Scan réseau** - Détection automatique des appareils  
- ✅ **Stockage InfluxDB** - Base de données chronologique  
- ✅ **Dashboards Grafana** - Visualisations avancées  
- ✅ **API REST** - Endpoints pour l'intégration  
- 🔒 **Sécurisation DevSecOps** - Scan d’image Docker avec Grype  

---

## 🛠️ Installation

```bash
# Déployer l'application
./deploy.sh

# Arrêter l'application
docker-compose down

# Voir les logs
docker-compose logs -f

## 🏗 Architecture du projet

```bash

monitoring-app/
├── app.py # Application Flask principale
├── requirements.txt  requirements-dev.txt # Dépendances Python & dépendance du test
├── Dockerfile # Configuration Docker
├── docker-compose.yml # Orchestration des services
├── deploy.sh # Script de déploiement automatisé
├── net_discovery_nmap.py # Module de détection réseau
├── test/ # Tests unitaires
│ └── test_net_discovery_nmap1.py
├── Makefile # Commandes automatiques (test, clean, lint)
├── grafana/ # Provisioning dashboards
└── influxdb/ # Données et configuration
```
## 🧪 Tests unitaires

**Exécution des tests :**

```bash
make test
pytest -v
```
**✅ Les tests sont automatisés pour le module net_discovery_nmap (détection d’hôtes et scan réseau).*

**💡 Astuce DevOps**

```bash
make clean #supprime les caches, fichiers temporaires et environnement virtuel

make reset # clean + recrée l’environnement virtuel
```
## 🔒 Sécurité DevSecOps

**L’image Docker est scannée avec Grype pour détecter les vulnérabilités :**

```bash
grype myapp:v1
```
```bash
| Niveau de sévérité | Nombre |
| ------------------ | ------ |
| 🔴 Critique        | 0      |
| 🟠 Haute           | 3      |
| 🟡 Moyenne         | 4      |
| 🟢 Faible          | 6      |
| ⚪ Négligeable      | 44     |
```

Correction du packages vulnérables  **gunicorn*, pour sécuriser l’image.

## 🧰 Technologies principales

**Backend : Flask (Python)**

**Base de données : InfluxDB**

**Visualisation : Grafana**

**Containerisation : Docker / Docker Compose**

**Sécurité : Grype (scan vulnérabilités)**

**Automatisation : Makefile, Bash, tests unitaires (pytest)**