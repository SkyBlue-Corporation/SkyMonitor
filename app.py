from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, logout_user, login_required
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import ipaddress
import psutil
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
from dotenv import load_dotenv

from models.user import users, get_user

# --- Chargement des variables ---
load_dotenv()

# --- Initialisation Flask + logs ---
app = Flask(__name__, static_folder='static', template_folder='templates')

_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    print(
        "⚠️  SECRET_KEY non défini : clé temporaire générée pour ce process. "
        "Définissez SECRET_KEY en production (les sessions ne survivront pas "
        "à un redémarrage ou à plusieurs workers sans ça)."
    )
app.config['SECRET_KEY'] = _secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'

os.makedirs("logs", exist_ok=True)

_log_handler = RotatingFileHandler("logs/app.log", maxBytes=5 * 1024 * 1024, backupCount=5)
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])

# --- SocketIO ---
_cors_origins = os.environ.get("SOCKETIO_CORS_ORIGINS")
socketio = SocketIO(
    app,
    cors_allowed_origins=_cors_origins.split(",") if _cors_origins else None,
    async_mode='threading',
)

# --- Sécurité : CSRF + rate limiting ---
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

# --- Authentification ---
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if str(user.id) == str(user_id):
            return user
    return None

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_user(username)
        if user and user.check_password(password):
            login_user(user)
            # 🔁 Redirection directe vers la page principale
            return redirect(url_for("index"))
        return render_template("login.html", error="Identifiants invalides")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# --- InfluxDB ---
try:
    import influxdb_client
    from influxdb_client.client.write_api import SYNCHRONOUS
except Exception:
    influxdb_client = None
    SYNCHRONOUS = None

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', '')

influx_client = None
write_api = None
query_api = None

if not all([INFLUXDB_TOKEN, INFLUXDB_BUCKET, INFLUXDB_ORG]):
    logging.warning("InfluxDB non configuré (TOKEN/BUCKET/ORG manquants) : métriques désactivées.")
elif influxdb_client:
    try:
        influx_client = influxdb_client.InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        query_api = influx_client.query_api()
        logging.info("Connexion à InfluxDB réussie.")
    except Exception as e:
        influx_client = None
        write_api = None
        query_api = None
        logging.error(f"Erreur InfluxDB : {e}")

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

init_metrics(influx_client, write_api, INFLUXDB_BUCKET, socketio)
init_network_scan(write_metrics, socketio)

# --- Routes API ---
@app.route("/api/system/stats")
@login_required
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
        logging.error(f"System stats error: {e}")
        return jsonify({"error": "Unable to collect system stats"}), 500

# Liste blanche des arguments nmap acceptables depuis l'API (évite l'injection
# d'arguments type --script, -oN/-oX/-oG, -iL, etc. fournis par le client).
ALLOWED_SCAN_FLAGS = {
    "-sT", "-sS", "-sV", "-sU", "-sC", "-O", "-A", "-Pn",
    "-n", "-v", "-vv", "-T0", "-T1", "-T2", "-T3", "-T4", "-T5",
}
ALLOWED_PING_FLAGS = {
    "-PR", "-PS", "-PA", "-PU", "-PE", "-PP", "-PM", "-PO", "-sn", "-n", "-v",
}
MAX_SCAN_PORTS = 1000
MAX_SCAN_PARALLEL = 32

def _validate_nmap_args(args_str, allowed, label):
    if not args_str:
        return
    for token in str(args_str).split():
        if token not in allowed:
            raise ValueError(f"Argument nmap non autorisé dans {label}: {token!r}")

@app.route("/api/scan/network", methods=["POST"])
@login_required
@csrf.exempt
def api_scan_network():
    try:
        payload = request.json or {}

        network = payload.get("network", os.environ.get("NETWORK_CIDR", "10.236.155.0/24"))
        try:
            ipaddress.ip_network(network, strict=False)
        except ValueError:
            return jsonify({"success": False, "error": f"Réseau CIDR invalide: {network!r}"}), 400

        ports_raw = payload.get("ports", payload.get("ports_str", "22,80,443"))
        if isinstance(ports_raw, (list, tuple)):
            ports = sorted({int(p) for p in ports_raw if 1 <= int(p) <= 65535})
        else:
            ports = parse_ports(str(ports_raw)) if parse_ports else [22, 80, 443]
        if len(ports) > MAX_SCAN_PORTS:
            return jsonify({"success": False, "error": f"Trop de ports demandés (max {MAX_SCAN_PORTS})"}), 400

        parallel = max(1, min(int(payload.get("parallel", 8)), MAX_SCAN_PARALLEL))
        scan_args = payload.get("scan_args", "-sT -sV")
        ping_args = payload.get("ping_args", None)

        _validate_nmap_args(scan_args, ALLOWED_SCAN_FLAGS, "scan_args")
        _validate_nmap_args(ping_args, ALLOWED_PING_FLAGS, "ping_args")

        socketio.start_background_task(
            background_discover_and_emit, network, ports, parallel, scan_args, ping_args
        )

        return jsonify({"success": True, "message": "Scan launched"}), 202
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/test/socket")
@login_required
def test_socket():
    return render_template("test_socket.html")

# --- SPA & Static ---
@app.route("/")
@login_required
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
