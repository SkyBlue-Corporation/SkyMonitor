# app.py (intégré avec net_discovery_nmap)
import os
import time
from datetime import datetime
from typing import List, Optional

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO
import psutil
import logging

# ----------------------------------------
# Initialisation Flask + logs
# ----------------------------------------
app = Flask(__name__)

# Dossier de logs
os.makedirs("logs", exist_ok=True)

# Configuration du logger
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# ---- try to import optional dependencies ----
try:
    import influxdb_client
    from influxdb_client.client.write_api import SYNCHRONOUS
except Exception:
    influxdb_client = None
    SYNCHRONOUS = None

try:
    import docker
except Exception:
    docker = None

# try import your net discovery module (may be in same dir)
try:
    from net_discovery_nmap import discover_and_scan, parse_ports
    NET_DISCOVERY_AVAILABLE = True
except Exception:
    # If module not present, keep a fallback so app still imports
    discover_and_scan = None
    parse_ports = None
    NET_DISCOVERY_AVAILABLE = False

# ---- Flask + SocketIO ----
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-key')
if os.environ.get('ENV') == 'production':
    socketio = SocketIO(app, cors_allowed_origins="*")  # utilisera Eventlet/Gevent si installés
else:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')  # dev/tests

# ---- InfluxDB client (optional) ----
INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', '')

if influxdb_client and INFLUXDB_TOKEN and INFLUXDB_BUCKET and INFLUXDB_ORG:
    try:
        influx_client = influxdb_client.InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    except Exception:
        influx_client = None
        write_api = None
else:
    influx_client = None
    write_api = None

# ---- Docker client (optional) ----
if docker:
    try:
        docker_client = docker.from_env()
    except Exception:
        docker_client = None
else:
    docker_client = None

# ---- Expose a global "nm" for tests that may patch nmap.PortScanner if needed ----
try:
    import nmap as _nmap
    nm = getattr(_nmap, "PortScanner", None)
except Exception:
    nm = None

# ------------------ Utility: write_metrics ------------------
def write_metrics(measurement: str, fields: dict, tags: Optional[dict] = None):
    """
    Écrit un point dans InfluxDB si write_api disponible.
    Sinon, loggue sur stdout (pratique pour dev / tests).
    """
    if not write_api or not influxdb_client:
        print(f"[METRICS-SKIP] {measurement} | fields={fields} | tags={tags}")
        return

    try:
        point = influxdb_client.Point(measurement)
        if tags:
            for k, v in tags.items():
                point = point.tag(k, v)
        for k, v in fields.items():
            point = point.field(k, v)
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    except Exception as e:
        print(f"[METRICS-ERROR] {e}")

# ------------------ System metrics collector (background) ------------------
def collect_system_metrics():
    """Boucle infinie — démarre en background only when running server."""
    while True:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()

            fields = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "network_sent_mb": net.bytes_sent / (1024**2),
                "network_recv_mb": net.bytes_recv / (1024**2)
            }

            # example tag
            tags = {"host": os.environ.get("HOSTNAME", "monitoring-server")}

            write_metrics("system_metrics", fields, tags)
            socketio.emit("system_metrics", {**fields, "timestamp": datetime.now().isoformat()})
            time.sleep(5)
        except Exception as e:
            print(f"[collect_system_metrics] {e}")
            time.sleep(10)

# ------------------ Docker metrics collector (background) ------------------
def collect_docker_metrics(run_once=False):
    try:
        while True:
            containers = docker_client.containers.list()
            for c in containers:
                stats = c.stats(stream=False)
                cpu_percent = 0.0
                mem_percent = 0.0

                if stats.get("cpu_stats") and stats.get("precpu_stats"):
                    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                    sys_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
                    if sys_delta > 0:
                        cpu_percent = (cpu_delta / sys_delta) * 100

                if stats.get("memory_stats"):
                    mem = stats["memory_stats"]
                    if mem.get("usage") and mem.get("limit"):
                        mem_percent = (mem["usage"] / mem["limit"]) * 100

                write_metrics(c.name, cpu_percent, mem_percent)
                socketio.emit("docker_metrics", {"container": c.name, "cpu": cpu_percent, "memory": mem_percent})

            if run_once:
                break
            time.sleep(5)
    except Exception as e:
        print(f"Erreur Docker: {e}")
# ------------------ Network scan integration ------------------
def background_discover_and_emit(network: str, ports: List[int], parallel_hosts: int = 8, scan_args: str = "-sT -sV", ping_args: Optional[str] = None):
    """
    Lancer discover_and_scan (bloquant) en background puis:
      - écrire sommaire dans Influx si souhaité
      - émettre via SocketIO vers clients
    """
    if not NET_DISCOVERY_AVAILABLE:
        msg = "net_discovery_nmap module not available"
        print(f"[background_discover_and_emit] {msg}")
        socketio.emit("network_scan_complete", {"success": False, "error": msg, "scan_time": datetime.now().isoformat()})
        return

    try:
        summary = discover_and_scan(network=network, ports=ports, parallel_hosts=parallel_hosts, scan_args=scan_args, ping_args=ping_args)
    except Exception as e:
        print(f"[background_discover_and_emit] discover_and_scan error: {e}")
        socketio.emit("network_scan_complete", {"success": False, "error": str(e), "scan_time": datetime.now().isoformat()})
        return

    # Optionnel: écrire un point par hôte (ex: open_ports count)
    for host in summary.get("results", []):
        ip = host.get("ip")
        ports_info = host.get("ports", []) or []
        open_count = sum(1 for p in ports_info if p.get("state") == "open" or p.get("open", False))
        write_metrics("network_scan_host", {"open_ports": open_count}, {"ip": ip})

    # Émettre le résumé
    socketio.emit("network_scan_complete", {"success": True, "summary": summary, "scan_time": datetime.now().isoformat()})

# ------------------ Routes API ------------------
@app.route("/api/system/stats")
def system_stats():
    """Retourne les statistiques système en JSON de façon sûre"""
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

@app.route("/api/scan/network", methods=["POST"])
def api_scan_network():
    """
    Lance le scan en background et répond immédiatement (202 Accepted).
    Payload JSON attendu (optionnel): { "network": "...", "ports": "22,80", "parallel": 8, "scan_args": "...", "ping_args": "..." }
    """
    try:
        payload = request.json or {}
        network = payload.get("network", os.environ.get("NETWORK_CIDR", "10.236.155.0/24"))
        ports_str = payload.get("ports", payload.get("ports_str", "22,80,443"))
        ports = parse_ports(ports_str) if parse_ports else [22, 80, 443]
        parallel = int(payload.get("parallel", 8))
        scan_args = payload.get("scan_args", "-sT -sV")
        ping_args = payload.get("ping_args", None)

        # start background job
        socketio.start_background_task(background_discover_and_emit, network, ports, parallel, scan_args, ping_args)

        return jsonify({"success": True, "message": "Scan launched"}), 202
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------ SPA and static ------------------
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

# ------------------ WebSocket handlers ------------------
@socketio.on("connect")
def handle_connect():
    print("[socket] client connected")
    socketio.emit("connected", {"status": "connected"})

@socketio.on("disconnect")
def handle_disconnect():
    print("[socket] client disconnected")

# ------------------ Expose useful names for tests ------------------
# Tests can patch these globals: write_api, docker_client, discover_and_scan, parse_ports, nm
__all__ = [
    "app", "socketio", "write_api", "write_metrics", "docker_client",
    "discover_and_scan", "parse_ports", "nm", "background_discover_and_emit",
    "collect_system_metrics", "collect_docker_metrics"
]

# ------------------ Run server (only when executed directly) ------------------
if __name__ == "__main__":
    # start background collectors if desired
    socketio.start_background_task(collect_system_metrics)
    socketio.start_background_task(collect_docker_metrics)
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
