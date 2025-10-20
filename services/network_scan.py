from datetime import datetime
from typing import List, Optional

from flask_socketio import SocketIO
from net_discovery_nmap import discover_and_scan

write_metrics = None
socketio: Optional[SocketIO] = None

def init_network_scan(metrics_writer, sio):
    global write_metrics, socketio
    write_metrics = metrics_writer
    socketio = sio

def background_discover_and_emit(network: str, ports: List[int], parallel_hosts: int = 8, scan_args: str = "-sT -sV", ping_args: Optional[str] = None):
    try:
        summary = discover_and_scan(network=network, ports=ports, parallel_hosts=parallel_hosts, scan_args=scan_args, ping_args=ping_args)
    except Exception as e:
        print(f"[background_discover_and_emit] discover_and_scan error: {e}")
        if socketio:
            socketio.emit("network_scan_complete", {"success": False, "error": str(e), "scan_time": datetime.now().isoformat()})
        return

    for host in summary.get("results", []):
        ip = host.get("ip")
        ports_info = host.get("ports", []) or []
        open_count = sum(1 for p in ports_info if p.get("state") == "open" or p.get("open", False))
        if write_metrics:
            write_metrics("network_scan_host", {"open_ports": open_count}, {"ip": ip})

    if socketio:
        socketio.emit("network_scan_complete", {"success": True, "summary": summary, "scan_time": datetime.now().isoformat()})
