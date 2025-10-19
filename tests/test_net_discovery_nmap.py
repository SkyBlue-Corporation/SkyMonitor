import unittest
import sys
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from net_discovery_nmap import (
    ensure_nmap_installed,
    parse_ports,
    discover_hosts_nmap,
    scan_host_with_subprocess,
    discover_and_scan
)

class TestNetDiscoveryNmap(unittest.TestCase):

    def test_parse_ports_single_and_range(self):
        self.assertEqual(parse_ports("22,80,443"), [22, 80, 443])
        self.assertEqual(parse_ports("1000-1002"), [1000, 1001, 1002])
        self.assertEqual(parse_ports("22,1000-1002,443"), [22, 443, 1000, 1001, 1002])

    @patch("shutil.which", return_value="/usr/bin/nmap")
    def test_ensure_nmap_installed_true(self, mock_which):
        self.assertTrue(ensure_nmap_installed())

    @patch("shutil.which", return_value=None)
    def test_ensure_nmap_installed_false(self, mock_which):
        self.assertFalse(ensure_nmap_installed())

    @patch("subprocess.run")
    def test_discover_hosts_nmap(self, mock_run):
        mock_run.return_value = MagicMock(stdout="""
            Starting Nmap 7.80 ( https://nmap.org ) at 2025-10-19
            Nmap scan report for 192.168.1.10
            Host is up.
            Nmap scan report for 192.168.1.20
            Host is up.
        """, returncode=0)
        hosts = discover_hosts_nmap("192.168.1.0/24")
        self.assertEqual(hosts, ["192.168.1.10", "192.168.1.20"])

    @patch("subprocess.run")
    def test_scan_host_with_subprocess(self, mock_run):
        mock_run.return_value = MagicMock(stdout="""
            PORT     STATE SERVICE
            22/tcp   open  ssh
            80/tcp   open  http
        """, returncode=0)
        result = scan_host_with_subprocess("192.168.1.10", [22, 80])
        self.assertEqual(result["ip"], "192.168.1.10")
        self.assertEqual(len(result["ports"]), 2)
        self.assertEqual(result["ports"][0]["port"], 22)
        self.assertEqual(result["ports"][0]["state"], "open")

    @patch("net_discovery_nmap.discover_hosts_nmap", return_value=["192.168.1.10"])
    @patch("net_discovery_nmap.scan_host_with_subprocess")
    def test_discover_and_scan(self, mock_scan, mock_discover):
        mock_scan.return_value = {
            "ip": "192.168.1.10",
            "ports": [{"port": 22, "state": "open", "protocol": "tcp", "service": "ssh"}]
        }
        result = discover_and_scan("192.168.1.0/24", [22])
        self.assertEqual(result["hosts_scanned"], 1)
        self.assertEqual(result["results"][0]["ip"], "192.168.1.10")

if __name__ == "__main__":
    unittest.main()

@unittest.skipUnless("nmap" in sys.modules, "python-nmap not available")
@patch("net_discovery_nmap.nmap.PortScanner")
def test_scan_host_with_python_nmap(mock_portscanner):
    # Simule l'objet scanner
    mock_instance = MagicMock()
    mock_instance.scan.return_value = None
    mock_instance.all_hosts.return_value = ["192.168.1.10"]
    mock_instance.scan.return_value = None
    mock_instance.all_hosts.return_value = ["192.168.1.10"]

    # Simule scanner["192.168.1.10"]
    mock_host = MagicMock()
    mock_host.all_protocols.return_value = ["tcp"]
    mock_host.__getitem__.return_value = {
        22: {
            "state": "open",
            "name": "ssh",
            "product": "OpenSSH",
            "version": "7.9p1",
            "extrainfo": ""
        }
    }

    mock_instance.__getitem__.return_value = mock_host
    mock_portscanner.return_value = mock_instance

    from net_discovery_nmap import scan_host_with_python_nmap
    result = scan_host_with_python_nmap("192.168.1.10", [22])
    assert result["ip"] == "192.168.1.10"
    assert len(result["ports"]) == 1
    assert result["ports"][0]["port"] == 22
    assert result["ports"][0]["state"] == "open"
    assert result["ports"][0]["service"] == "ssh"
    assert result["ports"][0]["product"] == "OpenSSH"
    assert result["ports"][0]["version"] == "7.9p1"
    assert result["ports"][0]["extrainfo"] == ""