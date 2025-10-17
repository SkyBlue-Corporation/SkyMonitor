# tests/test_net_discovery_nmap.py
from typing import List, Dict, Any
from unittest.mock import Mock

import pytest

# importe les fonctions depuis ton script
# Assure-toi que net_discovery_nmap.py est dans le même dossier racine du repo
from net_discovery_nmap import (
    parse_ports,
    discover_hosts_nmap,
    scan_host_with_subprocess,
    discover_and_scan,
    ensure_nmap_installed,
)

# -------------------------
# Tests unitaires simples
# -------------------------
def test_parse_ports_single_and_range():
    assert parse_ports("22") == [22]
    assert parse_ports("22,80,8000-8002") == [22, 80, 8000, 8001, 8002]
    assert parse_ports("  443 , 1000-1002 ") == [443, 1000, 1001, 1002]

def test_parse_ports_invalid_ignored():
    # ports out of range or empty parts are ignored
    assert parse_ports("0,70000, ,22") == [22]

# -------------------------
# Mock discovery parsing
# -------------------------
def test_discover_hosts_nmap_parsing(monkeypatch):
    # Simuler la sortie de subprocess.run pour la commande nmap -sn
    fake_stdout = """
Starting Nmap 7.80 ( https://nmap.org ) at 2025-10-16 12:00
Nmap scan report for 192.168.1.1
Host is up (0.0010s latency).
Nmap scan report for 192.168.1.5
Host is up (0.0020s latency).
Nmap done: 256 IP addresses (2 hosts up) scanned in 2.50 seconds
"""
    fake_proc = Mock()
    fake_proc.stdout = fake_stdout
    fake_proc.returncode = 0

    def fake_run(args, capture_output, text, check):
        return fake_proc

    monkeypatch.setattr("subprocess.run", fake_run)
    ips = discover_hosts_nmap("192.168.1.0/24")
    assert "192.168.1.1" in ips
    assert "192.168.1.5" in ips
    assert len(ips) == 2

# -------------------------
# Mock scan parsing (subprocess fallback)
# -------------------------
def test_scan_host_with_subprocess_parsing(monkeypatch):
    # Simuler la sortie d'un nmap -p 22,80 ip
    fake_out = """
Starting Nmap 7.80 ( https://nmap.org ) at 2025-10-16 12:10
Nmap scan report for 192.168.1.5
Host is up (0.0010s latency).
PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  closed http
MAC Address: 00:11:22:33:44:55 (Vendor)
"""
    fake_proc = Mock()
    fake_proc.stdout = fake_out
    fake_proc.returncode = 0

    def fake_run(args, capture_output, text, check):
        return fake_proc

    monkeypatch.setattr("subprocess.run", fake_run)
    res = scan_host_with_subprocess("192.168.1.5", [22, 80], scan_args="-sT -sV")
    # verify structure
    assert res["ip"] == "192.168.1.5"
    ports = res.get("ports", [])
    # one open, one closed
    assert any(p["port"] == 22 and p["state"] == "open" for p in ports)
    assert any(p["port"] == 80 and p["state"] == "closed" for p in ports)

# -------------------------
# Lightweight integration: mock discovery and scan functions
# -------------------------
def test_discover_and_scan_integration(monkeypatch):
    # mock ensure_nmap_installed to True
    monkeypatch.setattr("net_discovery_nmap.ensure_nmap_installed", lambda: True)

    # mock discover_hosts_nmap to return two IPs
    monkeypatch.setattr("net_discovery_nmap.discover_hosts_nmap", lambda network, ping_args=None: ["192.168.1.10", "192.168.1.20"])

    # prepare fake scan result for each host
    def fake_scan_host(ip, ports, scan_args="-sT -sV", timeout=300):
        return {"ip": ip, "ports": [{"port": 22, "state": "open"}], "raw": {}}

    # Patch both possible scan functions to be safe.
    monkeypatch.setattr("net_discovery_nmap.scan_host_with_python_nmap", fake_scan_host)
    monkeypatch.setattr("net_discovery_nmap.scan_host_with_subprocess", fake_scan_host)

    summary = discover_and_scan("192.168.1.0/24", [22], parallel_hosts=2)
    assert summary["hosts_scanned"] == 2
    assert len(summary["results"]) == 2
    ips = {r["ip"] for r in summary["results"]}
    assert "192.168.1.10" in ips and "192.168.1.20" in ips
    for r in summary["results"]:
        assert any(p["port"] == 22 for p in r["ports"])

