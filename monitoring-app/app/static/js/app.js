// Configuration de l'API
const API_BASE = '/api';

// Gestion du thème sombre/clair
function initializeTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;

    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark') {
        body.classList.add('dark-theme');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('dark-theme');
            localStorage.setItem('theme', body.classList.contains('dark-theme') ? 'dark' : 'light');
        });
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
});
