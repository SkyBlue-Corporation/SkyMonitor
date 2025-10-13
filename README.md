# 🚀 SkyMonitor - Network Monitoring Platform

![Status](https://img.shields.io/badge/status-in%20testing-yellow?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&style=flat-square)
![Flask](https://img.shields.io/badge/Flask-2.3+-black?logo=flask&style=flat-square)
![Grafana](https://img.shields.io/badge/Grafana-Configured-orange?logo=grafana&style=flat-square)
![InfluxDB](https://img.shields.io/badge/InfluxDB-2.x-success?logo=influxdb&style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

---

## 🌐 Description

**SkyMonitor** est une plateforme moderne de **supervision réseau** permettant de visualiser et d’analyser les métriques système en temps réel.  
Développée avec une architecture conteneurisée basée sur **Flask**, **InfluxDB**, **Grafana** et **Docker Compose**, elle offre une solution prête à déployer pour le monitoring d’infrastructure.

---

## ✨ Fonctionnalités principales

| Fonctionnalité | Description |
|----------------|-------------|
| 🧭 **Interface SPA** | Navigation fluide entre les pages grâce à Flask |
| 📡 **Monitoring temps réel** | Suivi en direct des métriques système |
| 🔍 **Scan réseau** | Détection automatique et sécurisée des appareils connectés |
| 🗃️ **Stockage InfluxDB** | Base de données chronologique pour les métriques |
| 📊 **Dashboards Grafana** | Visualisations dynamiques et personnalisées |
| ⚙️ **API REST** | Endpoints RESTful pour l’intégration avec d’autres services |

---

## 🧩 Stack Technique

| Technologie | Rôle |
|--------------|------|
| 🐍 **Flask (Python)** | Interface web et API REST |
| 🧠 **InfluxDB** | Stockage des métriques |
| 📈 **Grafana** | Visualisation et tableaux de bord |
| 🐳 **Docker & Compose** | Orchestration et conteneurisation des services |

---

## 🛠️ Installation & Déploiement

### 1️⃣ Cloner le dépôt
```bash
git clone https://github.com/Claude7776/SkyMonitor.git
cd SkyMonitor
chmod +x deploy.sh
./deploys.sh
```

## Structure avant l'Execution du Script ./deploy.sh

monitoring-app/
├── 📄 app.py                          # Application Flask principale
├── 📄 requirements.txt                # Dépendances Python
├── 📄 Dockerfile                      # Configuration Docker
├── 📄 docker-compose.yml              # Orchestration des services
├── 📄 deploy.sh                       # Script de déploiement
├── 📄 README.md                       # Documentation
├── 📁 grafana/
│   ├── 📁 provisioning/
│   │   ├── 📁 dashboards/
│   │   │   └── 📄 dashboards.yml      # Configuration des dashboards
│   │   └── 📁 datasources/
│   │       └── 📄 influxdb.yml        # Source de données InfluxDB
├── 📁 influxdb/
│   └── 📄 init.iql                    # Script d'initialisation (optionnel)
├── 📁 templates/                      # Templates HTML
│   ├── 📄 base.html                   # Template de base avec navigation
│   ├── 📄 index.html                  # Page d'accueil
│   ├── 📄 dashboard.html              # Tableau de bord
│   ├── 📄 serveurs.html               # Page des serveurs
│   ├── 📄 postes.html                 # Page des postes
│   ├── 📄 conteneurs.html             # Page des conteneurs
│   ├── 📄 metriques.html              # Page des métriques
│   ├── 📄 parametres.html             # Page des paramètres
│   └── 📄 nav.html                    # Navigation (inclus dans base.html)
└── 📁 static/                         # Fichiers statiques
    ├── 📁 css/
    │   └── 📄 style.css               # Styles CSS communs
    ├── 📁 js/
    │   ├── 📄 router.js               # Système de routing SPA
    │   ├── 📄 app.js                  # Logique JavaScript principale
    │   └── 📄 charts.js               # Graphiques (optionnel)
    └── 📁 images/
        └── 📄 logo.png                # Logo (optionnel)