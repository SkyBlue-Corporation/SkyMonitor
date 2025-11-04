from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import psutil
import logging
import os
from dotenv import load_dotenv
from datetime import datetime

# --- Chargement des variables ---
load_dotenv()

# --- Initialisation Flask + logs ---
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-key')
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- SocketIO ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- Authentification ---
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

users = {
    "admin": User(id=1, username="admin", password="admin123")
}

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if str(user.id) == str(user_id):
            return user
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.get(username)
        if user and password == user.password:
            login_user(user)
            # 🔁 Redirection directe vers la page principale
            return redirect(url_for("index"))
        return render_template("login.html", error="Identifiants invalides")
    return render_template("login.html")

# --- InfluxDB ---
try:
    import influxdb_client
    from influxdb_client.client.write_api import SYNCHRONOUS
    from influxdb_client import Point
except Exception:
    influxdb_client = None
    SYNCHRONOUS = None

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', '')

if not all([INFLUXDB_TOKEN, INFLUXDB_BUCKET, INFLUXDB_ORG]):
    raise ValueError("⚠️ Vérifie que TOKEN, BUCKET et ORG sont bien définis !")

if influxdb_client:
    try:
        influx_client = influxdb_client.InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        query_api = influx_client.query_api()
        print("✅ Connexion à InfluxDB réussie !")
    except Exception as e:
        influx_client = None
        write_api = None
        query_api = None
        print(f"❌ Erreur InfluxDB : {e}")
else:
    influx_client = None
    write_api = None
    query_api = None

# Test d'écriture
if write_api:
    point = Point("test_metric").tag("source", "sky_monitor").field("value", 42).time(datetime.utcnow())
    try:
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        print(f"✅ Point écrit dans le bucket '{INFLUXDB_BUCKET}' !")
    except Exception as e:
        print(f"❌ Erreur lors de l’écriture du point : {e}")

# Test de lecture
if influx_client:
    try:
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

@app.route("/api/scan/network", methods=["POST"])
@login_required
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
