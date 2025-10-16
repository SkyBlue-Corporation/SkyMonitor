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
