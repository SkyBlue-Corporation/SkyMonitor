import socketio
import time
import random
from datetime import datetime

# Adresse de ton serveur Flask-SocketIO
SERVER_URL = "http://localhost:5000"  # Remplace par l'IP réelle si nécessaire

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Connecté au serveur Socket.IO")
    # Envoie un événement de test toutes les 2 secondes
    for i in range(5):
        metrics = {
            "cpu_percent": round(random.uniform(10, 90), 2),
            "memory_percent": round(random.uniform(20, 80), 2),
            "disk_percent": round(random.uniform(30, 70), 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        print(f"📊 Envoi system_metrics: {metrics}")
        sio.emit("system_metrics", metrics)
        time.sleep(2)

    # Simule un scan réseau terminé
    scan_result = {
        "success": True,
        "summary": {
            "results": [
                {"ip": "10.236.155.12", "ports": [{"port": 22, "state": "open"}, {"port": 80, "state": "closed"}]},
                {"ip": "10.236.155.15", "ports": [{"port": 443, "state": "open"}]}
            ]
        }
    }
    print("🔍 Envoi network_scan_complete")
    sio.emit("network_scan_complete", scan_result)

@sio.event
def disconnect():
    print("❌ Déconnecté du serveur")

try:
    sio.connect(SERVER_URL)
    sio.wait()
except Exception as e:
    print(f"Erreur de connexion : {e}")
