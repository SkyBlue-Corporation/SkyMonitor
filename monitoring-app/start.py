#!/usr/bin/env python3
import os
import sys
import subprocess
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

def is_venv_active():
    """Vérifie si un environnement virtuel est actif"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def check_and_install_requirements():
    """Vérifie et installe les requirements"""
    try:
        # Essayer d'importer les dépendances
        import flask
        import flask_sqlalchemy
        print("✅ Toutes les dépendances sont installées")
        return True
    except ImportError:
        print("❌ Dépendances manquantes, installation...")
        
        # Vérifier si on est dans un venv
        if not is_venv_active():
            print("\n⚠️  ATTENTION: Aucun environnement virtuel actif!")
            print("📋 Veuillez exécuter ces commandes:")
            print("   source venv/bin/activate")
            print("   pip install -r requirements.txt")
            return False
        
        try:
            # Installer les requirements
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dépendances installées avec succès")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Échec de l'installation: {e}")
            return False

def scan_host(ip, port=22, timeout=1):
    """
    Scan un hôte sur un port spécifique (SSH par défaut)
    Retourne True si le port est ouvert
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            return result == 0
    except:
        return False

def get_hostname(ip):
    """
    Tente de récupérer le nom d'hôte
    """
    try:
        hostname = socket.getfqdn(ip)
        return hostname if hostname != ip else f"host-{ip.replace('.', '-')}"
    except:
        return f"host-{ip.replace('.', '-')}"

def detect_device_type(ip, open_ports):
    """
    Détermine le type d'appareil basé sur les ports ouverts
    """
    if 22 in open_ports:  # SSH
        # Vérifier d'autres ports pour affiner la détection
        if 80 in open_ports or 443 in open_ports:  # HTTP/HTTPS
            return "server"
        elif 3389 in open_ports:  # RDP
            return "workstation"
        else:
            return "server"
    elif 3389 in open_ports:  # RDP
        return "workstation"
    elif 80 in open_ports or 443 in open_ports:  # HTTP/HTTPS
        return "server"
    else:
        return "unknown"

def scan_network(subnet="192.168.1", ports_to_scan=[22, 80, 443, 3389, 21]):
    """
    Scan le réseau pour trouver des appareils actifs
    """
    print(f"🔍 Scan du réseau {subnet}.0/24...")
    active_hosts = []
    
    def check_host(host_ip):
        open_ports = []
        for port in ports_to_scan:
            if scan_host(host_ip, port):
                open_ports.append(port)
        
        if open_ports:
            hostname = get_hostname(host_ip)
            device_type = detect_device_type(host_ip, open_ports)
            
            host_info = {
                'ip': host_ip,
                'hostname': hostname,
                'open_ports': open_ports,
                'type': device_type,
                'status': 'online'
            }
            return host_info
        return None

    # Scanner les 254 hôtes possibles
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for i in range(1, 255):
            host_ip = f"{subnet}.{i}"
            futures.append(executor.submit(check_host, host_ip))
        
        for future in futures:
            result = future.result()
            if result:
                active_hosts.append(result)
                print(f"✅ {result['ip']} - {result['hostname']} ({result['type']}) - Ports: {result['open_ports']}")

    return active_hosts

def create_network_data():
    """Crée la base de données avec les appareils réseau détectés"""
    try:
        from app import create_app, db
        from app.models import Server
        
        app = create_app()
        with app.app_context():
            db.create_all()
            
            # Vérifier si des données existent déjà
            if Server.query.count() == 0:
                print("🔄 Scan du réseau en cours...")
                
                # Déterminer le sous-réseau à scanner
                subnet = get_local_ip()
                
                # Scanner le réseau
                network_devices = scan_network(subnet)
                
                if not network_devices:
                    print("❌ Aucun appareil trouvé. Vérifiez le sous-réseau.")
                    # Ajouter un exemple local pour démonstration
                    local_device = Server(
                        name='Serveur Local',
                        ip_address='127.0.0.1',
                        status='online',
                        cpu_usage=0.0,
                        memory_usage=0.0,
                        type='server'
                    )
                    db.session.add(local_device)
                else:
                    # Ajouter les appareils détectés à la base de données
                    for device in network_devices:
                        server = Server(
                            name=device['hostname'],
                            ip_address=device['ip'],
                            status='online',
                            cpu_usage=0.0,
                            memory_usage=0.0,
                            type=device['type']
                        )
                        db.session.add(server)
                
                db.session.commit()
                print(f"✅ {len(network_devices)} appareils réseau ajoutés à la base de données")
            else:
                print("✅ Base de données déjà initialisée")
                
    except Exception as e:
        print(f"⚠️  Attention lors de la création des données: {e}")
        print("📋 Assurez-vous que:")
        print("   - Vous êtes connecté au réseau")
        print("   - Le sous-réseau est correct")
        print("   - Les ports de scan ne sont pas bloqués par un firewall")

def get_local_ip():
    """Récupère l'adresse IP locale pour déterminer le sous-réseau"""
    try:
        # Créer une socket pour déterminer l'IP locale
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            # Retourner les 3 premiers octets
            return '.'.join(local_ip.split('.')[:3])
    except:
        return "192.168.1"  # Fallback

def init_database():
    """Initialise la base de données"""
    try:
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            db.create_all()
            print("✅ Base de données initialisée")
            
            # Vérifier si des données existent
            from app.models import Server
            count = Server.query.count()
            print(f"📊 {count} appareils dans la base")
            
    except Exception as e:
        print(f"❌ Erreur initialisation DB: {e}")

def main():
    """Fonction principale"""
    print("🚀 Démarrage du système de monitoring réseau...")
    print(f"📁 Répertoire: {os.getcwd()}")
    
    # Vérifier l'environnement virtuel
    if not is_venv_active():
        print("\n" + "="*60)
        print("❌ ENVIRONNEMENT VIRTUEL NON ACTIF")
        print("="*60)
        print("\n📋 Pour corriger ce problème, exécutez ces commandes:")
        print("\n1. Créer l'environnement virtuel (une seule fois):")
        print("   python3 -m venv venv")
        print("\n2. Activer l'environnement virtuel:")
        print("   source venv/bin/activate")
        print("\n3. Installer les dépendances:")
        print("   pip install -r requirements.txt")
        print("\n4. Redémarrer ce script:")
        print("   python start.py")
        print("\n" + "="*60)
        return
    
    print(f"✅ Environnement virtuel: {sys.prefix}")
    
    # Vérifier et installer les dépendances
    if not check_and_install_requirements():
        return
    
    # Détecter le sous-réseau automatiquement
    subnet = get_local_ip()
    print(f"🌐 Sous-réseau détecté: {subnet}.0/24")
    
    # Initialiser la base de données
    init_database()
    
    # Créer les données réseau (scan automatique)
    create_network_data()
    
    # Démarrer Flask
    print("\n🌐 Démarrage du serveur Flask...")
    try:
        from run import app
        print("\n" + "="*50)
        print("✅ APPLICATION PRÊTE!")
        print("="*50)
        print("📊 Accédez à: http://localhost:5000")
        print("🔍 Scan réseau automatique activé")
        print("🛑 Pour arrêter: Ctrl+C")
        print("="*50)
        
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        print("\n🔧 Dépannage:")
        print("1. Vérifiez que tous les fichiers sont présents")
        print("2. Vérifiez la structure des dossiers")
        print("3. Vérifiez les imports dans les fichiers Python")

if __name__ == '__main__':
    main()