#!/usr/bin/env python3
import socket
import threading
import time
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor

class NetworkScanner:
    def __init__(self):
        self.active_devices = []
        self.scanning = False
        
    def ping_host(self, ip):
        """Vérifie si un hôte est joignable via ping"""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", "-W" if platform.system().lower() == "linux" else "-w", "1000", ip]
            return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except:
            return False

    def scan_port(self, ip, port, timeout=1):
        """Scan un port spécifique"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                return result == 0
        except:
            return False

    def get_host_info(self, ip):
        """Récupère les informations détaillées d'un hôte"""
        try:
            # Nom d'hôte
            try:
                hostname = socket.getfqdn(ip)
                if hostname == ip:
                    hostname = f"device-{ip.replace('.', '-')}"
            except:
                hostname = f"device-{ip.replace('.', '-')}"

            # Ports ouverts pour détection des postes de travail
            workstation_ports = [3389, 22, 445, 139, 135]  # RDP, SSH, SMB
            server_ports = [80, 443, 21, 25, 53, 3306]     # HTTP, HTTPS, FTP, SMTP, DNS, MySQL
            container_ports = [8080, 3000, 5000, 5432]     # Ports d'applications
            
            all_ports = workstation_ports + server_ports + container_ports
            open_ports = []
            
            for port in all_ports:
                if self.scan_port(ip, port, 0.5):
                    open_ports.append(port)

            # Type d'appareil basé sur les ports ouverts
            device_type = self.detect_device_type(open_ports)
            
            # Statut
            status = "online" if open_ports else "offline"
            
            # Temps de réponse
            response_time = self.measure_response_time(ip)
            
            return {
                'ip': ip,
                'hostname': hostname,
                'open_ports': open_ports,
                'type': device_type,
                'status': status,
                'last_seen': time.time(),
                'response_time': response_time
            }
        except Exception as e:
            print(f"Erreur get_host_info pour {ip}: {e}")
            return None

    def detect_device_type(self, open_ports):
        """Détermine le type d'appareil basé sur les ports ouverts"""
        # Postes de travail - généralement RDP (3389) ou SMB (445)
        if 3389 in open_ports or (445 in open_ports and 135 in open_ports):
            return "workstation"
        # Serveurs - ports web, bases de données, etc.
        elif any(port in open_ports for port in [80, 443, 21, 22, 25, 53, 3306, 5432]):
            return "server"
        # Conteneurs - ports d'applications
        elif any(port in open_ports for port in [8080, 3000, 5000, 8000, 9000, 8081, 8082, 8083, 5432, 3306, 27017, 9200, 5601, 6379]):
            return "container"
        else:
            return "network_device"

    def measure_response_time(self, ip):
        """Mesure le temps de réponse"""
        try:
            start_time = time.time()
            socket.setdefaulttimeout(1)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((ip, 80))
                if result == 0:
                    return round((time.time() - start_time) * 1000, 2)
            return None
        except:
            return None

    def get_local_network(self):
        """Détermine le réseau local"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                return '.'.join(local_ip.split('.')[:3])
        except:
            return "192.168.1"

    def scan_network(self, subnet=None, threads=50):
        """Scan complet du réseau"""
        if not subnet:
            subnet = self.get_local_network()
            
        print(f"🔍 Scan du réseau {subnet}.0/24...")
        self.scanning = True
        active_devices = []

        def check_single_host(host_num):
            if not self.scanning:
                return None
                
            ip = f"{subnet}.{host_num}"
            
            # Vérifier d'abord par ping
            if self.ping_host(ip):
                device_info = self.get_host_info(ip)
                if device_info:
                    return device_info
            return None

        # Scanner avec threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(check_single_host, i) for i in range(1, 255)]
            
            completed = 0
            for future in futures:
                try:
                    result = future.result(timeout=2)
                    if result:
                        active_devices.append(result)
                        device_type = result['type']
                        status_icon = "✅" if result['status'] == 'online' else "❌"
                        print(f"{status_icon} {result['ip']} - {result['hostname']} ({device_type})")
                    
                    completed += 1
                    if completed % 10 == 0:
                        print(f"📊 Progression: {completed}/254 ({completed/254*100:.1f}%)")
                        
                except Exception as e:
                    completed += 1
                    continue

        self.scanning = False
        return active_devices

# Singleton pour le scanner
network_scanner = NetworkScanner()