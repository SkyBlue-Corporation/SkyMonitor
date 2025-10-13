#!/usr/bin/env python3
import socket
import threading
import time
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
from datetime import datetime

class NetworkScanner:
    def __init__(self):
        self.active_devices = []
        self.scanning = False
        self.last_scan_time = None
        self.scan_progress = 0
        self.scan_callback = None
        
    def ping_host(self, ip, timeout=1):
        """Vérifie si un hôte est joignable via ping avec timeout"""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
            command = ["ping", param, "1", timeout_param, str(timeout * 1000), ip]
            
            # Utiliser Popen avec timeout pour éviter les blocages
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                process.wait(timeout=timeout + 0.5)
                return process.returncode == 0
            except subprocess.TimeoutExpired:
                process.kill()
                return False
                
        except Exception as e:
            return False

    def scan_port_fast(self, ip, port, timeout=0.3):
        """Scan rapide d'un port avec timeout réduit"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                return result == 0
        except:
            return False

    def get_host_info(self, ip):
        """Récupère les informations détaillées d'un hôte de manière optimisée"""
        try:
            # Nom d'hôte (rapide)
            hostname = ip
            try:
                hostname = socket.getfqdn(ip)
                if hostname == ip:
                    hostname = f"device-{ip.replace('.', '-')}"
            except:
                hostname = f"device-{ip.replace('.', '-')}"

            # Ports prioritaires pour une détection rapide
            priority_ports = {
                'workstation': [3389, 445, 135, 139],  # RDP, SMB
                'server': [80, 443, 22, 21],           # HTTP, HTTPS, SSH, FTP
                'container': [8080, 3000, 5000, 5432]  # Apps web, PostgreSQL
            }
            
            open_ports = []
            device_type = "unknown"
            
            # Scanner d'abord les ports les plus significatifs
            for port_type, ports in priority_ports.items():
                for port in ports:
                    if self.scan_port_fast(ip, port, 0.2):
                        open_ports.append(port)
                        # Dès qu'on trouve un port significatif, on détermine le type
                        if device_type == "unknown":
                            device_type = port_type
                        # Pas besoin de scanner tous les ports si on a déjà une bonne idée
                        if len(open_ports) >= 2:
                            break
                if device_type != "unknown":
                    break
            
            # Si aucun port significatif trouvé, essayer quelques ports supplémentaires
            if device_type == "unknown":
                additional_ports = [25, 53, 110, 143, 993, 995, 3306, 27017, 9200]
                for port in additional_ports[:3]:  # Seulement 3 ports supplémentaires
                    if self.scan_port_fast(ip, port, 0.2):
                        open_ports.append(port)
                        if port in [25, 53, 110]:
                            device_type = "server"
                        elif port in [3306, 27017, 9200]:
                            device_type = "container"
                        break

            # Affiner la détection basée sur la combinaison de ports
            if device_type == "unknown" and open_ports:
                device_type = self.refine_device_type(open_ports)
            
            # Statut
            status = "online" if open_ports else "offline"
            
            return {
                'ip': ip,
                'hostname': hostname,
                'open_ports': open_ports,
                'type': device_type,
                'status': status,
                'last_seen': datetime.now().isoformat(),
                'response_time': self.measure_response_time(ip),
                'mac_address': self.get_mac_address(ip)  # Nouveau: adresse MAC
            }
        except Exception as e:
            return None

    def refine_device_type(self, open_ports):
        """Affine la détection du type d'appareil basé sur les ports ouverts"""
        workstation_score = len([p for p in open_ports if p in [3389, 445, 135, 139]])
        server_score = len([p for p in open_ports if p in [80, 443, 22, 21, 25, 53]])
        container_score = len([p for p in open_ports if p in [8080, 3000, 5000, 5432, 3306, 27017]])
        
        scores = {
            'workstation': workstation_score,
            'server': server_score,
            'container': container_score
        }
        
        best_type = max(scores, key=scores.get)
        return best_type if scores[best_type] > 0 else "network_device"

    def measure_response_time(self, ip):
        """Mesure le temps de réponse optimisé"""
        try:
            start_time = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, 80))
                if result == 0:
                    return round((time.time() - start_time) * 1000, 2)
            return None
        except:
            return None

    def get_mac_address(self, ip):
        """Tente de récupérer l'adresse MAC (Unix/Linux seulement)"""
        try:
            if platform.system().lower() != "linux":
                return None
                
            # Utiliser ARP pour récupérer le MAC
            result = subprocess.check_output(['arp', '-n', ip], stderr=subprocess.DEVNULL)
            result = result.decode('utf-8')
            lines = result.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 3:
                    return parts[2]
        except:
            pass
        return None

    def get_local_network(self):
        """Détermine le réseau local de manière plus robuste"""
        try:
            # Essayer plusieurs méthodes pour obtenir l'IP locale
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
                return '.'.join(local_ip.split('.')[:3])
        except:
            try:
                # Méthode de secours
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                return '.'.join(local_ip.split('.')[:3])
            except:
                return "192.168.1"

    def scan_network(self, subnet=None, max_scan_time=60, progress_callback=None):
        """Scan complet du réseau avec timeout maximum de 1 minute"""
        if not subnet:
            subnet = self.get_local_network()
            
        print(f"🔍 Scan du réseau {subnet}.0/24 (max {max_scan_time}s)...")
        self.scanning = True
        self.scan_progress = 0
        self.scan_callback = progress_callback
        self.last_scan_time = datetime.now()
        
        active_devices = []
        scan_start_time = time.time()
        
        def check_single_host(host_num):
            if not self.scanning or (time.time() - scan_start_time) > max_scan_time:
                return None
                
            ip = f"{subnet}.{host_num}"
            
            # Vérifier d'abord par ping rapide
            if self.ping_host(ip, timeout=0.8):
                device_info = self.get_host_info(ip)
                return device_info
            return None

        # Scanner avec threads optimisé
        total_hosts = 254
        completed = 0
        
        with ThreadPoolExecutor(max_workers=100) as executor:  # Plus de threads pour plus de vitesse
            # Soumettre toutes les tâches
            future_to_host = {
                executor.submit(check_single_host, i): i 
                for i in range(1, total_hosts + 1)
            }
            
            # Traiter les résultats au fur et à mesure
            for future in as_completed(future_to_host, timeout=max_scan_time):
                if not self.scanning or (time.time() - scan_start_time) > max_scan_time:
                    break
                    
                try:
                    result = future.result(timeout=1)
                    if result:
                        active_devices.append(result)
                        device_type = result['type']
                        status_icon = "✅" if result['status'] == 'online' else "🟡"
                        mac_info = f" - MAC: {result['mac_address']}" if result['mac_address'] else ""
                        print(f"{status_icon} {result['ip']} - {result['hostname']} ({device_type}){mac_info}")
                    
                    completed += 1
                    self.scan_progress = int((completed / total_hosts) * 100)
                    
                    # Callback de progression
                    if self.scan_callback:
                        self.scan_callback(self.scan_progress, completed, total_hosts)
                    
                    # Afficher la progression tous les 10%
                    if completed % 25 == 0 or completed == total_hosts:
                        elapsed_time = time.time() - scan_start_time
                        remaining = max_scan_time - elapsed_time
                        print(f"📊 Progression: {completed}/{total_hosts} ({self.scan_progress}%) - Temps écoulé: {elapsed_time:.1f}s - Restant: {remaining:.1f}s")
                        
                except Exception as e:
                    completed += 1
                    continue

        self.scanning = False
        scan_duration = time.time() - scan_start_time
        
        print(f"✅ Scan terminé en {scan_duration:.1f}s - {len(active_devices)} appareils détectés")
        
        # Statistiques
        device_types = {}
        for device in active_devices:
            device_types[device['type']] = device_types.get(device['type'], 0) + 1
        
        print("📈 Statistiques:")
        for dev_type, count in device_types.items():
            print(f"   {dev_type}: {count}")
        
        return active_devices

    def quick_scan(self, known_ips=None, timeout=5):
        """Scan rapide des IPs connues pour les mises à jour (5 secondes max)"""
        if known_ips is None:
            known_ips = [device['ip'] for device in self.active_devices]
            
        print(f"🔄 Scan rapide de {len(known_ips)} appareils connus...")
        updated_devices = []
        
        def check_device(ip):
            if self.ping_host(ip, timeout=0.5):
                device_info = self.get_host_info(ip)
                return device_info
            else:
                # Marquer comme hors ligne
                return {
                    'ip': ip,
                    'hostname': f"device-{ip.replace('.', '-')}",
                    'status': 'offline',
                    'type': 'unknown',
                    'open_ports': [],
                    'last_seen': datetime.now().isoformat()
                }
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(check_device, ip) for ip in known_ips]
            
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result(timeout=1)
                    if result:
                        updated_devices.append(result)
                except:
                    continue
        
        # Mettre à jour la liste active
        for updated in updated_devices:
            # Remplacer ou ajouter l'appareil mis à jour
            existing_index = next((i for i, d in enumerate(self.active_devices) if d['ip'] == updated['ip']), -1)
            if existing_index >= 0:
                self.active_devices[existing_index] = updated
            else:
                self.active_devices.append(updated)
        
        print(f"✅ Scan rapide terminé en {time.time() - start_time:.1f}s - {len(updated_devices)} appareils mis à jour")
        return updated_devices

    def continuous_monitoring(self, interval=5):
        """Surveillance continue avec mise à jour toutes les 5 secondes"""
        print(f"🔄 Surveillance continue activée (mise à jour toutes les {interval}s)")
        
        while True:
            try:
                if self.active_devices:
                    # Scan rapide des appareils connus
                    self.quick_scan()
                else:
                    # Si aucun appareil connu, faire un scan complet rapide
                    print("🔍 Aucun appareil connu, lancement d'un scan complet...")
                    self.scan_network(max_scan_time=30)  # Scan complet en 30s max
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("🛑 Surveillance arrêtée")
                break
            except Exception as e:
                print(f"❌ Erreur lors de la surveillance: {e}")
                time.sleep(interval)  # Attendre avant de réessayer

    def get_network_stats(self):
        """Retourne les statistiques du réseau"""
        stats = {
            'total_devices': len(self.active_devices),
            'online_devices': len([d for d in self.active_devices if d['status'] == 'online']),
            'device_types': {},
            'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'scanning': self.scanning,
            'scan_progress': self.scan_progress
        }
        
        for device in self.active_devices:
            dev_type = device['type']
            stats['device_types'][dev_type] = stats['device_types'].get(dev_type, 0) + 1
            
        return stats

# Singleton pour le scanner
network_scanner = NetworkScanner()

# Fonction utilitaire pour le callback de progression
def print_progress(progress, completed, total):
    """Callback pour afficher la progression"""
    if progress % 10 == 0:  # Afficher seulement tous les 10%
        print(f"🔄 Progression: {progress}% ({completed}/{total})")

# Exemple d'utilisation
if __name__ == "__main__":
    # Test du scanner
    print("🚀 Test du scanner réseau optimisé")
    
    # Scan complet (max 1 minute)
    devices = network_scanner.scan_network(progress_callback=print_progress)
    print(f"📋 Appareils trouvés: {len(devices)}")
    
    # Affichage des appareils
    for device in devices:
        print(f"  - {device['ip']} ({device['type']}) - {device['status']}")
    
    # Démarrer la surveillance continue
    print("\n🎯 Démarrage de la surveillance continue...")
    try:
        network_scanner.continuous_monitoring(interval=5)
    except KeyboardInterrupt:
        print("\n👋 Arrêt du programme")

# =============================================
# 🔄 INTÉGRATION INFLUXDB & IA
# =============================================

try:
    from app.services.influx_service import influx_service
    from app.services.ai_service import ai_service
    INFLUX_AI_AVAILABLE = True
    print("✅ Modules InfluxDB et IA chargés")
except ImportError as e:
    INFLUX_AI_AVAILABLE = False
    print(f"⚠️  Modules InfluxDB/IA non disponibles: {e}")

class NetworkScannerEnhanced(NetworkScanner):
    """Version étendue du scanner avec intégration InfluxDB et IA"""
    
    def __init__(self):
        super().__init__()
        self.influx_enabled = INFLUX_AI_AVAILABLE
        self.ai_enabled = INFLUX_AI_AVAILABLE
        self.scan_lock = threading.Lock()
    
    def scan_network_async(self, subnet=None, max_scan_time=60, callback=None):
        """Lance un scan asynchrone avec intégration InfluxDB/IA"""
        def scan_thread():
            try:
                result = self.scan_network_enhanced(subnet, max_scan_time)
                if callback:
                    callback('completed', result)
            except Exception as e:
                print(f"❌ Erreur scan asynchrone: {e}")
                if callback:
                    callback('error', str(e))
        
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()
        return thread
    
    def scan_network_enhanced(self, subnet=None, max_scan_time=60):
        """Scan réseau avec enregistrement InfluxDB et analyse IA"""
        with self.scan_lock:
            print("🚀 Scan réseau avancé démarré...")
            
            # Effectuer le scan de base
            devices = super().scan_network(subnet, max_scan_time)
            
            if not self.influx_enabled:
                print("⚠️  InfluxDB non disponible - retour des données basiques")
                return {
                    'devices': devices,
                    'scan_metrics': self._calculate_scan_metrics(devices),
                    'influxdb_available': False,
                    'ai_available': False
                }
            
            # Enregistrement dans InfluxDB
            successful_writes = 0
            for device in devices:
                if influx_service.write_device_metrics(device):
                    successful_writes += 1
            
            print(f"📊 {successful_writes}/{len(devices)} appareils enregistrés dans InfluxDB")
            
            # Métriques de scan global
            scan_metrics = self._calculate_scan_metrics(devices)
            influx_service.write_scan_metrics(scan_metrics)
            
            # Analyse IA asynchrone
            ai_results = {}
            if self.ai_enabled:
                ai_thread = threading.Thread(
                    target=self._perform_ai_analysis, 
                    args=(devices,),
                    daemon=True
                )
                ai_thread.start()
                ai_results = {
                    'analysis_in_progress': True,
                    'message': 'Analyse IA démarrée en arrière-plan'
                }
            else:
                ai_results = {
                    'analysis_in_progress': False,
                    'message': 'IA non disponible'
                }
            
            return {
                'devices': devices,
                'scan_metrics': scan_metrics,
                'influxdb_stats': {
                    'devices_written': successful_writes,
                    'total_devices': len(devices),
                    'success_rate': successful_writes / len(devices) if devices else 0
                },
                'ai_analysis': ai_results,
                'influxdb_available': True,
                'ai_available': self.ai_enabled,
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_scan_metrics(self, devices):
        """Calcule les métriques de scan"""
        return {
            'total_devices': len(devices),
            'online_devices': len([d for d in devices if d['status'] == 'online']),
            'workstations': len([d for d in devices if d['type'] == 'workstation']),
            'servers': len([d for d in devices if d['type'] == 'server']),
            'containers': len([d for d in devices if d['type'] == 'container']),
            'network_devices': len([d for d in devices if d['type'] == 'network_device']),
            'unknown_devices': len([d for d in devices if d['type'] == 'unknown'])
        }
    
    def _perform_ai_analysis(self, devices):
        """Effectue l'analyse IA en arrière-plan"""
        try:
            print("🧠 Démarrage de l'analyse IA...")
            
            # Détection d'anomalies
            anomalies = ai_service.detect_anomalies(devices)
            
            # Génération d'insights
            insights = ai_service.generate_insights(devices)
            
            # Enregistrement des anomalies dans InfluxDB
            for anomaly in anomalies:
                influx_service.write_anomaly_metrics(anomaly)
            
            print(f"✅ Analyse IA terminée: {len(anomalies)} anomalies, {len(insights)} insights")
            
            # Log des insights importants
            for insight in insights:
                if insight['severity'] in ['high', 'medium']:
                    print(f"📢 Insight {insight['severity']}: {insight['title']} - {insight['message']}")
                    
        except Exception as e:
            print(f"❌ Erreur analyse IA: {e}")
    
    def quick_scan_enhanced(self, known_ips=None, timeout=5):
        """Scan rapide avec mise à jour InfluxDB"""
        updated_devices = super().quick_scan(known_ips, timeout)
        
        if self.influx_enabled:
            for device in updated_devices:
                influx_service.write_device_metrics(device)
            print(f"🔄 {len(updated_devices)} appareils mis à jour dans InfluxDB")
        
        return updated_devices
    
    def get_enhanced_stats(self):
        """Retourne les statistiques étendues"""
        base_stats = super().get_network_stats()
        
        enhanced_stats = {
            **base_stats,
            'influxdb_available': self.influx_enabled,
            'ai_available': self.ai_enabled,
            'influxdb_status': 'connected' if self.influx_enabled and influx_service.client else 'disconnected',
            'ai_status': 'trained' if self.ai_enabled and ai_service.is_trained else 'not_trained'
        }
        
        return enhanced_stats

# Singleton étendu
network_scanner_enhanced = NetworkScannerEnhanced()

# Alias pour rétrocompatibilité
advanced_scanner = network_scanner_enhanced

# =============================================
# 🧪 TEST & EXEMPLE D'UTILISATION
# =============================================

def test_enhanced_scanner():
    """Test du scanner avancé"""
    print("🧪 Test du scanner avancé...")
    
    def scan_callback(status, result):
        if status == 'completed':
            print("✅ Scan avancé terminé avec succès!")
            print(f"📊 Appareils trouvés: {len(result['devices'])}")
            print(f"📈 Métriques: {result['scan_metrics']}")
            print(f"💾 InfluxDB: {result['influxdb_stats']['devices_written']} appareils enregistrés")
            print(f"🧠 IA: {result['ai_analysis']['message']}")
        elif status == 'error':
            print(f"❌ Erreur lors du scan: {result}")
    
    # Lancement asynchrone
    scanner_thread = network_scanner_enhanced.scan_network_async(
        max_scan_time=30,
        callback=scan_callback
    )
    
    print("🔄 Scan asynchrone démarré...")
    return scanner_thread

if __name__ == "__main__":
    # Test du scanner avancé si demandé
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--advanced":
        test_enhanced_scanner()
        
        # Attendre la fin du scan
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Arrêt du test")
    else:
        # Comportement normal du scanner original
        print("🚀 Scanner réseau standard")
        devices = network_scanner.scan_network()
        print(f"📋 {len(devices)} appareils trouvés")