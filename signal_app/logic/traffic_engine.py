"""
Centralized Traffic Engine for Smart Adaptive Traffic Signal System.

Handles:
1. Database-driven vehicle type weighting.
2. Centralized traffic density classification.
3. Adaptive green light duration calculation.
4. Priority score calculation with anti-starvation mechanism.
"""

from signal_app.models import VehicleTypeConfig


class TrafficEngine:
    """
    Core algorithmic engine for calculating density, priority, and timing.
    """

    # Signal timing boundaries (in seconds)
    MIN_GREEN = 10
    MAX_GREEN = 60
    BASE_GREEN = 10
    YELLOW_TIME = 3
    MIN_RED = 10

    # Starvation prevention weighting: score bonus per second of waiting
    STARVATION_RATE = 0.35

    def __init__(self):
        self.default_weights = {
            'two_wheeler': 0.5,
            'four_wheeler': 1.0,
            'heavy_vehicle': 2.5,
            'emergency_vehicle': 100.0,
        }

    def get_weight(self, vehicle_type):
        """
        Fetch vehicle weight multiplier from database or fallback to defaults.
        """
        try:
            config = VehicleTypeConfig.objects.filter(vehicle_type=vehicle_type).first()
            if config:
                return float(config.weight)
        except Exception:
            pass
        return self.default_weights.get(vehicle_type, 1.0)

    def calculate_weighted_density(self, counts):
        """
        Calculate weighted density score from vehicle counts dictionary.
        Supports both raw YOLO labels and DB categories.
        Args:
            counts: dict e.g. {'car': 5, 'motorcycle': 2, ...} or {'two_wheeler': 2, ...}
        Returns:
            float: Weighted traffic density score
        """
        # Map YOLO class names to DB categories if needed
        two_wheelers = counts.get('two_wheeler', 0) + counts.get('motorcycle', 0) + counts.get('bicycle', 0)
        four_wheelers = counts.get('four_wheeler', 0) + counts.get('car', 0)
        heavy_vehicles = counts.get('heavy_vehicle', 0) + counts.get('bus', 0) + counts.get('truck', 0)
        emergency_vehicles = counts.get('emergency_vehicle', 0) + counts.get('emergency', 0)

        score = (
            (two_wheelers * self.get_weight('two_wheeler')) +
            (four_wheelers * self.get_weight('four_wheeler')) +
            (heavy_vehicles * self.get_weight('heavy_vehicle')) +
            (emergency_vehicles * self.get_weight('emergency_vehicle'))
        )
        return round(score, 2)

    @classmethod
    def classify_density(cls, weighted_density):
        """
        Standardized classification for traffic density.
        Returns: 'LOW', 'MEDIUM', 'HIGH', or 'VERY HIGH'
        """
        if weighted_density >= 40.0:
            return 'VERY HIGH'
        elif weighted_density >= 25.0:
            return 'HIGH'
        elif weighted_density >= 10.0:
            return 'MEDIUM'
        else:
            return 'LOW'

    @classmethod
    def get_density_label(cls, weighted_density):
        """Human-readable label for UI."""
        mapping = {
            'LOW': 'Low Traffic',
            'MEDIUM': 'Medium Traffic',
            'HIGH': 'High Traffic',
            'VERY HIGH': 'Very High Traffic',
        }
        return mapping[cls.classify_density(weighted_density)]

    def calculate_green_time(self, weighted_density):
        """
        Calculate dynamic green light duration (in seconds) based on weighted density.
        Formula: BASE_GREEN + (weighted_density * 1.5), clamped strictly between MIN_GREEN and MAX_GREEN.
        """
        raw_time = self.BASE_GREEN + (weighted_density * 1.5)
        green_time = int(round(raw_time))
        return max(self.MIN_GREEN, min(green_time, self.MAX_GREEN))

    def calculate_priority_score(self, weighted_density, waiting_time=0, is_emergency=False):
        """
        Calculate total priority score for a direction:
        Priority = Weighted Density + (Waiting Time * Starvation Rate)
        Emergency vehicles instantly override with maximum priority score.
        """
        if is_emergency:
            return 9999.0

        starvation_bonus = waiting_time * self.STARVATION_RATE
        return round(weighted_density + starvation_bonus, 2)

    def evaluate_signals(self, signals, waiting_times=None):
        """
        Evaluate a collection of TrafficSignal objects to determine the next green phase.
        Args:
            signals: List or QuerySet of TrafficSignal instances.
            waiting_times: Optional dict {signal_id or direction: waiting_seconds}
        Returns:
            TrafficSignal: Highest priority signal.
        """
        if not signals:
            return None

        from django.utils import timezone
        now = timezone.now()

        if waiting_times is None:
            waiting_times = {}

        best_signal = None
        highest_score = -1.0

        for s in signals:
            wait = waiting_times.get(s.direction, waiting_times.get(s.id, None))
            if wait is None and s.current_state == 'RED' and s.state_start_time:
                wait = max(0, (now - s.state_start_time).total_seconds())
            elif wait is None:
                wait = 0

            score = self.calculate_priority_score(
                s.current_weighted_density,
                waiting_time=wait,
                is_emergency=s.is_emergency_active
            )
            if score > highest_score:
                highest_score = score
                best_signal = s

        return best_signal
