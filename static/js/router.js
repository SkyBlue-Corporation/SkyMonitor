document.addEventListener('DOMContentLoaded', () => {
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
            // ...chargement du template, inchangé...
            const response = await fetch(path);
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const mainContent = doc.querySelector('.page-content') || doc.querySelector('main');
            if (mainContent) {
                document.getElementById('main-content').innerHTML = mainContent.innerHTML;
                this.initPageComponents(path);
            }
            const loader = document.getElementById('monitoring-loader');
            if (loader) loader.style.display = 'none';
        } catch (error) {
            this.showError('Erreur lors du chargement de la page');
            const loader = document.getElementById('monitoring-loader');
            if (loader) loader.style.display = 'none';
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
        document.getElementById('main-content').innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i><p>Chargement...</p></div>';
    }

    showError(message) {
        document.getElementById('main-content').innerHTML = '<div class="error"><i class="fas fa-exclamation-triangle"></i><h3>Erreur</h3><p>' + message + '</p><button class="btn btn-primary" onclick="window.router.navigate('/')">Retour à l\'accueil</button></div>';
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

    initHomePage() {}
    initDashboard() {}
    initServeurs() {}
    initPostes() {}
    initConteneurs() {}
    initMetriques() {}
    initParametres() {}

    // Toutes les méthodes de scan sont vides :
    loadNetworkDevices() {}
    loadServeursData() {}
    loadPostesData() {}
    loadConteneursData() {}
    loadMetricsData() {}
}


    window.router = new Router();
});
