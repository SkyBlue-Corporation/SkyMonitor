#!/usr/bin/env python3
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from datetime import datetime
import logging

class InfluxService:
    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self.bucket = "network_monitoring"
        self.org = "skywatch"
        self.setup_connection()
    
    def setup_connection(self):
        """Établit la connexion à InfluxDB"""
        try:
            # Configuration via variables d'environnement
            url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
            token = os.getenv('INFLUXDB_TOKEN', 'your-admin-token')
            
            self.client = InfluxDBClient(url=url, token=token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            logging.info("✅ Connecté à InfluxDB")
            
        except Exception as e:
            logging.error(f"❌ Erreur connexion InfluxDB: {e}")
            self.client = None
    
    def write_device_metrics(self, device_data):
        """Écrit les métriques d'un appareil dans InfluxDB"""
        if not self.client:
            return False
            
        try:
            point = (
                Point("network_devices")
                .tag("device_ip", device_data['ip'])
                .tag("device_type", device_data['type'])
                .tag("hostname", device_data['hostname'])
                .field("status", 1 if device_data['status'] == 'online' else 0)
                .field("response_time", device_data.get('response_time', 0))
                .field("open_ports_count", len(device_data.get('open_ports', [])))
                .field("cpu_usage", device_data.get('cpu_usage', 0))
                .field("memory_usage", device_data.get('memory_usage', 0))
                .time(datetime.utcnow())
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            return True
            
        except Exception as e:
            logging.error(f"❌ Erreur écriture InfluxDB: {e}")
            return False
    
    def write_scan_metrics(self, scan_data):
        """Écrit les métriques de scan global"""
        if not self.client:
            return False
            
        try:
            point = (
                Point("network_scans")
                .tag("scan_type", "full")
                .field("total_devices", scan_data['total_devices'])
                .field("online_devices", scan_data['online_devices'])
                .field("scan_duration", scan_data.get('scan_duration', 0))
                .field("devices_workstation", scan_data.get('workstations', 0))
                .field("devices_server", scan_data.get('servers', 0))
                .field("devices_container", scan_data.get('containers', 0))
                .time(datetime.utcnow())
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            return True
            
        except Exception as e:
            logging.error(f"❌ Erreur écriture scan InfluxDB: {e}")
            return False
    
    def get_device_history(self, device_ip, hours=24):
        """Récupère l'historique d'un appareil"""
        if not self.client:
            return []
            
        try:
            query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "network_devices")
            |> filter(fn: (r) => r.device_ip == "{device_ip}")
            |> aggregateWindow(every: 1m, fn: mean)
            '''
            
            result = self.query_api.query(query)
            return self._parse_query_result(result)
            
        except Exception as e:
            logging.error(f"❌ Erreur requête InfluxDB: {e}")
            return []
    
    def get_network_stats(self, hours=24):
        """Récupère les statistiques du réseau"""
        if not self.client:
            return {}
            
        try:
            query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "network_scans")
            |> last()
            '''
            
            result = self.query_api.query(query)
            return self._parse_query_result(result)
            
        except Exception as e:
            logging.error(f"❌ Erreur stats InfluxDB: {e}")
            return {}
    
    def _parse_query_result(self, result):
        """Parse les résultats de requête InfluxDB"""
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    'time': record.get_time(),
                    'measurement': record.get_measurement(),
                    'field': record.get_field(),
                    'value': record.get_value(),
                    'tags': record.values
                })
        return data
    
    def close(self):
        """ connexion fermer"""
        if self.client:
            self.client.close()

# Singleton
influx_service = InfluxService()