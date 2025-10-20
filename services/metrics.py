import os
import time
from datetime import datetime
from typing import Optional

import psutil
from flask_socketio import SocketIO

# InfluxDB client must be passed in from app
influxdb_client = None
write_api = None
INFLUXDB_BUCKET = ""
socketio: Optional[SocketIO] = None

def init_metrics(influx_client, write, bucket, sio):
    global influxdb_client, write_api, INFLUXDB_BUCKET, socketio
    influxdb_client = influx_client
    write_api = write
    INFLUXDB_BUCKET = bucket
    socketio = sio

def write_metrics(measurement: str, fields: dict, tags: Optional[dict] = None):
    if not write_api or not influxdb_client:
        print(f"[METRICS-SKIP] {measurement} | fields={fields} | tags={tags}")
        return

    try:
        point = influxdb_client.Point(measurement)
        if tags:
            for k, v in tags.items():
                point = point.tag(k, v)
        for k, v in fields.items():
            point = point.field(k, v)
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    except Exception as e:
        print(f"[METRICS-ERROR] {e}")

def collect_system_metrics():
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

            tags = {"host": os.environ.get("HOSTNAME", "monitoring-server")}
            write_metrics("system_metrics", fields, tags)
            if socketio:
                socketio.emit("system_metrics", {**fields, "timestamp": datetime.now().isoformat()})
            time.sleep(5)
        except Exception as e:
            print(f"[collect_system_metrics] {e}")
            time.sleep(10)

def collect_docker_metrics(docker_client, run_once=False):
    try:
        while True:
            containers = docker_client.containers.list()
            for c in containers:
                stats = c.stats(stream=False)
                cpu_percent = 0.0
                mem_percent = 0.0

                if stats.get("cpu_stats") and stats.get("precpu_stats"):
                    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                    sys_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
                    if sys_delta > 0:
                        cpu_percent = (cpu_delta / sys_delta) * 100

                if stats.get("memory_stats"):
                    mem = stats["memory_stats"]
                    if mem.get("usage") and mem.get("limit"):
                        mem_percent = (mem["usage"] / mem["limit"]) * 100

                write_metrics(c.name, {"cpu": cpu_percent, "memory": mem_percent})
                if socketio:
                    socketio.emit("docker_metrics", {"container": c.name, "cpu": cpu_percent, "memory": mem_percent})

            if run_once:
                break
            time.sleep(5)
    except Exception as e:
        print(f"[collect_docker_metrics] {e}")
