# test/conftest.py
import sys
from unittest.mock import MagicMock

import pytest

# Mock docker avant d'importer app
import types
docker_mock = MagicMock()
sys.modules['docker'] = types.SimpleNamespace(from_env=lambda: docker_mock)
