// Texte du pitch (lignes) - version française animée
const pitchLines = [
    "Il est 3h du matin. Dans le centre de données, un serveur crucial commence à surchauffer. Sans surveillance, cette alerte passerait inaperçue… Mais grâce à Skymonitor, une notification instantanée arrive sur votre tableau de bord. Vous intervenez à temps, évitant une panne critique qui aurait paralysé toute l’entreprise.",
    "",
    "Chez Sky Blue Corporation, nous savons que chaque décision compte et que chaque incident peut coûter cher. Skymonitor n’est pas juste un outil : c’est votre partenaire de confiance pour :",
    "",
    "🔒 Sécuriser vos données en détectant les anomalies avant qu’elles ne deviennent des problèmes.",
    "⚡ Réagir rapidement grâce à des alertes intelligentes et une interface intuitive.",
    "📊 Piloter votre infrastructure avec des métriques claires et centralisées.",
    "",
    "Skymonitor — la vigilance professionnelle, là où vous ne pouvez pas être."
];

/**
 * Tape les lignes en mode shell et redémarre l'animation après un délai.
 * @param {string} targetId - id de l'élément <pre>
 * @param {string} cursorId - id du curseur
 * @param {string[]} lines - lignes à taper
 * @param {number} speed - ms par caractère
 * @param {number} lineDelay - pause entre les lignes
 * @param {number} restartDelay - délai avant de relancer l'animation complète après la fin
 */
function typePitch(targetId, cursorId, lines, speed = 40, lineDelay = 700, restartDelay = 8000) {
    const out = document.getElementById(targetId);
    const cursor = document.getElementById(cursorId);
    if (!out || !cursor) return;
    let lineIndex = 0;

    function clearOutput() {
        out.textContent = '';
        cursor.style.display = 'inline-block';
    }

    function typeLine() {
        if (lineIndex >= lines.length) {
            // Fin de l'animation : garder le texte affiché un moment puis relancer
            cursor.style.display = 'inline-block';
            setTimeout(() => {
                clearOutput();
                lineIndex = 0;
                setTimeout(typeLine, 300); // redémarre après court délai
            }, restartDelay);
            return;
        }

        const text = lines[lineIndex];
        let i = 0;
        // Si la ligne est vide, insérer un retour et passer à la suivante
        if (text === '') {
            out.textContent += '\n';
            lineIndex++;
            setTimeout(typeLine, lineDelay);
            return;
        }

        const t = setInterval(() => {
            out.textContent += text.charAt(i);
            i++;
            out.scrollTop = out.scrollHeight;
            if (i >= text.length) {
                clearInterval(t);
                out.textContent += '\n';
                lineIndex++;
                setTimeout(typeLine, lineDelay);
            }
        }, speed);
    }

    // Démarre l'animation
    clearOutput();
    typeLine();
}

document.addEventListener('DOMContentLoaded', () => {
    // démarre l'animation du pitch sur la page d'accueil, replay après pause
    // vitesse ajustée pour une lecture claire : 40ms/caractère, pause ligne 700ms
    typePitch('shellPitch', 'shellCursor', pitchLines, 40, 700, 9000);
});
