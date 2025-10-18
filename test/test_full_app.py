# test/test_fast_app.py
import pytest
from unittest.mock import patch, MagicMock
import app as myapp
import psutil

# ------------------- Fixture Flask -------------------
@pytest.fixture
def client():
    myapp.app.config["TESTING"] = True
    with myapp.app.test_client() as client:
        yield client

# ------------------- Test API système -------------------
def test_system_stats_quick(client):
    """Test rapide et safe du endpoint /api/system/stats"""
    with patch("app.psutil.cpu_percent", return_value=30), \
         patch("app.psutil.virtual_memory") as mock_mem, \
         patch("app.psutil.disk_usage") as mock_disk, \
         patch("app.psutil.net_io_counters") as mock_net:

        mock_mem.return_value = MagicMock(percent=40)
        mock_disk.return_value = MagicMock(percent=50)
        mock_net.return_value = MagicMock(bytes_sent=1000, bytes_recv=2000)

        resp = client.get("/api/system/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["cpu_percent"] == 30
        assert data["memory_percent"] == 40
        assert data["disk_percent"] == 50
        assert data["net_bytes_sent"] == 1000
        assert data["net_bytes_recv"] == 2000

# ------------------- Test routes SPA -------------------
def test_routes_spa_quick(client):
    resp = client.get("/")
    assert resp.status_code == 200
    resp2 = client.get("/unknown/route")
    assert resp2.status_code == 200

# ------------------- Test SocketIO events -------------------
def test_socketio_quick():
    with patch("app.socketio.emit") as mock_emit, patch("builtins.print") as mock_print:
        myapp.handle_connect()
        mock_emit.assert_called_with("connected", {"status": "connected"})
        myapp.handle_disconnect()
        mock_print.assert_called_with("[socket] client disconnected")

# ------------------- Test scan réseau (mocké) -------------------
def test_scan_network_quick(client):
    with patch("app.socketio.start_background_task") as mock_bg, \
         patch("app.parse_ports", return_value=[22,80]):
        resp = client.post("/api/scan/network", json={"network":"192.168.1.0/24","ports":"22,80"})
        assert resp.status_code == 202
        mock_bg.assert_called_once()

# ------------------- Test Docker (mocké et sans sleep) -------------------
def test_docker_metrics_quick():
    """Test rapide de collect_docker_metrics sans Docker réel"""
    # Mock des conteneurs
    container_mock = MagicMock()
    container_mock.name = "test_container"
    container_mock.stats.return_value = {
        'cpu_stats': {'cpu_usage': {'total_usage': 1000}, 'system_cpu_usage': 2000},
        'precpu_stats': {'cpu_usage': {'total_usage': 500}, 'system_cpu_usage': 1000},
        'memory_stats': {'usage': 256*1024*1024, 'limit': 512*1024*1024}
    }

    with patch.object(myapp.docker_client, "containers") as mock_containers, \
         patch("app.write_metrics") as mock_write, \
         patch("app.socketio.emit") as mock_emit:
        
        # Simule un conteneur existant
        mock_containers.list.return_value = [container_mock]

        # Appel safe avec run_once pour tests
        myapp.collect_docker_metrics(run_once=True)

        # Vérifications
        mock_containers.list.assert_called_once()
        mock_write.assert_called_once()
        mock_emit.assert_called_once()

# ------------------- Test erreurs / scan réseau -------------------
def test_scan_network_error_handling(client):
    # Endpoint renvoie 202 même pour JSON vide
    resp = client.post("/api/scan/network", json={})
    assert resp.status_code == 202
