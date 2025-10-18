# ========================= app.py =========================
import os
import time
from datetime import datetime
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_socketio import SocketIO
import psutil
import nmap
import docker

# ------------------- Flask + SocketIO -------------------
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ------------------- InfluxDB Client -------------------
try:
    import influxdb_client
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    influxdb_client = None
    SYNCHRONOUS = None

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'monitoring-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'monitoring-org')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'monitoring-data')

if influxdb_client:
    influx_client = influxdb_client.InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
else:
    influx_client = None
    write_api = None

# ------------------- Docker Client -------------------
docker_client = docker.from_env()
# ------------------- Nmap Client -------------------
nm = nmap.PortScanner()

# ------------------- Fonctions testables -------------------
def write_metrics(measurement, fields, tags=None):
    """Écrire un point dans InfluxDB"""
    if not write_api:
        print("InfluxDB non disponible, point ignoré")
        return
    point = influxdb_client.Point(measurement)
    if tags:
        for k, v in tags.items():
            point = point.tag(k, v)
    for k, v in fields.items():
        point = point.field(k, v)
    try:
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    except Exception as e:
        print(f"Erreur InfluxDB: {e}")

def network_scan(network="10.236.155.0/24"):
    """Scan réseau et retourne liste de devices"""
    try:
        nm.scan(hosts=network, arguments='-sn -T4')
        devices = []
        for host in nm.all_hosts():
            status = 1 if nm[host].state() == 'up' else 0
            hostname = nm[host].hostname() or 'unknown'
            devices.append({
                'ip': host,
                'hostname': hostname,
                'status': status,
                'last_seen': datetime.now().isoformat()
            })
        return devices
    except Exception as e:
        print(f"Erreur scan réseau: {e}")
        return []

def collect_system_metrics():
    """Collecte métriques CPU/Mémoire/Disque/Network et émet via SocketIO"""
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

            tags = {"host": "monitoring-server"}

            write_metrics("system_metrics", fields, tags)
            socketio.emit('system_metrics', {**fields, 'timestamp': datetime.now().isoformat()})
            time.sleep(5)
        except Exception as e:
            print(f"Erreur collecte système: {e}")
            time.sleep(10)

def collect_docker_metrics():
    """Collecte métriques Docker et émet via SocketIO"""
    while True:
        try:
            containers = docker_client.containers.list()
            for c in containers:
                stats = c.stats(stream=False)
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100 if system_delta > 0 else 0
                mem_usage = stats['memory_stats']['usage'] / (1024**2)
                mem_limit = stats['memory_stats']['limit'] / (1024**2)
                mem_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0

                fields = {"cpu_percent": cpu_percent, "memory_usage_mb": mem_usage, "memory_percent": mem_percent}
                tags = {"container_name": c.name, "container_id": c.id[:12]}

                write_metrics("docker_metrics", fields, tags)
                socketio.emit('docker_metrics', {**fields, 'container_name': c.name, 'timestamp': datetime.now().isoformat()})
            time.sleep(10)
        except Exception as e:
            print(f"Erreur collecte Docker: {e}")
            time.sleep(15)

# ------------------- Routes API -------------------
@app.route('/api/system/stats')
def get_system_stats():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return jsonify({
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': disk.percent,
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan/network', methods=['POST'])
def scan_network_now():
    try:
        network = request.json.get('network', '10.236.155.0/24')
        devices = network_scan(network)
        socketio.emit('network_scan_complete', {'devices': devices, 'scan_time': datetime.now().isoformat()})
        return jsonify({'success': True, 'devices_found': len(devices)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ------------------- Routes SPA -------------------
@app.route('/')
def index(): return render_template('index.html')
@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

# ------------------- WebSocket -------------------
@socketio.on('connect')
def handle_connect():
    print('Client connecté')
    socketio.emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client déconnecté')

# ------------------- SPA fallback & static -------------------
@app.route('/static/<path:filename>')
def static_files(filename): return send_from_directory(app.static_folder, filename)

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint API non trouvé'}), 404
    return render_template('index.html'), 200

# ------------------- Lancer le serveur -------------------
if __name__ == '__main__':
    # Lancer les tâches en background
    socketio.start_background_task(collect_system_metrics)
    socketio.start_background_task(collect_docker_metrics)
    socketio.start_background_task(lambda: network_scan())  # scan en boucle à l'intérieur de la fonction si nécessaire
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

# ------------------- Expose pour tests -------------------
__all__ = ['app', 'socketio', 'write_api', 'write_metrics', 'docker_client', 'nm', 'network_scan', 'collect_system_metrics', 'collect_docker_metrics']
