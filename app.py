from typing import List, Optional
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO
import psutil
import logging
import os
from services.aletre_telegram import send_telegram_alert

# --- Initialisation Flask + logs ---
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-key')
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- SocketIO ---
if os.environ.get('ENV') == 'production':
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
else:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- InfluxDB ---
try:
    import influxdb_client
    from influxdb_client.client.write_api import SYNCHRONOUS
except Exception:
    influxdb_client = None
    SYNCHRONOUS = None

from dotenv import load_dotenv
import os
from datetime import datetime
from influxdb_client import Point

load_dotenv()

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', '')

# Vérification des variables
if not all([INFLUXDB_TOKEN, INFLUXDB_BUCKET, INFLUXDB_ORG]):
    raise ValueError("⚠️ Vérifie que TOKEN, BUCKET et ORG sont bien définis !")

# Initialisation du client
if influxdb_client:
    try:
        influx_client = influxdb_client.InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        print("✅ Connexion à InfluxDB réussie !")
    except Exception as e:
        influx_client = None
        write_api = None
        print(f"❌ Erreur lors de l'initialisation du client : {e}")
else:
    influx_client = None
    write_api = None
    print("❌ influxdb_client non installé.")

# Test d'écriture
if write_api:
    point = Point("test_metric").tag("source", "sky_monitor").field("value", 42).time(datetime.utcnow())
    try:
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        print(f"✅ Point écrit dans le bucket '{INFLUXDB_BUCKET}' !")
        send_telegram_alert("✅ Nouveau point écrit dans InfluxDB: test_metric = 42")
    except Exception as e:
        print(f"❌ Erreur lors de l’écriture du point : {e}")

# Test de lecture
if influx_client:
    try:
        query_api = influx_client.query_api()
        query = f'from(bucket:"{INFLUXDB_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "test_metric")'
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        print(f"📊 Points récupérés dans le bucket '{INFLUXDB_BUCKET}':")
        for table in result:
            for record in table.records:
                print(f"  {record.get_time()} | {record.get_measurement()} | {record.get_field()} = {record.get_value()}")
    except Exception as e:
        print(f"❌ Erreur lors de la lecture : {e}")


# --- Docker ---
try:
    import docker
    docker_client = docker.from_env()
except Exception:
    docker_client = None

# --- Net Discovery ---
try:
    from net_discovery_nmap import discover_and_scan, parse_ports
    NET_DISCOVERY_AVAILABLE = True
except Exception:
    discover_and_scan = None
    parse_ports = None
    NET_DISCOVERY_AVAILABLE = False

# --- Services ---
from services.metrics import (
    collect_system_metrics,
    collect_docker_metrics,
    init_metrics,
    write_metrics
)
from services.network_scan import (
    background_discover_and_emit,
    init_network_scan
)

# --- Initialisation des modules ---
init_metrics(influx_client, write_api, INFLUXDB_BUCKET, socketio)
init_network_scan(write_metrics, socketio)

# --- Routes API ---
@app.route("/api/system/stats")
def system_stats():
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        net = psutil.net_io_counters()

        data = {
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_percent": disk,
            "net_bytes_sent": getattr(net, "bytes_sent", 0),
            "net_bytes_recv": getattr(net, "bytes_recv", 0),
        }

        logging.info(f"System stats collected: {data}")
        return jsonify(data), 200

    except Exception as e:
        error_msg = f"Error collecting system stats: {e}"
        logging.error(error_msg)
        return jsonify({
            "error": "Unable to collect system stats",
            "details": str(e)
        }), 500    

threshold = int(os.environ.get("ALERT_THRESHOLD", 80))
if cpu > threshold:
        send_telegram_alert(f"⚠️ CPU élevé: {cpu}%")
        if mem > threshold:
            send_telegram_alert(f"⚠️ Mémoire élevée: {mem}%")
            if disk > threshold:
                send_telegram_alert(f"⚠️ Disque presque plein: {disk}%")


@app.route("/api/scan/network", methods=["POST"])
def api_scan_network():
    try:
        payload = request.json or {}
        network = payload.get("network", os.environ.get("NETWORK_CIDR", "10.236.155.0/24"))
        ports_str = payload.get("ports", payload.get("ports_str", "22,80,443"))
        ports = parse_ports(ports_str) if parse_ports else [22, 80, 443]
        parallel = int(payload.get("parallel", 8))
        scan_args = payload.get("scan_args", "-sT -sV")
        ping_args = payload.get("ping_args", None)

        socketio.start_background_task(
            background_discover_and_emit, network, ports, parallel, scan_args, ping_args
        )

        return jsonify({"success": True, "message": "Scan launched"}), 202
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route("/test/socket")
def test_socket():
    return render_template("test_socket.html")


# --- SPA & Static ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "API endpoint not found"}), 404
    return render_template("index.html"), 200

# --- WebSocket ---
@socketio.on("connect")
def handle_connect():
    print("[socket] client connected")
    socketio.emit("connected", {"status": "connected"})

@socketio.on("disconnect")
def handle_disconnect():
    print("[socket] client disconnected")

# --- Run ---
if __name__ == "__main__":
    socketio.start_background_task(collect_system_metrics)
    socketio.start_background_task(collect_docker_metrics, docker_client)
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
