import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from services.network_scan import background_discover_and_emit  # remplace par ton module réel

@pytest.fixture
def mock_scan_result():
    return {
        "results": [
            {
                "ip": "10.0.0.1",
                "ports": [{"port": 22, "state": "open"}, {"port": 80, "state": "closed"}]
            },
            {
                "ip": "10.0.0.2",
                "ports": [{"port": 443, "state": "open"}]
            }
        ]
    }

@patch("services.network_scan.socketio")
@patch("services.network_scan.write_metrics")
@patch("services.network_scan.discover_and_scan")
def test_background_emit_success(mock_scan, mock_write, mock_socketio, mock_scan_result):
    mock_scan.return_value = mock_scan_result

    background_discover_and_emit(
        network="10.0.0.0/24",
        ports=[22, 80, 443],
        parallel_hosts=2,
        scan_args="-sT -sV"
    )

    # Vérifie que scan_progress est émis pour chaque hôte
    progress_calls = [call for call in mock_socketio.emit.call_args_list if call[0][0] == "scan_progress"]
    assert len(progress_calls) == 2
    for call in progress_calls:
        assert "ip" in call[0][1]
        assert "progress" in call[0][1]

    # Vérifie que network_scan_complete est émis une fois
    complete_calls = [call for call in mock_socketio.emit.call_args_list if call[0][0] == "network_scan_complete"]
    assert len(complete_calls) == 1
    payload = complete_calls[0][0][1]
    assert payload["success"] is True
    assert "scan_time" in payload
    assert "summary" in payload

    # Vérifie que les badges sont bien ajoutés
    results = payload["summary"]["results"]
    assert "services" in results[0]
    assert "SSH" in results[0]["services"]
    assert "HTTPS" in results[1]["services"]
    # Vérifie que les métriques sont écrites
    assert mock_write.call_count == 2