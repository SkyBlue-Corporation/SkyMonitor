# test/conftest.py
import os
import sys
from unittest.mock import MagicMock

import pytest

# Variables d'environnement requises par app.py au moment de l'import.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("INFLUXDB_TOKEN", "test-token")
os.environ.setdefault("INFLUXDB_ORG", "test-org")
os.environ.setdefault("INFLUXDB_BUCKET", "test-bucket")

# Mock docker avant d'importer app
import types
docker_mock = MagicMock()
sys.modules['docker'] = types.SimpleNamespace(from_env=lambda: docker_mock)
