# src/anomaly_detector.py : Module dédié à l'IA
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
import pandas as pd
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class AnomalyDetector:
    """
    Détecteur d’anomalies et prévision court terme pour des métriques système.

    - Détection d’anomalies : Isolation Forest (unsupervised).
      * Entrées : cpu_percent, ram_percent, uptime_hours (normalisées via StandardScaler).
      * Sortie : liste d’anomalies (machine_id, timestamp, type, valeur, sévérité, score).

    - Prévisions : ARIMA(1,1,1) séparé pour CPU et RAM.
      * Prépare une série temporelle resamplée à l’heure et effectue des prévisions sur N heures.
    """

    def __init__(self):
        # Standardisation des features pour stabiliser l'entraînement (moyenne=0, variance=1)
        self.scaler = StandardScaler()

        # Isolation Forest : bon détecteur générique en non-supervisé
        # - contamination=0.1 => assume 10% d'anomalies (influence le seuil interne)
        # - n_jobs=-1 pour paralléliser
        # - n_estimators=100 : compromis vitesse/variance
        self.model = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        self.is_trained = False

    def train(self, metrics_data: List[Dict]) -> bool:
        """
        Entraîne le scaler + IsolationForest sur une liste de dictionnaires de métriques.

        Exigences :
        - >= 10 points
        - Champs requis : cpu_percent, ram_percent, uptime_hours
        - Valeurs numériques finies (pas de NaN/Inf)
        """
        if not isinstance(metrics_data, list) or len(metrics_data) < 10:
            logger.warning("Invalid or insufficient data for training")
            raise ValueError("At least 10 valid metric dictionaries required")

        try:
            features = []
            for metric in metrics_data:
                if not all(key in metric for key in ['cpu_percent', 'ram_percent', 'uptime_hours']):
                    # On impose la présence du trio minimal
                    raise ValueError("Missing required fields in metric data")

                cpu = float(metric['cpu_percent'])
                ram = float(metric['ram_percent'])
                uptime = float(metric['uptime_hours'])

                # Vérification de la qualité des nombres
                if any(np.isnan(val) or np.isinf(val) for val in [cpu, ram, uptime]):
                    raise ValueError("Data contains NaN or infinite values")

                # NOTE: Pour l’instant, on n’utilise pas disk/network. TODO: envisager plus de features
                features.append([cpu, ram, uptime])

            X = np.array(features)

            # Fit du scaler sur l'ensemble d'entraînement
            X_scaled = self.scaler.fit_transform(X)

            # Entraînement du modèle d’anomalies
            self.model.fit(X_scaled)
            self.is_trained = True
            logger.info(f"Model trained successfully with {len(metrics_data)} samples")
            return True

        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            raise

    def detect_anomalies(self, metrics: List[Dict]) -> List[Dict]:
        """
        Applique le modèle entraîné aux métriques et retourne une liste d’anomalies.
        - Requiert un modèle déjà entraîné (self.is_trained = True).
        - Examine chaque point individuellement (détection online simple).
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before detection")

        if not isinstance(metrics, list) or len(metrics) == 0:
            raise ValueError("Valid non-empty list of metrics required")

        anomalies = []
        try:
            for metric in metrics:
                # On exige ces champs pour logguer et construire la sortie
                if not all(key in metric for key in ['cpu_percent', 'ram_percent', 'uptime_hours', 'machine_id', 'timestamp']):
                    logger.warning(f"Skipping invalid metric: {metric}")
                    continue

                cpu = float(metric['cpu_percent'])
                ram = float(metric['ram_percent'])
                uptime = float(metric['uptime_hours'])

                # Sauter les points douteux
                if any(np.isnan(val) or np.isinf(val) for val in [cpu, ram, uptime]):
                    continue

                features = [[cpu, ram, uptime]]

                # IMPORTANT : même scaler que celui utilisé au fit
                X_scaled = self.scaler.transform(features)

                # predict => 1 = inlier, -1 = outlier (anomalie)
                prediction = self.model.predict(X_scaled)[0]

                # score_samples => plus c'est faible, plus c'est anormal (non calibré)
                score = self.model.score_samples(X_scaled)[0]

                if prediction == -1:
                    # Heuristique pour "étiqueter" la métrique en cause
                    metric_types = []
                    if cpu > 80:
                        metric_types.append('cpu_percent')
                    if ram > 85:
                        metric_types.append('ram_percent')
                    if not metric_types:
                        # Sinon, on marque "system" (anomalie globale)
                        metric_types = ['system']

                    for metric_type in metric_types:
                        severity = self._calculate_severity(score)
                        value = metric.get(metric_type, 0)

                        anomaly = {
                            'machine_id': metric['machine_id'],
                            'timestamp': metric['timestamp'],
                            'metric_type': metric_type,
                            'value': value,
                            'severity': severity,
                            'description': self._generate_description(metric_type, value, severity),
                            'anomaly_score': float(score)  # conservé pour analyse
                        }
                        anomalies.append(anomaly)

            logger.info(f"Detected {len(anomalies)} anomalies")
            return anomalies

        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            raise

    def _calculate_severity(self, score: float) -> str:
        """
        Convertit un score (non calibré) en sévérité nominale.
        NOTE : seuils arbitraires. Meilleur choix : percentiles par machine.
        """
        if not isinstance(score, (int, float)):
            raise ValueError("Score must be a number")

        # Heuristique : plus le score_samples est bas, plus c'est anormal
        if score < -0.5:
            return 'high'
        elif score < -0.3:
            return 'medium'
        else:
            return 'low'

    def _generate_description(self, metric_type: str, value: float, severity: str) -> str:
        """
        Message lisible côté humain pour l’alerte.
        """
        if not isinstance(value, (int, float)) or not isinstance(severity, str):
            raise ValueError("Invalid value or severity types")

        descriptions = {
            'cpu_percent': f"Utilisation CPU anormale détectée: {value:.1f}% (Sévérité: {severity})",
            'ram_percent': f"Utilisation RAM anormale détectée: {value:.1f}% (Sévérité: {severity})",
            'system': f"Comportement système anormal détecté (Sévérité: {severity})"
        }
        return descriptions.get(metric_type, f"Anomalie détectée sur {metric_type}")

    def predict_trends(self, metrics: List[Dict], hours_ahead: int = 6) -> Dict:
        """
        Prévoit l'évolution CPU/RAM sur les prochaines heures via ARIMA(1,1,1).
        - Nécessite >= 5 points horodatés.
        - Resample à l’heure (moyenne) + ffill pour combler les trous.
        - Retourne forecast + tendance + un risque de surcharge heuristique.
        """
        if len(metrics) < 5:
            raise ValueError("At least 5 timestamped metrics required for prediction")

        if not isinstance(hours_ahead, int) or hours_ahead <= 0:
            raise ValueError("hours_ahead must be a positive integer")

        try:
            # Tri temporel puis DataFrame
            sorted_metrics = sorted(metrics, key=lambda x: x['timestamp'])
            df = pd.DataFrame(sorted_metrics[-50:])  # on se limite aux 50 derniers
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            # Agrégation horaire ; ffill évite des NaN post-resample
            df = df.resample('H').mean().ffill()

            predictions = {}

            # CPU
            cpu_series = df['cpu_percent']
            cpu_model = ARIMA(cpu_series, order=(1, 1, 1))
            cpu_fit = cpu_model.fit()
            cpu_forecast = cpu_fit.forecast(steps=hours_ahead)
            predictions['cpu'] = {
                'forecast': cpu_forecast.tolist(),
                'trend': (
                    'augmentant' if cpu_forecast[-1] > cpu_series[-1]
                    else 'diminuant' if cpu_forecast[-1] < cpu_series[-1]
                    else 'stable'
                ),
                # Heuristique simple ; TODO : calibrer par machine / période
                'overload_risk': (
                    'high' if any(v > 90 for v in cpu_forecast)
                    else 'medium' if any(v > 80 for v in cpu_forecast)
                    else 'low'
                )
            }

            # RAM
            ram_series = df['ram_percent']
            ram_model = ARIMA(ram_series, order=(1, 1, 1))
            ram_fit = ram_model.fit()
            ram_forecast = ram_fit.forecast(steps=hours_ahead)
            predictions['ram'] = {
                'forecast': ram_forecast.tolist(),
                'trend': (
                    'augmentant' if ram_forecast[-1] > ram_series[-1]
                    else 'diminuant' if ram_forecast[-1] < ram_series[-1]
                    else 'stable'
                ),
                'overload_risk': (
                    'high' if any(v > 95 for v in ram_forecast)
                    else 'medium' if any(v > 85 for v in ram_forecast)
                    else 'low'
                )
            }

            result = {
                'predictions': predictions,
                'hours_ahead': hours_ahead,
                'prediction_timestamp': datetime.now().isoformat()
            }
            logger.info(f"Trends predicted for {hours_ahead} hours ahead")
            return result

        except Exception as e:
            logger.error(f"Trend prediction failed: {str(e)}")
            raise
