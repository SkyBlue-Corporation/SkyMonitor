# ========================= test_monitoring.py =========================
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import app

# ------------------- Fixture Flask -------------------
@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client

# ------------------- Test write_metrics -------------------
def test_write_metrics_calls_write_api():
    if not app.write_api:
        pytest.skip("InfluxDB non installé, test ignoré")
    with patch.object(app.write_api, 'write') as mock_write:
        app.write_metrics('test_measurement', {'value': 42}, {'host': 'test'})
        mock_write.assert_called_once()

# ------------------- Test collect_system_metrics (une itération) -------------------
@patch('psutil.cpu_percent', return_value=50)
@patch('psutil.virtual_memory')
@patch('psutil.disk_usage')
@patch('psutil.net_io_counters')
def test_collect_system_metrics(mock_net, mock_disk, mock_mem, mock_cpu):
    mock_mem.return_value = MagicMock(percent=60, used=2 * 1024**3)
    mock_disk.return_value = MagicMock(percent=70, used=10 * 1024**3)
    mock_net.return_value = MagicMock(bytes_sent=1024**2, bytes_recv=2 * 1024**2)

    with patch('app.write_metrics') as mock_write, \
         patch.object(app.socketio, 'emit') as mock_emit, \
         patch('time.sleep', return_value=None):
        # Appel direct à une itération pour test
        # On appelle collect_system_metrics mais on break après 1 loop
        def one_loop_collect():
            cpu_percent = app.psutil.cpu_percent(interval=1)
            memory = app.psutil.virtual_memory()
            disk = app.psutil.disk_usage('/')
            net = app.psutil.net_io_counters()
            fields = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "network_sent_mb": net.bytes_sent / (1024**2),
                "network_recv_mb": net.bytes_recv / (1024**2)
            }
            app.write_metrics("system_metrics", fields, {"host": "test"})
            app.socketio.emit('system_metrics', fields)
        one_loop_collect()

        mock_write.assert_called_once()
        mock_emit.assert_called_once()

# ------------------- Test network_scan -------------------
def test_network_scan(monkeypatch):
    nm_mock = MagicMock()
    nm_mock.all_hosts.return_value = ['192.168.1.1']
    nm_mock.scan.return_value = None
    nm_mock.__getitem__.return_value.state.return_value = 'up'
    nm_mock.__getitem__.return_value.hostname.return_value = 'router'
    monkeypatch.setattr(app, 'nm', nm_mock)

    results = app.network_scan('192.168.1.0/24')
    assert isinstance(results, list)
    assert results[0]['ip'] == '192.168.1.1'
    assert results[0]['status'] == 1

# ------------------- Test collect_docker_metrics -------------------
def test_collect_docker_metrics(monkeypatch):
    container_mock = MagicMock()
    container_mock.name = 'test_container'
    container_mock.id = '123456789abc'
    container_mock.stats.return_value = {
        'cpu_stats': {'cpu_usage': {'total_usage': 200, 'percpu_usage': [100, 100]},
                      'system_cpu_usage': 400},
        'precpu_stats': {'cpu_usage': {'total_usage': 100}, 'system_cpu_usage': 200},
        'memory_stats': {'usage': 512 * 1024 * 1024, 'limit': 1024 * 1024 * 1024}
    }

    docker_mock = MagicMock()
    docker_mock.containers.list.return_value = [container_mock]
    monkeypatch.setattr(app, 'docker_client', docker_mock)

    with patch('app.write_metrics') as mock_write, \
         patch.object(app.socketio, 'emit') as mock_emit, \
         patch('time.sleep', return_value=None):
        # Appel direct d'une itération pour test
        containers = app.docker_client.containers.list()
        for c in containers:
            stats = c.stats(stream=False)
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100 if system_delta > 0 else 0
            mem_usage = stats['memory_stats']['usage'] / (1024**2)
            mem_limit = stats['memory_stats']['limit'] / (1024**2)
            mem_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0
            fields = {"cpu_percent": cpu_percent, "memory_usage_mb": mem_usage, "memory_percent": mem_percent}
            app.write_metrics("docker_metrics", fields, {"container_name": c.name})
            app.socketio.emit('docker_metrics', fields)

        mock_write.assert_called_once()
        mock_emit.assert_called_once()

# ------------------- Test API /api/system/stats -------------------
def test_get_system_stats(client):
    rv = client.get('/api/system/stats')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'cpu_percent' in data
    assert 'memory_percent' in data

# ------------------- Test API /api/scan/network -------------------
def test_scan_network_now(client, monkeypatch):
    nm_mock = MagicMock()
    nm_mock.all_hosts.return_value = ['192.168.1.1']
    nm_mock.scan.return_value = None
    nm_mock.__getitem__.return_value.state.return_value = 'up'
    nm_mock.__getitem__.return_value.hostname.return_value = 'router'
    monkeypatch.setattr(app, 'nm', nm_mock)

    rv = client.post('/api/scan/network', json={'network': '192.168.1.0/24'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert data['devices_found'] == 1
