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