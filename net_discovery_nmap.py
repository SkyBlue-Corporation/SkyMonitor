"""
net_discovery_nmap.py

Découverte d'hôtes + scan via nmap.
Usage:
    sudo python3 net_discovery_nmap.py --network 192.168.1.0/24 --ports 22,80,443 --json
Notes:
 - Installez nmap sur l'hôte (apt install nmap / apk add nmap / pacman -S nmap).
 - pip install python-nmap influxdb-client
 - Si vous n'avez pas python-nmap, le script utilisera subprocess nmap.
 - Pour un scan SYN (-sS) vous avez besoin des droits root ; le script utilise par défaut -sT (connect scan) non-root.
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import shutil
import subprocess
import sys
import os

# Optional: python-nmap wrapper
try:
    import nmap  # type: ignore
    NM_AVAILABLE = True
except Exception:
    NM_AVAILABLE = False

# Optional influx
INFLUX_AVAILABLE = False
try:
    from influxdb_client import InfluxDBClient, Point, WriteOptions  # type: ignore
    INFLUX_AVAILABLE = True
except Exception:
    INFLUX_AVAILABLE = False

def ensure_nmap_installed() -> bool:
    """Vérifie que la commande nmap est disponible."""
    return shutil.which("nmap") is not None

def discover_hosts_nmap(network: str, ping_args: Optional[str] = None) -> List[str]:
    """
    Découverte d'hôtes via nmap -sn (ping scan). Retourne liste d'IPs vivantes.
    ping_args permet d'ajouter des options supplémentaires (ex: '-PR' pour ARP)
    """
    if not ensure_nmap_installed():
        raise RuntimeError("nmap non installé. Installez 'nmap' via votre gestionnaire de paquets.")
    args = ["nmap", "-sn", network]
    if ping_args:
        args = ["nmap"] + ping_args.split() + ["-sn", network]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=True)
        out = proc.stdout
        ips = []
        # Recherche simple d'IPs "Nmap scan report for 192.168.1.5"
        for line in out.splitlines():
            if line.strip().startswith("Nmap scan report for"):
                parts = line.split()
                ip = parts[-1].strip("()")
                ips.append(ip)
        return ips
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erreur discovery nmap: {e.stderr or e.stdout}")

def scan_host_with_python_nmap(ip: str, ports: List[int], scan_args: str = "-sT -sV", timeout: int = 300) -> Dict[str, Any]:
    """Utilise python-nmap (wrapper) pour scanner un hôte."""
    scanner = nmap.PortScanner()
    ports_str = ",".join(str(p) for p in ports)
    # Ex: -sT (connect), -sV (service/version)
    try:
        scanner.scan(ip, ports_str, arguments=scan_args, timeout=timeout)
    except Exception as e:
        return {"ip": ip, "error": f"nmap scan failed: {e}"}
    result = {"ip": ip, "ports": [], "raw": {}}
    if ip in scanner.all_hosts():
        host = scanner[ip]
        for proto in host.all_protocols():
            lports = sorted(host[proto].keys())
            for p in lports:
                state = host[proto][p]["state"]
                name = host[proto][p].get("name") or ""
                product = host[proto][p].get("product") or ""
                version = host[proto][p].get("version") or ""
                extra = host[proto][p].get("extrainfo") or ""
                result["ports"].append({
                    "port": p,
                    "protocol": proto,
                    "state": state,
                    "service": name,
                    "product": product,
                    "version": version,
                    "extrainfo": extra
                })
    result["raw"] = scanner[ip] if ip in scanner.all_hosts() else {}
    return result

def scan_host_with_subprocess(ip: str, ports: List[int], scan_args: str = "-sT -sV") -> Dict[str, Any]:
    """Fallback : utilise subprocess nmap et parse minimal."""
    ports_str = ",".join(str(p) for p in ports)
    args = ["nmap"] + scan_args.split() + ["-p", ports_str, ip]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=True)
        out = proc.stdout
        ports_info = []
        for line in out.splitlines():
            # ligne de table ex: "22/tcp open  ssh"
            if "/tcp" in line or "/udp" in line:
                parts = line.split()
                if len(parts) >= 3:
                    port_proto = parts[0]
                    state = parts[1]
                    service = parts[2]
                    pp = port_proto.split("/")[0]
                    try:
                        portnum = int(pp)
                    except:
                        continue
                    ports_info.append({
                        "port": portnum,
                        "protocol": "tcp" if "/tcp" in port_proto else "udp",
                        "state": state,
                        "service": service,
                        "raw": line.strip()
                    })
        return {"ip": ip, "ports": ports_info, "raw_output": out}
    except subprocess.CalledProcessError as e:
        return {"ip": ip, "error": f"nmap subprocess failed: {e.stderr or e.stdout}"}

def push_to_influx(results: Dict[str, Any], influx_url: str, token: str, org: str, bucket: str):
    """Exemple simple d'envoi: mesure host_scan avec tag ip et champ open_ports_count"""
    if not INFLUX_AVAILABLE:
        print("[!] influxdb-client non installé. Ignoring influx push.")
        return
    client = InfluxDBClient(url=influx_url, token=token, org=org)
    write_api = client.write_api(write_options=WriteOptions(batch_size=1))
    for host in results.get("results", []):
        open_count = sum(1 for p in host.get("ports", []) if p.get("state","") == "open" or p.get("open", False))
        point = Point("host_scan").tag("ip", host["ip"]).field("open_ports", open_count).time(time.time_ns())
        write_api.write(bucket=bucket, record=point)
    client.close()

def parse_ports(ports_str: str) -> List[int]:
    ports = set()
    for part in ports_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            ports.update(range(int(a), int(b)+1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 1 <= p <= 65535)

def discover_and_scan(network: str, ports: List[int], parallel_hosts: int = 8, scan_args: str = "-sT -sV", ping_args: Optional[str] = None) -> Dict[str, Any]:
    if not ensure_nmap_installed():
        raise RuntimeError("nmap non installé sur le système. Installez 'nmap' d'abord.")
    start = time.time()
    # 1) découverte d'hôtes
    hosts = discover_hosts_nmap(network, ping_args=ping_args)
    if not hosts:
        return {"network": network, "hosts_scanned": 0, "results": [], "elapsed_seconds": time.time() - start}

    results = []
    # 2) scan en parallèle par host
    with ThreadPoolExecutor(max_workers=parallel_hosts) as ex:
        futures = {}
        for ip in hosts:
            if NM_AVAILABLE:
                futures[ex.submit(scan_host_with_python_nmap, ip, ports, scan_args)] = ip
            else:
                futures[ex.submit(scan_host_with_subprocess, ip, ports, scan_args)] = ip
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"ip": ip, "error": str(e)}
            results.append(res)
    elapsed = time.time() - start
    return {"network": network, "hosts_scanned": len(hosts), "results": results, "elapsed_seconds": elapsed}

def main():
    parser = argparse.ArgumentParser(description="Discovery + nmap scan (SkyMonitor nmap helper)")
    parser.add_argument("--network", "-n", required=True, help="CIDR réseau ex: 192.168.1.0/24")
    parser.add_argument("--ports", "-p", default="22,80,443", help="Ports ou plages: 22,80,8000-8010")
    parser.add_argument("--parallel", type=int, default=8, help="Hôtes scannés en parallèle")
    parser.add_argument("--scan-args", default="-sT -sV", help="Arguments nmap pour le scan (ex: '-sT -sV')")
    parser.add_argument("--ping-args", default=None, help="Args nmap pour la découverte si besoin (ex: '-PR' pour ARP)")
    parser.add_argument("--json", action="store_true", help="Sauvegarder la sortie JSON (scan_results_nmap.json)")
    parser.add_argument("--influx", action="store_true", help="Envoyer résultats vers InfluxDB (config via env vars)")
    args = parser.parse_args()

    ports = parse_ports(args.ports)
    print(f"[i] Network: {args.network} | Ports: {ports[:10]}{'...' if len(ports)>10 else ''}")
    try:
        summary = discover_and_scan(args.network, ports, parallel_hosts=args.parallel, scan_args=args.scan_args, ping_args=args.ping_args)
    except Exception as e:
        print(f"[!] Erreur: {e}")
        sys.exit(1)

    print(f"\nScan terminé en {summary['elapsed_seconds']:.2f}s — hôtes trouvés: {summary['hosts_scanned']}\n")
    for host in summary["results"]:
        if host.get("error"):
            print(f"- {host.get('ip')} ERROR: {host.get('error')}")
            continue
        open_ports = [p for p in host.get("ports", []) if p.get("state","") == "open" or p.get("open", False)]
        print(f"- {host['ip']}  open_ports={len(open_ports)}")
        for p in open_ports:
            svc = p.get("service") or p.get("product") or ""
            ver = p.get("version") or ""
            raw = p.get("raw", "")
            print(f"    -> {p['port']}/{p.get('protocol','tcp')}  {svc} {ver} {raw}")

    if args.json:
        fname = "scan_results_nmap.json"
        with open(fname, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"[i] Résultats sauvegardés dans {fname}")

    if args.influx:
        # récupère config depuis env vars
        INFLUX_URL = os.getenv("INFLUX_URL")
        INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
        INFLUX_ORG = os.getenv("INFLUX_ORG")
        INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
        if not all([INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET]):
            print("[!] Variables Influx manquantes: INFLUX_URL / INFLUX_TOKEN / INFLUX_ORG / INFLUX_BUCKET")
        else:
            try:
                push_to_influx(summary, INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET)
                print("[i] Données envoyées vers InfluxDB.")
            except Exception as e:
                print(f"[!] Envoi Influx échoué: {e}")

if __name__ == "__main__":
    main()

