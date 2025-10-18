# test/test_net_discovery_real.py
import pytest
from net_discovery_nmap import discover_and_scan, parse_ports

def test_discover_and_scan_local():
    """
    Test réel de discovery + scan Nmap sur le réseau local 127.0.0.1 / localhost.
    Ne lance que sur localhost pour éviter de spammer le réseau.
    """
    network = "127.0.0.1/32"  # juste la machine locale
    ports = parse_ports("22,80")  # ports à scanner
    summary = discover_and_scan(network, ports, parallel_hosts=1)

    # Vérifications simples
    assert "network" in summary
    assert summary["network"] == network
    assert "hosts_scanned" in summary
    assert summary["hosts_scanned"] >= 0
    assert "results" in summary
    assert isinstance(summary["results"], list)

    # Affiche le résumé pour contrôle manuel
    print("Résumé du scan réel :", summary)

if __name__ == "__main__":
    pytest.main([__file__])
