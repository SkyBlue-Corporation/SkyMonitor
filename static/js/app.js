// app.js

const App = {
    init() {
        console.log('🚀 Application SkyMonitor initialisée');
        this.setupGlobalEvents();
        this.setupSocketStatus();
        this.setupScanNetwork();       // 📡 Prépare l’écoute du bouton et le scan
        this.startSimulation();
    },

    // Gestion des erreurs globales
    setupGlobalEvents() {
        window.addEventListener('error', (e) => {
            console.error('Erreur globale:', e.error);
        });
        window.addEventListener('unhandledrejection', (e) => {
            console.error('Promesse rejetée:', e.reason);
        });
    },

    // Pop-ups d’info / succès / warning / erreur
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    },

    getNotificationIcon(type) {
        const icons = {
            info: 'info-circle',
            success: 'check-circle',
            warning: 'exclamation-triangle',
            error: 'times-circle'
        };
        return icons[type] || 'info-circle';
    },

    // Mise en forme utilitaires
    formatBytes(bytes) {
        const sizes = ['Bytes','KB','MB','GB','TB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
    },

    formatPercentage(value) {
        return value.toFixed(1) + '%';
    },

    // Indicateur de connexion Socket.IO
    setupSocketStatus() {
        const socket = window.socket;
        if (!socket) return;
        const indicator = document.getElementById('connection-indicator');

        socket.on('connect', () => {
            if (indicator) {
                indicator.classList.replace('disconnected','connected');
                indicator.title = 'Socket.IO: connecté';
            }
            this.showNotification('Connexion temps réel établie','success');
        });

        socket.on('disconnect', () => {
            if (indicator) {
                indicator.classList.replace('connected','disconnected');
                indicator.title = 'Socket.IO: déconnecté';
            }
            this.showNotification('Connexion temps réel perdue','warning');
        });
    },

    // → Configuration du scan réseau
    setupScanNetwork() {
        const btn = document.getElementById('launchScan');
        if (!btn) return;
        btn.addEventListener('click', () => this.launchNetworkScan());
    },

    // Lance un fetch & wires Socket.IO pour scan_progress & network_scan_complete
    launchNetworkScan() {
        const scanStatus  = document.getElementById('scan-status');
        const scanTable   = document.getElementById('scanTable');
        const tbody       = scanTable?.querySelector('tbody');
        const bar         = document.getElementById('scan-progress-bar');
        const fill        = document.getElementById('scan-progress-fill');

        if (!scanStatus || !scanTable || !tbody || !bar || !fill) return;

        // Reset UI
        scanStatus.textContent = '🔍 Scan en cours...';
        scanTable.style.display = 'none';
        tbody.innerHTML = '';
        bar.style.display = 'block';
        fill.style.width = '0%';

        fetch('/api/scan/network', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
                network: '10.236.155.0/24',
                ports: [22,80,443],
                parallel: true
            })
        })
        .then(res => {
            if (!res.ok) throw new Error('Echec du lancement du scan');
            let scanned = 0;
            const total = 256;  // /24
            window.socket.off('scan_progress');
            window.socket.off('network_scan_complete');

            window.socket.on('scan_progress', data => {
                scanned++;
                scanStatus.textContent = `📡 Scan de ${data.ip}...`;
                const pct = Math.min(100, Math.round((scanned/total)*100));
                fill.style.width = `${pct}%`;
            });

            window.socket.on('network_scan_complete', data => {
                scanStatus.textContent = `✅ Scan terminé en ${data.duration}s`;
                bar.style.display = 'none';
                scanTable.style.display = 'table';
                tbody.innerHTML = '';
                data.results.forEach(host => {
                    const badges = host.open_ports.map(p => {
                        const label = {22:'SSH',80:'HTTP',443:'HTTPS'}[p]||`Port ${p}`;
                        return `<span class="badge-port">${label}</span>`;
                    }).join(' ');
                    tbody.innerHTML += `<tr><td>${host.ip}</td><td>${badges}</td></tr>`;
                });
            });
        })
        .catch(err => {
            scanStatus.textContent = '❌ Échec du scan réseau';
            bar.style.display = 'none';
            console.error(err);
        });
    },

    // État interne pour métriques réelles + simulées
    metrics: {cpu:0,memory:0,disk:0},
    lastRealMetricsTime: 0,
    simulationInactivityMs: 7000,
    _restartTimer: null,

    applyRealMetrics(data) {
        if (data.cpu_percent  != null) this.metrics.cpu    = Number(data.cpu_percent);
        if (data.memory_percent != null) this.metrics.memory = Number(data.memory_percent);
        if (data.disk_percent != null) this.metrics.disk    = Number(data.disk_percent);
        this.lastRealMetricsTime = Date.now();
        this.stopSimulation();
        clearTimeout(this._restartTimer);
        this._restartTimer = setTimeout(() => {
            this.startSimulation();
        }, this.simulationInactivityMs);
        this.updateNavMetrics();
    },

    updateNavMetrics() {
        const cpuEl  = document.getElementById('nav-cpu-value');
        const memEl  = document.getElementById('nav-memory-value');
        const diskEl = document.getElementById('nav-disk-value');
        if (cpuEl)  cpuEl.textContent  = this.formatPercentage(this.metrics.cpu);
        if (memEl)  memEl.textContent  = this.formatPercentage(this.metrics.memory);
        if (diskEl) diskEl.textContent = this.formatPercentage(this.metrics.disk);
        const simBadge = document.getElementById('sim-badge');
        const isSim = (Date.now() - this.lastRealMetricsTime) >= this.simulationInactivityMs;
        if (simBadge) simBadge.style.display = isSim ? 'inline-block' : 'none';
    },

    // Random walk simulation
    _simInterval: null,
    startSimulation(intervalMs = 2000, staleMs = 7000) {
        if (this._simInterval) return;
        if (isNaN(this.metrics.cpu)) {
            this.metrics = {
                cpu: 5+Math.random()*10,
                memory: 20+Math.random()*20,
                disk: 30+Math.random()*20
            };
        }
        this._simInterval = setInterval(() => {
            if ((Date.now() - this.lastRealMetricsTime) < staleMs) {
                this.updateNavMetrics();
                return;
            }
            const walk = (v) => {
                let nv = v + (Math.random()-0.5)*6;
                return Math.max(0, Math.min(100, Number(nv.toFixed(1))));
            };
            this.metrics.cpu    = walk(this.metrics.cpu);
            this.metrics.memory = walk(this.metrics.memory);
            this.metrics.disk   = walk(this.metrics.disk);
            this.updateNavMetrics();
        }, intervalMs);
    },

    stopSimulation() {
        clearInterval(this._simInterval);
        this._simInterval = null;
    }
};

// Démarrage & thème
document.addEventListener('DOMContentLoaded', () => {
    App.init();

    const themeBtn = document.getElementById('theme-toggle');
    if (!themeBtn) return;
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('theme-dark');
    }
    themeBtn.addEventListener('click', () => {
        document.body.classList.toggle('theme-dark');
        localStorage.setItem(
            'theme',
            document.body.classList.contains('theme-dark') ? 'dark' : 'light'
        );
    });
});

// Expose globalement pour debug / tests
window.App = App;
