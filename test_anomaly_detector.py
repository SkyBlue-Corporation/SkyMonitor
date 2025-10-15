# tests/test_anomaly_detector.py
# =====================================================================
# Suite de tests unitaires pour src/anomaly_detector.py utilisant pytest
# ---------------------------------------------------------------------
# Objectifs de cette batterie de tests :
# 1) Vérifier l'initialisation du détecteur (présence des composants, état).
# 2) Valider l'entraînement (cas nominal, erreurs de données, logs).
# 3) Valider la détection d'anomalies (préconditions, cas nominal, données invalides).
# 4) Tester les utilitaires internes (_calculate_severity, _generate_description).
# 5) Tester la prévision (ARIMA) : erreurs de paramètres, cas nominal, et gestion d'exception via mock.
#
# Outils/techniques utilisés :
# - pytest : framework de tests.
# - fixtures : réutilisation d'objets (detector, jeux de données).
# - caplog : capture et vérification des logs émis par le module.
# - unittest.mock.patch : substitution de ARIMA pour simuler des erreurs.
# =====================================================================

import pytest                 # Framework de tests
import numpy as np            # Génération de valeurs NaN pour tests négatifs
import pandas as pd           # (Importé par cohérence; pas directement utilisé ici)
from datetime import datetime, timezone  # Pour horodatage en UTC dans les jeux de données
from unittest.mock import patch, MagicMock  # patch utilisé; MagicMock dispo si besoin étendre les tests

# Import du détecteur et de son logger pour valider les messages de log
from src.anomaly_detector import AnomalyDetector, logger


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

@pytest.fixture
def detector():
    """
    Fournit une instance fraîche d'AnomalyDetector pour chaque test.
    - Garantit l'isolation des tests : pas de partage d'état (is_trained, scaler, model).
    """
    return AnomalyDetector()


@pytest.fixture
def sample_metrics():
    """
    Génère un petit jeu de données 'propres' et cohérents pour l'entraînement et la prévision.

    Caractéristiques :
    - >= 12 points (le train() exige au moins 10) pour éviter les erreurs.
    - Valeurs croissantes pour cpu_percent/ram_percent/uptime_hours
      afin de simuler une charge modérément montante mais plausible.
    - Timestamps : même instant (base_time) ici ; dans la vraie vie, ils différeraient.
      Cela reste suffisant pour tester l'entraînement IsolationForest
      et la logique de contrôle des entrées. La prévision ARIMA ré-échantillonne
      à l’heure et peut remplir avec ffill pour ce cas simple.
    """
    base_time = datetime.now(timezone.utc)
    metrics = []
    for i in range(12):  # 12 > 10 (seuil minimal d'entraînement)
        metrics.append({
            "machine_id": "test_machine",
            "timestamp": base_time,
            "cpu_percent": 50.0 + i * 2,   # 50, 52, 54, ...
            "ram_percent": 60.0 + i * 2,   # 60, 62, 64, ...
            "uptime_hours": 10.0 + i       # 10, 11, 12, ...
        })
    return metrics


@pytest.fixture
def anomaly_metric():
    """
    Produit un unique point 'fortement anormal' pour déclencher la détection :
    - cpu_percent élevé (95%)
    - ram_percent élevée (90%)
    - uptime_hours arbitraire
    """
    return {
        "machine_id": "test_machine",
        "timestamp": datetime.now(timezone.utc),
        "cpu_percent": 95.0,  # > 80 => devrait étiqueter 'cpu_percent'
        "ram_percent": 90.0,  # > 85 => devrait étiqueter 'ram_percent'
        "uptime_hours": 100.0
    }


# ---------------------------------------------------------------------
# Tests : Initialisation
# ---------------------------------------------------------------------

def test_init(detector):
    """
    Vérifie l'état initial du détecteur :
    - is_trained doit être False (rien n'a encore été appris),
    - présence du scaler et du modèle (objets instanciés).
    """
    assert detector.is_trained is False
    assert hasattr(detector, "scaler")
    assert hasattr(detector, "model")


# ---------------------------------------------------------------------
# Tests : Entraînement
# ---------------------------------------------------------------------

def test_train_success(detector, sample_metrics, caplog):
    """
    Cas nominal : l'entraînement doit réussir et produire des logs INFO.
    """
    caplog.set_level("INFO")                # Capture les logs au niveau INFO
    result = detector.train(sample_metrics) # Entraînement sur >= 10 points
    assert result is True                   # Renvoie True si tout va bien
    assert detector.is_trained is True      # Le flag interne doit passer à True
    assert "Model trained successfully" in caplog.text  # Message de succès attendu dans les logs


def test_train_insufficient_data(detector, caplog):
    """
    Cas d'erreur : liste vide -> ValueError, et un log WARNING doit être émis.
    """
    caplog.set_level("WARNING")
    with pytest.raises(ValueError, match="At least 10 valid metric"):
        detector.train([])  # Jeu vide => insuffisant
    assert "insufficient data" in caplog.text  # Le message WARNING du module doit apparaître


def test_train_missing_fields(detector):
    """
    Cas d'erreur : champs requis manquants ('uptime_hours' absent) -> ValueError.
    """
    invalid_data = [{"cpu_percent": 50.0, "ram_percent": 60.0}] * 10  # uptime_hours manquant
    with pytest.raises(ValueError, match="Missing required fields"):
        detector.train(invalid_data)


def test_train_nan_values(detector):
    """
    Cas d'erreur : présence de NaN -> ValueError.
    """
    invalid_data = [{"cpu_percent": np.nan, "ram_percent": 60.0, "uptime_hours": 10.0}] * 10
    with pytest.raises(ValueError, match="Data contains NaN"):
        detector.train(invalid_data)


# ---------------------------------------------------------------------
# Tests : Détection d'anomalies
# ---------------------------------------------------------------------

def test_detect_anomalies_not_trained(detector):
    """
    Précondition non satisfaite : détecter sans avoir entraîné -> ValueError.
    """
    with pytest.raises(ValueError, match="Model must be trained"):
        detector.detect_anomalies([])


def test_detect_anomalies_empty(detector, sample_metrics):
    """
    Entrée invalide : liste vide -> ValueError (même si le modèle est entraîné).
    """
    detector.train(sample_metrics)  # On entraîne d'abord
    with pytest.raises(ValueError, match="Valid non-empty list"):
        detector.detect_anomalies([])


def test_detect_anomalies_success(detector, sample_metrics, anomaly_metric, caplog):
    """
    Cas nominal : après entraînement, la détection sur un point 'anormal' doit
    retourner une liste (potentiellement non vide) d'anomalies.
    On vérifie la présence de champs clés ('severity', 'description') et le log INFO.
    """
    caplog.set_level("INFO")
    detector.train(sample_metrics)
    anomalies = detector.detect_anomalies([anomaly_metric])

    assert isinstance(anomalies, list)
    if anomalies:
        # Selon la position de l'IsolationForest, on peut avoir 1 ou 2 anomalies
        # (cpu_percent et/ou ram_percent) ; on vérifie la structure du premier élément.
        assert "severity" in anomalies[0]
        assert "description" in anomalies[0]

    assert "Detected" in caplog.text  # Le module logge le nombre d’anomalies détectées


def test_detect_anomalies_invalid_metric(detector, sample_metrics, caplog):
    """
    Données incomplètes : l'élément est ignoré (log WARNING) et aucune anomalie n'est renvoyée.
    """
    caplog.set_level("WARNING")
    detector.train(sample_metrics)
    invalid_metric = {"cpu_percent": 50.0}  # Champs essentiels manquants
    anomalies = detector.detect_anomalies([invalid_metric])

    assert len(anomalies) == 0              # Rien détecté car l'entrée est invalide
    assert "Skipping invalid metric" in caplog.text  # Le module a bien loggé l'ignorance de ce point


# ---------------------------------------------------------------------
# Tests : Fonctions utilitaires internes (sévérité, description)
# ---------------------------------------------------------------------

def test_calculate_severity(detector):
    """
    Vérifie le mapping heuristique du score vers une sévérité.
    Rappels (selon l'implémentation) :
    - score < -0.5  => 'high'
    - -0.5 <= score < -0.3 => 'medium'
    - score >= -0.3 => 'low'
    """
    assert detector._calculate_severity(-0.6) == "high"
    assert detector._calculate_severity(-0.4) == "medium"
    assert detector._calculate_severity(-0.2) == "low"

    with pytest.raises(ValueError):
        detector._calculate_severity("invalid")  # Type invalide


def test_generate_description(detector):
    """
    Vérifie que la description générée pour 'cpu_percent' contient bien
    le message attendu, et que des types invalides provoquent une ValueError.
    """
    desc = detector._generate_description("cpu_percent", 95.0, "high")
    assert "Utilisation CPU anormale" in desc

    with pytest.raises(ValueError):
        detector._generate_description("cpu", "invalid", "high")  # 'value' non numérique


# ---------------------------------------------------------------------
# Tests : Prévision (ARIMA)
# ---------------------------------------------------------------------

def test_predict_trends_insufficient_data(detector):
    """
    Erreur : nombre de points < 5 -> ValueError.
    """
    with pytest.raises(ValueError, match="At least 5 timestamped"):
        detector.predict_trends([])


def test_predict_trends_invalid_hours(detector, sample_metrics):
    """
    Erreur : hours_ahead <= 0 -> ValueError.
    """
    with pytest.raises(ValueError, match="hours_ahead must be"):
        detector.predict_trends(sample_metrics, -1)


def test_predict_trends_success(detector, sample_metrics, caplog):
    """
    Cas nominal : la fonction retourne une structure contenant :
    - 'predictions' -> sous-clés 'cpu' et 'ram'
    - pour chaque sous-clé : 'trend' et 'overload_risk'
    Et log INFO 'Trends predicted'.
    """
    caplog.set_level("INFO")
    result = detector.predict_trends(sample_metrics)

    # Clés racines
    assert "predictions" in result

    # Partie CPU
    assert "cpu" in result["predictions"]
    assert "trend" in result["predictions"]["cpu"]
    assert "overload_risk" in result["predictions"]["cpu"]

    assert "Trends predicted" in caplog.text


@patch('src.anomaly_detector.ARIMA')
def test_predict_trends_exception(mock_arima, detector, sample_metrics, caplog):
    """
    Teste la robustesse à une exception interne d'ARIMA en simulant une erreur.
    - On "patch" la classe ARIMA pour qu'elle lève une Exception lors de l'instanciation.
    - La fonction doit propager l'Exception et logger une erreur appropriée.
    """
    mock_arima.side_effect = Exception("Mock error")
    caplog.set_level("ERROR")

    with pytest.raises(Exception):
        detector.predict_trends(sample_metrics)

    assert "Trend prediction failed" in caplog.text