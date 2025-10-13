class Router {
    constructor() {
        this.routes = {
            '/': 'home',
            '/dashboard': 'dashboard',
            '/serveurs': 'serveurs',
            '/postes': 'postes',
            '/conteneurs': 'conteneurs',
            '/metriques': 'metriques',
            '/parametres': 'parametres'
        };
        
        this.init();
    }
    
    init() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-route]') || e.target.closest('[data-route]')) {
                e.preventDefault();
                const link = e.target.matches('[data-route]') ? e.target : e.target.closest('[data-route]');
                this.navigate(link.getAttribute('href'));
            }
        });
        
        window.addEventListener('popstate', () => {
            this.loadRoute(window.location.pathname);
        });
        
        this.loadRoute(window.location.pathname);
    }
    
    navigate(path) {
        history.pushState({}, '', path);
        this.loadRoute(path);
    }
    
    async loadRoute(path) {
        try {
            this.updateActiveNav(path);
            this.showLoading();
            
            const response = await fetch(path);
            const html = await response.text();
            
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const mainContent = doc.querySelector('.page-content') || doc.querySelector('main');
            
            if (mainContent) {
                document.getElementById('main-content').innerHTML = mainContent.innerHTML;
                this.initPageComponents(path);
            }
            
        } catch (error) {
            console.error('Erreur chargement route:', error);
            this.showError('Erreur lors du chargement de la page');
        }
    }
    
    updateActiveNav(path) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const activeLink = document.querySelector(`[href="${path}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }
    
    showLoading() {
        document.getElementById('main-content').innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Chargement...</p>
            </div>
        `;
    }
    
    showError(message) {
        document.getElementById('main-content').innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Erreur</h3>
                <p>${message}</p>
                <button class="btn btn-primary" onclick="window.router.navigate('/')">
                    Retour à l'accueil
                </button>
            </div>
        `;
    }
    
    initPageComponents(path) {
        switch(path) {
            case '/':
                this.initHomePage();
                break;
            case '/dashboard':
                this.initDashboard();
                break;
            case '/serveurs':
                this.initServeurs();
                break;
            case '/postes':
                this.initPostes();
                break;
            case '/conteneurs':
                this.initConteneurs();
                break;
            case '/metriques':
                this.initMetriques();
                break;
            case '/parametres':
                this.initParametres();
                break;
        }
    }
    
    initHomePage() {
        this.loadSystemStats();
        this.loadNetworkDevices();
        this.setupRealTimeUpdates();
    }
    
    initDashboard() {
        console.log('Initialisation dashboard');
    }
    
    initServeurs() {
        this.loadServeursData();
    }
    
    initPostes() {
        this.loadPostesData();
    }
    
    initConteneurs() {
        this.loadConteneursData();
    }
    
    initMetriques() {
        this.loadMetricsData();
    }
    
    initParametres() {
        console.log('Initialisation paramètres');
    }
    
    async loadSystemStats() {
        try {
            const response = await fetch('/api/system/stats');
            const data = await response.json();
            
            if (document.getElementById('cpu-value')) {
                document.getElementById('cpu-value').textContent = data.cpu_percent.toFixed(1) + '%';
                document.getElementById('memory-value').textContent = data.memory_percent.toFixed(1) + '%';
                document.getElementById('disk-value').textContent = data.disk_percent.toFixed(1) + '%';
            }
        } catch (error) {
            console.error('Erreur stats système:', error);
        }
    }
    
    async loadNetworkDevices() {
        try {
            const response = await fetch('/api/network/devices');
            const devices = await response.json();
            this.updateDevicesList(devices);
        } catch (error) {
            console.error('Erreur appareils réseau:', error);
        }
    }
    
    async loadServeursData() {
        try {
            const response = await fetch('/api/serveurs');
            const serveurs = await response.json();
            this.renderServeurs(serveurs);
        } catch (error) {
            console.error('Erreur serveurs:', error);
        }
    }
    
    async loadPostesData() {
        try {
            const response = await fetch('/api/postes');
            const postes = await response.json();
            this.renderPostes(postes);
        } catch (error) {
            console.error('Erreur postes:', error);
        }
    }
    
    async loadConteneursData() {
        try {
            const response = await fetch('/api/conteneurs');
            const conteneurs = await response.json();
            this.renderConteneurs(conteneurs);
        } catch (error) {
            console.error('Erreur conteneurs:', error);
        }
    }
    
    async loadMetricsData() {
        try {
            const response = await fetch('/api/metrics/history?range=1h');
            const metrics = await response.json();
            console.log('Métriques chargées:', metrics);
        } catch (error) {
            console.error('Erreur métriques:', error);
        }
    }
    
    updateDevicesList(devices) {
        const container = document.getElementById('devices-container');
        if (!container) return;
        
        if (devices.length === 0) {
            container.innerHTML = '<p class="no-data">Aucun appareil détecté</p>';
            return;
        }
        
        container.innerHTML = devices.map(device => `
            <div class="device-item">
                <div class="device-info">
                    <strong>${device.ip}</strong>
                    <span>${device.hostname || 'Unknown'}</span>
                </div>
                <div class="device-status ${device.status}">
                    ${device.status === 'online' ? '🟢 En ligne' : '🔴 Hors ligne'}
                </div>
            </div>
        `).join('');
    }
    
    renderServeurs(serveurs) {
        const container = document.getElementById('serveurs-container');
        if (!container) return;
        
        container.innerHTML = serveurs.map(serveur => `
            <div class="server-item">
                <h3>${serveur.name}</h3>
                <p>IP: ${serveur.ip_address}</p>
                <p>Statut: <span class="status-${serveur.status}">${serveur.status}</span></p>
                <div class="server-metrics">
                    <span>CPU: ${serveur.cpu_usage}%</span>
                    <span>RAM: ${serveur.memory_usage}%</span>
                    <span>Stockage: ${serveur.storage_usage}%</span>
                </div>
            </div>
        `).join('');
    }
    
    renderPostes(postes) {
        const container = document.getElementById('postes-container');
        if (!container) return;
        
        container.innerHTML = postes.map(poste => `
            <div class="poste-item">
                <h3>${poste.name}</h3>
                <p>IP: ${poste.ip_address}</p>
                <p>Statut: <span class="status-${poste.status}">${poste.status}</span></p>
            </div>
        `).join('');
    }
    
    renderConteneurs(conteneurs) {
        const container = document.getElementById('conteneurs-container');
        if (!container) return;
        
        container.innerHTML = conteneurs.map(conteneur => `
            <div class="conteneur-item">
                <h3>${conteneur.name}</h3>
                <p>Image: ${conteneur.image}</p>
                <p>Statut: <span class="status-${conteneur.status}">${conteneur.status}</span></p>
            </div>
        `).join('');
    }
    
    setupRealTimeUpdates() {
        if (typeof io !== 'undefined') {
            const socket = io();
            
            socket.on('system_metrics', (data) => {
                if (document.getElementById('cpu-value')) {
                    document.getElementById('cpu-value').textContent = data.cpu_percent.toFixed(1) + '%';
                    document.getElementById('memory-value').textContent = data.memory_percent.toFixed(1) + '%';
                    document.getElementById('disk-value').textContent = data.disk_percent.toFixed(1) + '%';
                }
            });
            
            socket.on('network_scan', (data) => {
                this.updateDevicesList(data.devices);
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.router = new Router();
});
