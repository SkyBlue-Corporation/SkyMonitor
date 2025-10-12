# 🌐 SkyMonitor

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-Framework-black?logo=flask)
![DevOps](https://img.shields.io/badge/DevOps-Monitoring-orange?logo=docker)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-green)
![Made by Claude](https://img.shields.io/badge/Made%20with%20❤️%20by-Claude%20Médine%20GAMBIGHA-red)

---

## 🧠 Présentation

**SkyMonitor** est une application de **supervision réseau et serveur** développée en Python avec le framework Flask.  
Elle fournit une interface web simple pour visualiser en temps réel l’état du réseau local et des serveurs, tout en intégrant des scripts d’automatisation pour la collecte de métriques et le monitoring.

---

## ⚙️ Fonctionnalités

- **Scan réseau automatique** : détection des adresses IP locales et état des hôtes.
- **Collecte de données système** : CPU, RAM, uptime et utilisation disque.
- **Dashboard web en temps réel** : interface légère et responsive avec Flask.
- **Architecture modulaire** : code organisé pour faciliter l’évolution et la dockerisation.
- **Extensible** : possibilité d’ajouter de nouvelles fonctionnalités DevOps.

---

## 🧩 Structure du projet

```text
SkyMonitor/
│
├── app/
│   ├── __init__.py         # Initialisation de l'application Flask
│   ├── models.py           # Définition des modèles de données
│   ├── routes.py           # Définition des routes web
│   ├── services/           # Services et modules métier
│   ├── static/             # Fichiers CSS, JS et assets
│   └── templates/          # Templates HTML pour le dashboard
│
├── instance/
│   └── monitoring.db       # Base de données SQLite
│
├── scripts/
│   ├── config.py           # Configuration des scripts
│   ├── run.py              # Script principal de lancement
│   ├── scanner.py          # Script de scan réseau
│   └── start.py            # Script de démarrage automatique
│
├── requirements.txt        # Dépendances Python
└── README.md               # Documentation du projet

## 🚀 Installation

### Prérequis

- Python 3.12+
- pip
- (Optionnel) Docker pour containerisation

### Étapes

1. **Cloner le dépôt :**

```bash
git clone https://github.com/Claude7776/SkyMonitor.git
cd SkyMonitor
```
---------

### Créer un environnement virtuel

```bash
python -m venv venv
# Sur Linux / Mac
source venv/bin/activate
# Sur Windows
venv\Scripts\activate
```
----------------
### Installation

```bash
pip install -r requirements.txt
```

### Lancement d'application

```bash
python scripts/run.py
```

**Le dashboard sera accessible à l'adresse : http://localhost:5000**

## 📸 Captures d'écran

### Dashboard principal
![Dashboard SkyMonitor](/monitoring-app/app/static/images/dashboard.png)

### Scan réseau en cours
![Parametre](/monitoring-app/app/static/images/parametre.png)
