## SkyMonitor — Copilot instructions for code edits

Keep this short and specific. Use these facts when editing or extending the codebase.

- Big picture: Flask single-process web app (SPA) that collects system and container metrics, runs network discovery (nmap) and writes to InfluxDB; Grafana is provisioned in `grafana/provisioning` for dashboards. Key services are defined in `docker-compose.yml` (web, influxdb, grafana).

- Key files to inspect when changing behavior:
  - `app.py` — main Flask app, Socket.IO integration, background collectors, API endpoints. Many behaviors (metrics, scans) are implemented here.
  - `net_discovery_nmap.py` — discovery + nmap scanning logic. Contains `discover_and_scan`, `parse_ports`, subprocess fallback and Influx push helper.
  - `Dockerfile`, `docker-compose.yml` — how the app is packaged and what runtime capabilities (eg. NET_RAW) are required.
  - `requirements.txt` — exact Python dependencies (install these in the environment used for running tests).
  - `tests/` — unit tests show how to mock globals and background tasks; use them as living examples.
  - `grafana/provisioning/` — grafana dashboards and datasource provisioning (edit carefully).

- Runtime & dev workflows (concrete commands):
  - Local dev / full stack: `./deploy.sh` (project ships a helper that uses docker-compose). Alternatively `docker-compose up --build`.
  - Run unit tests: `make test` or `pytest -v` (tests rely on patching globals; avoid starting real network scans in tests).
  - Run the nmap helper standalone: `python3 net_discovery_nmap.py --network 192.168.1.0/24 --ports 22,80 --json` (requires `nmap` binary installed).

- Environment knobs (important when changing config):
  - INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET — enable real Influx writes.
  - ENV=production enables production async_mode in Socket.IO (Eventlet/gevent recommended).
  - SECRET_KEY, PORT, NETWORK_CIDR — other runtime switches.

- Project-specific patterns and gotchas (extracted from code):
  - Optional dependencies: `influxdb_client`, `docker`, and `python-nmap` are imported conditionally. Code paths are defensive — tests patch these globals. When adding features, follow the optional import pattern used in `app.py` and `net_discovery_nmap.py`.
  - Metrics writing: use `write_metrics(measurement, fields, tags)` from `app.py`. If Influx client isn't configured, it prints a concise `[METRICS-SKIP]` line instead of failing — tests rely on this fallback.
  - Background work: start long-running tasks with `socketio.start_background_task(func, ...)`. Tests call background functions directly with `run_once=True` when supported (see `collect_docker_metrics`).
  - Network scanning: `parse_ports("22,80,8000-8010")` returns a sorted list; modify only `net_discovery_nmap.parse_ports` if changing port parsing semantics.
  - Docker in compose uses `network_mode: "host"` and `cap_add: [NET_RAW, NET_ADMIN]` — changes may require extra runtime privileges.

- Tests / mocking conventions (use these examples):
  - Tests import `app` and patch module globals: `write_api`, `docker_client`, `discover_and_scan`, `parse_ports`, `nm`. The `__all__` list in `app.py` exposes these names.
  - Use Flask test client: `app.test_client()` and set `app.config['TESTING']=True`.
  - For Socket.IO behavior tests, patch `app.socketio.emit` or `app.socketio.start_background_task`.

- Integration notes:
  - `net_discovery_nmap.discover_and_scan` will raise if the `nmap` binary is missing; the CLI script documents this. When implementing network-related features add graceful error messages and keep the API endpoints returning 202 for background starts.
  - Grafana provisioning files (in `grafana/provisioning`) are applied by the Grafana container on startup — edit them and test with a fresh container.

- Suggested short prompts for the agent when editing this repo:
  1) "Change network scan behavior: update `net_discovery_nmap.parse_ports` and add a unit test in `tests/test_net_discovery_nmap.py` that verifies ranges and invalid inputs." 
 2) "Add a new Socket.IO event: implement server emit in `app.py`, update frontend consumer in `static/js/app.js`, and add a test that patches `app.socketio.emit`."

If any section is unclear or you want more examples (tests, API sample payloads, or how to run the full stack locally), tell me which area to expand and I'll iterate.
