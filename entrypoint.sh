#!/bin/bash
set -e

# Crée le dossier logs si nécessaire (propriétaire peut être root si earlier chown failed)
mkdir -p /app/logs || true

# Option : désactiver jobs lourds en prod (test)
export DISABLE_HEAVY_TESTS=${DISABLE_HEAVY_TESTS:-true}

echo "[entrypoint] starting app (DISABLE_HEAVY_TESTS=${DISABLE_HEAVY_TESTS})"
exec "$@"
