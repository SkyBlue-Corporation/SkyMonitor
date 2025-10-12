# 🌐 SkyMonitor

[![Status](https://img.shields.io/badge/status-dev--work-informational)](https://github.com/Claude7776/SkyMonitor)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Repo size](https://img.shields.io/github/repo-size/Claude7776/SkyMonitor)](https://github.com/Claude7776/SkyMonitor)

**SkyMonitor** est une application de **supervision réseau et serveur** développée en Python (Flask) avec une interface web simple et un script de collecte de métriques système.  
Ce projet vise à fournir un **tableau de bord léger** pour visualiser l’état du réseau local et des serveurs, intégré dans une démarche DevOps (containerisation, automatisation, CI/CD).

---

## ⚙️ Fonctionnalités

- Scan réseau automatique (adresses IP locales) — extensible vers `nmap`/`ping`
- Collecte de métriques système (Uptime, CPU, RAM)
- Dashboard web en Flask affichant l’état des machines
- Architecture modulaire prête à être dockerisée
- Code simple, documenté et évolutif (prêt pour CI/CD)

---

## 🧩 Structure du projet

SkyMonitor/
│
├── app/
│ ├── init.py # Initialisation de Flask
│ ├── routes.py # Routes principales du tableau de bord
│ ├── utils.py # Fonctions de scan et de collecte système
│ └── templates/
│ └── index.html # Interface web principale
│
├── scripts/
│ └── network_scan.py # Scan du réseau et envoi des données
│
├── static/
│ └── style.css # Feuille de style du dashboard
│
├── run.py # Point d'entrée de l'application
├── requirements.txt # Dépendances Python
└── README.md # Documentation

