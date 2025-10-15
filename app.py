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
import socket
import netifaces
from ipaddress import IPv4Network
import concurrent.futures

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

# Cache pour les devices réseau
network_devices_cache = {
    'devices': [],
    'last_scan': None,
    'cache_duration': 300  # 5 minutes
}

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

def get_local_network():
    """Détecte automatiquement le réseau local"""
    try:
        # Obtenir l'adresse IP de l'interface par défaut
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Trouver l'interface réseau correspondante
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr_info in addrs[netifaces.AF_INET]:
                    if addr_info['addr'] == local_ip:
                        netmask = addr_info.get('netmask', '255.255.255.0')
                        # Calculer le réseau CIDR
                        network = IPv4Network(f"{local_ip}/{netmask}", strict=False)
                        return str(network)
        
        # Fallback: réseau par défaut basé sur l'IP locale
        return f"{local_ip.rsplit('.', 1)[0]}.0/24"
        
    except Exception as e:
        print(f"Erreur détection réseau: {e}")
        return "192.168.1.0/24"  # Fallback

def get_local_network_simple():
    """Détection réseau simplifiée sans netifaces"""
    try:
        # Obtenir l'IP locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Déterminer le masque selon la classe d'IP
        first_octet = int(local_ip.split('.')[0])
        if first_octet == 10:
            return "10.0.0.0/8"
        elif first_octet == 172 and 16 <= int(local_ip.split('.')[1]) <= 31:
            return "172.16.0.0/12"
        elif first_octet == 192:
            return "192.168.0.0/16"
        else:
            # Fallback: /24 pour les réseaux privés non standard
            return f"{local_ip.rsplit('.', 1)[0]}.0/24"
            
    except Exception as e:
        print(f"Erreur détection réseau simple: {e}")
        return "192.168.1.0/24"

def detect_device_type(ip, hostname, mac_address):
    """Détecter le type d'appareil basé sur l'IP, hostname et MAC"""
    hostname_lower = hostname.lower()
    mac_lower = mac_address.lower()
    
    # Détection basée sur le hostname
    if any(keyword in hostname_lower for keyword in ['router', 'gateway', 'livebox', 'freebox', 'bbox', 'orange']):
        return 'router'
    elif any(keyword in hostname_lower for keyword in ['nas', 'synology', 'qnap', 'server']):
        return 'nas'
    elif any(keyword in hostname_lower for keyword in ['printer', 'print', 'hp-', 'canon', 'epson']):
        return 'printer'
    elif any(keyword in hostname_lower for keyword in ['cam', 'camera', 'dvr', 'nvr', 'surveillance']):
        return 'camera'
    elif any(keyword in hostname_lower for keyword in ['tv', 'smarttv', 'android-tv', 'philips', 'samsung']):
        return 'tv'
    elif any(keyword in hostname_lower for keyword in ['phone', 'mobile', 'iphone', 'android', 'samsung']):
        return 'phone'
    elif any(keyword in hostname_lower for keyword in ['pc-', 'desktop', 'laptop', 'notebook', 'computer']):
        return 'computer'
    elif any(keyword in hostname_lower for keyword in ['raspberry', 'pi', 'arduino', 'iot']):
        return 'iot'
    # Détection basée sur l'IP
    elif ip.endswith('.1'):  # Généralement le routeur
        return 'router'
    elif ip.endswith('.254') or ip.endswith('.253'):  # Souvent des équipements réseau
        return 'network'
    else:
        return 'unknown'

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

def network_scan():
    """Scanner le réseau périodiquement avec détection automatique"""
    nm = nmap.PortScanner()
    
    while True:
        try:
            # Détection automatique du réseau
            network = get_local_network()
            print(f"Scan automatique du réseau: {network}")
            
            # Émettre le début du scan
            socketio.emit('network_scan_start', {
                'network': network,
                'start_time': datetime.now().isoformat(),
                'type': 'auto_detected'
            })
            
            scan_result = nm.scan(hosts=network, arguments='-sn --host-timeout 30s')
            
            devices = []
            for host in nm.all_hosts():
                host_info = nm[host]
                
                # Obtenir le hostname
                hostname = host_info.hostname()
                if not hostname or hostname == '':
                    try:
                        hostname = socket.gethostbyaddr(host)[0]
                    except (socket.herror, socket.gaierror):
                        hostname = f"device-{host.replace('.', '-')}"
                    except:
                        hostname = f"unknown-{host.replace('.', '-')}"
                
                device_type = detect_device_type(host, hostname, host_info.addresses.get('mac', ''))
                
                device_info = {
                    'ip': host,
                    'hostname': hostname,
                    'status': 'up' if host_info.state() == 'up' else 'down',
                    'mac_address': host_info.addresses.get('mac', 'Unknown'),
                    'vendor': host_info.vendor() or 'Unknown',
                    'type': device_type,
                    'last_seen': datetime.now().isoformat()
                }
                devices.append(device_info)
                
                write_to_influx("network_devices", {
                    "status": 1 if device_info['status'] == 'up' else 0
                }, tags={
                    "ip": host,
                    "hostname": device_info['hostname'] or 'unknown',
                    "network": network,
                    "type": device_type
                })
            
            # Mettre à jour le cache
            network_devices_cache['devices'] = devices
            network_devices_cache['last_scan'] = datetime.now()
            
            socketio.emit('network_scan', {
                'devices': devices,
                'total_count': len(devices),
                'online_count': len([d for d in devices if d['status'] == 'up']),
                'scan_time': datetime.now().isoformat(),
                'network': network,
                'scan_duration': scan_result['nmap']['scanstats']['elapsed']
            })
            
            time.sleep(300)  # Scan toutes les 5 minutes
            
        except Exception as e:
            print(f"Erreur scan réseau: {e}")
            socketio.emit('network_scan_error', {'error': str(e)})
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
        # Utiliser les données du cache
        current_time = datetime.now()
        if network_devices_cache['last_scan']:
            online_count = len([d for d in network_devices_cache['devices'] if d['status'] == 'up'])
            total_count = len(network_devices_cache['devices'])
        else:
            online_count = 0
            total_count = 0
            
        return jsonify({
            'total_devices': total_count,
            'online_devices': online_count,
            'last_scan': network_devices_cache['last_scan'].isoformat() if network_devices_cache['last_scan'] else None,
            'network': get_local_network()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/info')
def get_network_info():
    """Retourne les informations du réseau détecté"""
    try:
        network = get_local_network()
        return jsonify({
            'local_network': network,
            'auto_detected': True,
            'local_ip': socket.gethostbyname(socket.gethostname())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/devices')
def get_network_devices():
    try:
        global network_devices_cache
        
        # Vérifier si le cache est encore valide
        current_time = datetime.now()
        if (network_devices_cache['last_scan'] and 
            (current_time - network_devices_cache['last_scan']).total_seconds() < network_devices_cache['cache_duration']):
            return jsonify({
                'devices': network_devices_cache['devices'],
                'total_count': len(network_devices_cache['devices']),
                'online_count': len([d for d in network_devices_cache['devices'] if d['status'] == 'up']),
                'from_cache': True,
                'cache_age': (current_time - network_devices_cache['last_scan']).total_seconds(),
                'scan_time': network_devices_cache['last_scan'].isoformat()
            })
        
        nm = nmap.PortScanner()
        network = get_local_network()
        
        # Scan avec détection des ports ouverts pour plus d'informations
        scan_result = nm.scan(hosts=network, arguments='-sn -T4 --host-timeout 15s')
        
        devices = []
        for host in nm.all_hosts():
            host_info = nm[host]
            
            # Obtenir le hostname
            hostname = host_info.hostname()
            if not hostname or hostname == '':
                try:
                    # Essayer la résolution DNS
                    hostname = socket.gethostbyaddr(host)[0]
                except (socket.herror, socket.gaierror):
                    # Si échec, utiliser un nom générique basé sur l'IP
                    hostname = f"device-{host.replace('.', '-')}"
                except:
                    hostname = f"unknown-{host.replace('.', '-')}"
            
            # Détecter le type d'appareil
            device_type = detect_device_type(host, hostname, host_info.addresses.get('mac', ''))
            
            device_info = {
                'ip': host,
                'hostname': hostname,
                'status': 'online',
                'mac_address': host_info.addresses.get('mac', 'Unknown'),
                'vendor': host_info.vendor() or 'Unknown',
                'type': device_type,
                'last_seen': datetime.now().isoformat(),
                'os_guess': host_info.get('osmatch', [{}])[0].get('name', 'Unknown') if host_info.get('osmatch') else 'Unknown'
            }
            devices.append(device_info)
        
        # Mettre à jour le cache
        network_devices_cache['devices'] = devices
        network_devices_cache['last_scan'] = current_time
        
        # Trier par IP
        devices.sort(key=lambda x: [int(part) for part in x['ip'].split('.')])
        
        return jsonify({
            'devices': devices,
            'total_count': len(devices),
            'online_count': len([d for d in devices if d['status'] == 'online']),
            'network_scanned': network,
            'scan_time': current_time.isoformat(),
            'from_cache': False
        })
    
    except Exception as e:
        # En cas d'erreur, retourner le cache si disponible
        if network_devices_cache['devices']:
            return jsonify({
                'devices': network_devices_cache['devices'],
                'total_count': len(network_devices_cache['devices']),
                'online_count': len([d for d in network_devices_cache['devices'] if d['status'] == 'online']),
                'from_cache': True,
                'error': f'Scan échoué, utilisation du cache: {str(e)}',
                'scan_time': network_devices_cache['last_scan'].isoformat() if network_devices_cache['last_scan'] else None
            })
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/devices/refresh', methods=['POST'])
def refresh_network_devices():
    """Forcer un rafraîchissement du cache des devices"""
    try:
        global network_devices_cache
        network_devices_cache['last_scan'] = None
        
        # Retourner les nouveaux devices
        return get_network_devices()
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/serveurs')
def get_servers():
    try:
        # Utiliser les vraies données réseau pour les serveurs
        servers = []
        for device in network_devices_cache['devices']:
            if device['type'] in ['nas', 'server', 'router'] or 'server' in device['hostname'].lower():
                servers.append({
                    'id': hash(device['ip']),  # ID unique basé sur l'IP
                    'name': device['hostname'],
                    'ip_address': device['ip'],
                    'status': 'online' if device['status'] == 'online' else 'offline',
                    'cpu_usage': 0,  # À implémenter avec SNMP ou autre
                    'memory_usage': 0,
                    'storage_usage': 0,
                    'type': device['type'],
                    'last_seen': device['last_seen']
                })
        
        # Si pas de serveurs détectés, retourner des exemples
        if not servers:
            servers = [
                {
                    'id': 1,
                    'name': 'Routeur Principal',
                    'ip_address': '192.168.1.1',
                    'status': 'online',
                    'cpu_usage': 15,
                    'memory_usage': 40,
                    'storage_usage': 10,
                    'type': 'router',
                    'last_seen': datetime.now().isoformat()
                }
            ]
            
        return jsonify(servers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/postes')
def get_workstations():
    try:
        # Utiliser les vraies données réseau pour les postes
        workstations = []
        for device in network_devices_cache['devices']:
            if device['type'] in ['computer', 'unknown'] or 'pc' in device['hostname'].lower():
                workstations.append({
                    'id': hash(device['ip']),
                    'name': device['hostname'],
                    'ip_address': device['ip'],
                    'status': 'online' if device['status'] == 'online' else 'offline',
                    'cpu_usage': 0,
                    'memory_usage': 0,
                    'type': device['type'],
                    'last_seen': device['last_seen']
                })
        
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
        
        # Détection automatique OU utilisation du réseau fourni
        network = request.json.get('network') if request.json else None
        if not network:
            network = get_local_network()
        
        print(f"Scan du réseau: {network}")
        
        # Émettre le début du scan
        socketio.emit('network_scan_start', {
            'network': network,
            'start_time': datetime.now().isoformat(),
            'type': 'auto_detected' if not request.json or not request.json.get('network') else 'manual'
        })
        
        # Scan avec timeout
        scan_result = nm.scan(hosts=network, arguments='-sn -T4 --host-timeout 30s')
        
        devices = []
        for host in nm.all_hosts():
            host_info = nm[host]
            
            # Obtenir le hostname
            hostname = host_info.hostname()
            if not hostname or hostname == '':
                try:
                    hostname = socket.gethostbyaddr(host)[0]
                except:
                    hostname = f"device-{host.replace('.', '-')}"
            
            device_type = detect_device_type(host, hostname, host_info.addresses.get('mac', ''))
            
            device_info = {
                'ip': host,
                'hostname': hostname,
                'status': 'online',
                'mac_address': host_info.addresses.get('mac', 'Unknown'),
                'vendor': host_info.vendor() or 'Unknown',
                'type': device_type,
                'last_seen': datetime.now().isoformat()
            }
            devices.append(device_info)
            
            # Sauvegarde InfluxDB
            try:
                write_to_influx("network_scan", {
                    "scan_status": 1,
                    "devices_found": len(devices)
                }, tags={
                    "ip": host,
                    "hostname": device_info['hostname'],
                    "network": network,
                    "type": device_type
                })
            except Exception as db_error:
                print(f"InfluxDB error: {db_error}")
        
        # Mettre à jour le cache
        network_devices_cache['devices'] = devices
        network_devices_cache['last_scan'] = datetime.now()
        
        socketio.emit('network_scan_complete', {
            'devices': devices,
            'scan_time': datetime.now().isoformat(),
            'total_devices': len(devices),
            'network': network,
            'scan_duration': scan_result['nmap']['scanstats']['elapsed']
        })
        
        return jsonify({
            'success': True,
            'devices_found': len(devices),
            'scan_time': scan_result['nmap']['scanstats']['elapsed'],
            'network': network,
            'auto_detected': not request.json or not request.json.get('network')
        })
    
    except nmap.PortScannerError as nmap_error:
        error_msg = f'Erreur Nmap: {str(nmap_error)}'
        socketio.emit('network_scan_error', {'error': error_msg})
        return jsonify({'success': False, 'error': error_msg}), 500
    except Exception as e:
        error_msg = f'Erreur scan: {str(e)}'
        socketio.emit('network_scan_error', {'error': error_msg})
        return jsonify({'success': False, 'error': error_msg}), 500

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
    
    # Envoyer les informations réseau au client
    try:
        network_info = {
            'local_network': get_local_network(),
            'local_ip': socket.gethostbyname(socket.gethostname())
        }
        socketio.emit('network_info', network_info)
    except Exception as e:
        print(f"Erreur envoi info réseau: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client déconnecté')

@socketio.on('request_network_scan')
def handle_network_scan_request():
    """Déclencher un scan manuel via WebSocket"""
    scan_network_now()

if __name__ == '__main__':
    metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
    network_thread = threading.Thread(target=network_scan, daemon=True)
    
    metrics_thread.start()
    network_thread.start()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)