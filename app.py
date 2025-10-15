from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import psutil
import nmap
import threading
import time
import json
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration InfluxDB
INFLUXDB_URL = "http://influxdb:8086"
INFLUXDB_TOKEN = "monitoring-token"
INFLUXDB_ORG = "monitoring-org"
INFLUXDB_BUCKET = "monitoring-data"

client = influxdb_client.InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

def write_to_influx(measurement, fields, tags=None):
    """Écrire des données dans InfluxDB"""
    point = influxdb_client.Point(measurement)
    
    if tags:
        for key, value in tags.items():
            point = point.tag(key, value)
    
    for key, value in fields.items():
        point = point.field(key, value)
    
    try:
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        return True
    except Exception as e:
        print(f"Erreur InfluxDB: {e}")
        return False

def collect_system_metrics():
    """Collecter les métriques système"""
    while True:
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Mémoire
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            
            # Disque
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            
            # Réseau
            network = psutil.net_io_counters()
            network_sent_mb = network.bytes_sent / (1024**2)
            network_recv_mb = network.bytes_recv / (1024**2)
            
            # Écrire dans InfluxDB
            write_to_influx("system_metrics", {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_gb": memory_used_gb,
                "disk_percent": disk_percent,
                "disk_used_gb": disk_used_gb,
                "network_sent_mb": network_sent_mb,
                "network_recv_mb": network_recv_mb
            }, tags={"host": "monitoring-server"})
            
            # Envoyer via WebSocket
            socketio.emit('system_metrics', {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'timestamp': datetime.now().isoformat()
            })
            
            time.sleep(5)
            
        except Exception as e:
            print(f"Erreur collecte métriques: {e}")
            time.sleep(10)

# Avoir l'autorisation 
def network_scan():
    """Scanner le réseau périodiquement"""
    nm = nmap.PortScanner()
    
    while True:
        try:
            network = "192.168.1.0/24"
            scan_result = nm.scan(hosts=network, arguments='-sn')
            
            devices = []
            for host in nm.all_hosts():
                device_info = {
                    'ip': host,
                    'hostname': nm[host].hostname(),
                    'status': 'up' if nm[host].state() == 'up' else 'down',
                    'last_seen': datetime.now().isoformat()
                }
                devices.append(device_info)
                
                write_to_influx("network_devices", {
                    "status": 1 if device_info['status'] == 'up' else 0
                }, tags={
                    "ip": host,
                    "hostname": device_info['hostname'] or 'unknown'
                })
            
            socketio.emit('network_scan', {
                'devices': devices,
                'total_count': len(devices),
                'online_count': len([d for d in devices if d['status'] == 'up']),
                'scan_time': datetime.now().isoformat()
            })
            
            time.sleep(60)
            
        except Exception as e:
            print(f"Erreur scan réseau: {e}")
            time.sleep(120)

# Routes SPA
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/serveurs')
def serveurs():
    return render_template('serveurs.html')

@app.route('/postes')
def postes():
    return render_template('postes.html')

@app.route('/conteneurs')
def conteneurs():
    return render_template('conteneurs.html')

@app.route('/metriques')
def metriques():
    return render_template('metriques.html')

@app.route('/parametres')
def parametres():
    return render_template('parametres.html')

# API Routes
@app.route('/api/system/stats')
def get_system_stats():
    try:
        cpu_percent = psutil.cpu_percent()
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

@app.route('/api/network/stats')
def get_network_stats():
    try:
        return jsonify({
            'total_devices': 15,
            'online_devices': 12,
            'last_scan': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/serveurs')
def get_servers():
    try:
        servers = [
            {
                'id': 1,
                'name': 'Serveur Web Principal',
                'ip_address': '192.168.1.10',
                'status': 'online',
                'cpu_usage': 45,
                'memory_usage': 60,
                'storage_usage': 75,
                'last_seen': datetime.now().isoformat()
            },
            {
                'id': 2,
                'name': 'Base de Données',
                'ip_address': '192.168.1.11',
                'status': 'online',
                'cpu_usage': 25,
                'memory_usage': 80,
                'storage_usage': 45,
                'last_seen': datetime.now().isoformat()
            }
        ]
        return jsonify(servers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/postes')
def get_workstations():
    try:
        workstations = [
            {
                'id': 1,
                'name': 'PC-Admin-01',
                'ip_address': '192.168.1.50',
                'status': 'online',
                'cpu_usage': 15,
                'memory_usage': 40,
                'last_seen': datetime.now().isoformat()
            },
            {
                'id': 2,
                'name': 'PC-User-02',
                'ip_address': '192.168.1.51',
                'status': 'offline',
                'cpu_usage': 0,
                'memory_usage': 0,
                'last_seen': datetime.now().isoformat()
            }
        ]
        return jsonify(workstations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conteneurs')
def get_containers():
    try:
        containers = [
            {
                'id': 1,
                'name': 'web-app',
                'image': 'nginx:latest',
                'status': 'running',
                'cpu_usage': 10,
                'memory_usage': 25,
                'ports': [80, 443],
                'ip_address': '172.17.0.2'
            }
        ]
        return jsonify(containers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/history')
def get_metrics_history():
    try:
        range_param = request.args.get('range', '1h')
        
        import random
        from datetime import datetime, timedelta
        
        points = 60
        cpu_data = [random.uniform(10, 80) for _ in range(points)]
        memory_data = [random.uniform(30, 90) for _ in range(points)]
        storage_data = [random.uniform(40, 85) for _ in range(points)]
        
        return jsonify({
            'cpu': cpu_data,
            'memory': memory_data,
            'storage': storage_data
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan/network', methods=['POST'])
def scan_network_now():
    try:
        nm = nmap.PortScanner()
        network = request.json.get('network', '192.168.1.0/24')
        
        scan_result = nm.scan(hosts=network, arguments='-sn -T4')
        
        devices = []
        for host in nm.all_hosts():
            device_info = {
                'ip': host,
                'hostname': nm[host].hostname(),
                'status': 'online',
                'mac_address': nm[host].addresses.get('mac', 'Unknown'),
                'last_seen': datetime.now().isoformat()
            }
            devices.append(device_info)
            
            write_to_influx("network_scan", {
                "scan_status": 1
            }, tags={
                "ip": host,
                "hostname": device_info['hostname'] or 'unknown'
            })
        
        socketio.emit('network_scan_complete', {
            'devices': devices,
            'scan_time': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'devices_found': len(devices),
            'scan_time': scan_result['nmap']['scanstats']['elapsed']
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/network/devices')
def get_network_devices():
    try:
        devices = [
            {
                'ip': '192.168.1.1',
                'hostname': 'router.local',
                'status': 'online',
                'last_seen': datetime.now().isoformat()
            },
            {
                'ip': '192.168.1.10',
                'hostname': 'server1.local',
                'status': 'online',
                'last_seen': datetime.now().isoformat()
            }
        ]
        return jsonify(devices)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# SPA fallback
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint API non trouvé'}), 404
    return render_template('index.html'), 200

@socketio.on('connect')
def handle_connect():
    print('Client connecté')
    socketio.emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client déconnecté')

if __name__ == '__main__':
    metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
    network_thread = threading.Thread(target=network_scan, daemon=True)
    
    metrics_thread.start()
    network_thread.start()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
