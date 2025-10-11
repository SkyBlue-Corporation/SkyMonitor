import random
from datetime import datetime, timedelta

class MonitoringService:
    def scan_network(self):
        return [
            {'name': 'Serveur Web Principal', 'ip': '192.168.1.10', 'status': 'online'},
            {'name': 'Base de Données', 'ip': '192.168.1.11', 'status': 'warning'},
        ]
    
    def get_historical_metrics(self, time_range):
        return {
            'timestamps': ['00:00', '06:00', '12:00', '18:00'],
            'cpu': [25, 45, 60, 35],
            'memory': [40, 55, 70, 45],
            'storage': [30, 35, 40, 38]
        }
