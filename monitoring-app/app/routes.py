from flask import Blueprint, render_template, jsonify, request
from app.models import Server, db
from app.services.monitoring_service import MonitoringService
from datetime import datetime, timedelta
from scanner import network_scanner

main_bp = Blueprint('main', __name__)
monitoring_service = MonitoringService()

@main_bp.route('/')
def index():
    """Page d'accueil - Hub de navigation"""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Tableau de bord principal"""
    return render_template('dashboard.html')

@main_bp.route('/serveurs')
def serveurs():
    return render_template('serveurs.html')

@main_bp.route('/postes')
def postes():
    return render_template('postes.html')

@main_bp.route('/conteneurs')
def conteneurs():
    return render_template('conteneurs.html')

@main_bp.route('/metriques')
def metriques():
    return render_template('metriques.html')

@main_bp.route('/paramètres')
def parametres():
    return render_template('paramètres.html')

# API Routes (inchangées)
@main_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """Retourne les statistiques pour le tableau de bord"""
    servers_count = Server.query.filter_by(type='server').count()
    workstations_count = Server.query.filter_by(type='workstation').count()
    containers_count = Server.query.filter_by(type='container').count()
    
    # Calcul du taux de disponibilité
    online_servers = Server.query.filter_by(status='online').count()
    total_servers = Server.query.count()
    availability_rate = (online_servers / total_servers * 100) if total_servers > 0 else 0
    
    return jsonify({
        'servers': servers_count,
        'workstations': workstations_count,
        'containers': containers_count,
        'availability_rate': round(availability_rate, 1)
    })

# ... autres routes API ...
@main_bp.route('/api/conteneurs')
def api_conteneurs():
    """API pour les données des conteneurs - Retourne du JSON"""
    try:
        # Récupère les conteneurs depuis la base de données
        containers = Server.query.filter_by(type='container').all()
        
        # Transforme en format JSON
        containers_data = []
        for container in containers:
            containers_data.append({
                'id': container.id,
                'name': container.name,
                'ip': container.ip_address,
                'status': container.status,
                'cpu_usage': container.cpu_usage,
                'memory_usage': container.memory_usage,
                'type': container.type,
                'open_ports': container.open_ports
            })
        
        return jsonify(containers_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/postes')
def api_postes():
    """API pour les postes de travail"""
    try:
        workstations = Server.query.filter_by(type='workstation').all()
        workstations_data = []
        
        for ws in workstations:
            workstations_data.append({
                'id': ws.id,
                'name': ws.name,
                'ip': ws.ip_address,
                'status': ws.status,
                'cpu_usage': ws.cpu_usage,
                'memory_usage': ws.memory_usage
            })
        
        return jsonify(workstations_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/serveurs')
def api_serveurs():
    """API pour les serveurs"""
    try:
        servers = Server.query.filter_by(type='server').all()
        servers_data = []
        
        for server in servers:
            servers_data.append({
                'id': server.id,
                'name': server.name,
                'ip': server.ip_address,
                'status': server.status,
                'cpu_usage': server.cpu_usage,
                'memory_usage': server.memory_usage
            })
        
        return jsonify(servers_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/network/scan', methods=['POST'])
def api_network_scan():
    """API pour lancer un scan réseau"""
    try:
        from scanner import network_scanner
        
        # Lance le scan
        devices = network_scanner.scan_network()
        
        # Sauvegarde en base de données
        for device in devices:
            # Vérifie si l'appareil existe déjà
            existing = Server.query.filter_by(ip_address=device['ip']).first()
            
            if existing:
                # Met à jour
                existing.status = device['status']
                existing.type = device['type']
            else:
                # Crée un nouvel appareil
                new_device = Server(
                    name=device['hostname'],
                    ip_address=device['ip'],
                    status=device['status'],
                    type=device['type'],
                    cpu_usage=0.0,
                    memory_usage=0.0
                )
                db.session.add(new_device)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Scan terminé: {len(devices)} appareils trouvés',
            'devices': devices
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500