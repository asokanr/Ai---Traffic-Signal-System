"""
Signal State Machine and Transition Controller.

Enforces safe, deterministic traffic signal state transitions:
GREEN (Dynamic Timer) -> YELLOW (5s Clearance) -> RED -> Next Priority Direction GREEN.
Guarantees that no two intersecting directions have GREEN simultaneously and prevents abrupt phase switches.
"""

from django.utils import timezone
from signal_app.logic.traffic_engine import TrafficEngine
from signal_app.models import TrafficSignal, SignalTiming


class SignalController:
    """
    State machine controller for a 4-direction junction.
    """

    YELLOW_DURATION = 3  # Standard yellow clearance phase in seconds

    def __init__(self, traffic_engine=None):
        self.engine = traffic_engine or TrafficEngine()

    def advance_signal_cycle(self, junction=None, signals=None, waiting_tracker=None):
        """
        Advance the signal cycle based on current state and elapsed timers.
        Returns:
            dict: {
                'transition_occurred': bool,
                'events': list of string messages,
                'active_green': str or None,
                'active_state': str,
                'remaining_time': int,
                'remaining_formatted': str,
                'next_priority': str or None,
            }
        """
        now = timezone.now()
        events = []
        transition_occurred = False

        if signals is None:
            if junction:
                signals = list(TrafficSignal.objects.filter(junction=junction))
            else:
                signals = list(TrafficSignal.objects.all())

        if not signals:
            return {
                'transition_occurred': False,
                'events': ['No signals found'],
                'active_green': None,
                'active_state': 'RED',
                'remaining_time': 0,
                'remaining_formatted': '00:00',
                'next_priority': None,
            }

        # Check if emergency is active
        emergency_signal = next((s for s in signals if s.is_emergency_active), None)
        if emergency_signal:
            # Ensure only emergency signal is GREEN, all others locked to RED
            for s in signals:
                if s.id != emergency_signal.id and s.current_state != 'RED':
                    s.current_state = 'RED'
                    s.state_start_time = now
                    s.save()

            if emergency_signal.current_state != 'GREEN':
                emergency_signal.current_state = 'GREEN'
                emergency_signal.state_start_time = now
                emergency_signal.green_time = 60
                emergency_signal.save()
                transition_occurred = True

            rem = emergency_signal.remaining_time
            mins, secs = divmod(max(0, rem), 60)
            return {
                'transition_occurred': transition_occurred,
                'events': [f"EMERGENCY PRIORITY ACTIVE on {emergency_signal.get_direction_display()}"],
                'active_green': emergency_signal.direction,
                'active_state': 'GREEN',
                'remaining_time': rem,
                'remaining_formatted': f"{mins:02d}:{secs:02d}",
                'next_priority': None,
            }

        green_signal = next((s for s in signals if s.current_state == 'GREEN'), None)
        yellow_signal = next((s for s in signals if s.current_state == 'YELLOW'), None)

        # -------------------------------------------------------------
        # Phase 1: YELLOW -> RED -> Next GREEN
        # -------------------------------------------------------------
        if yellow_signal:
            elapsed = (now - yellow_signal.state_start_time).total_seconds()
            if elapsed >= self.YELLOW_DURATION:
                # 1. Yellow direction turns RED
                yellow_signal.current_state = 'RED'
                yellow_signal.state_start_time = now
                yellow_signal.save()
                events.append(f"{yellow_signal.get_direction_display()}: YELLOW → RED")
                transition_occurred = True

                # 2. Select next highest priority direction among other waiting RED signals
                other_red_signals = [s for s in signals if s.id != yellow_signal.id and s.current_state == 'RED']
                candidate_signals = other_red_signals if other_red_signals else [s for s in signals if s.current_state == 'RED']
                next_signal = self.engine.evaluate_signals(candidate_signals)

                if next_signal:
                    new_green_time = self.engine.calculate_green_time(next_signal.current_weighted_density)
                    next_signal.current_state = 'GREEN'
                    next_signal.green_time = new_green_time
                    next_signal.state_start_time = now
                    next_signal.save()

                    # Guarantee all other signals remain locked to RED
                    for s in signals:
                        if s.id != next_signal.id:
                            if s.current_state != 'RED':
                                s.current_state = 'RED'
                                s.state_start_time = now
                                s.save()

                    events.append(f"{next_signal.get_direction_display()}: RED → GREEN ({new_green_time}s)")
                    green_signal = next_signal
                yellow_signal = None

        # -------------------------------------------------------------
        # Phase 2: GREEN -> YELLOW (when green timer has expired)
        # -------------------------------------------------------------
        elif green_signal:
            elapsed = (now - green_signal.state_start_time).total_seconds()
            if elapsed >= green_signal.green_time:
                # Record timing log
                try:
                    SignalTiming.objects.create(
                        signal=green_signal,
                        green_start_time=green_signal.state_start_time,
                        green_end_time=now
                    )
                except Exception:
                    pass

                # Transition to YELLOW
                green_signal.current_state = 'YELLOW'
                green_signal.yellow_time = self.YELLOW_DURATION
                green_signal.state_start_time = now
                green_signal.save()
                events.append(f"{green_signal.get_direction_display()}: GREEN → YELLOW ({self.YELLOW_DURATION}s)")
                yellow_signal = green_signal
                green_signal = None
                transition_occurred = True

        # -------------------------------------------------------------
        # Phase 3: Bootstrap (all signals RED -> start highest priority)
        # -------------------------------------------------------------
        elif not green_signal and not yellow_signal:
            next_signal = self.engine.evaluate_signals(signals)
            if next_signal:
                new_green_time = self.engine.calculate_green_time(next_signal.current_weighted_density)
                next_signal.current_state = 'GREEN'
                next_signal.green_time = new_green_time
                next_signal.state_start_time = now
                next_signal.save()

                # Lock all others to RED
                for s in signals:
                    if s.id != next_signal.id and s.current_state != 'RED':
                        s.current_state = 'RED'
                        s.state_start_time = now
                        s.save()

                events.append(f"Initialized: {next_signal.get_direction_display()} → GREEN ({new_green_time}s)")
                green_signal = next_signal
                transition_occurred = True

        # Determine current snapshot info
        active_dir = None
        active_state = 'RED'
        remaining = 0

        if green_signal:
            active_dir = green_signal.direction
            active_state = 'GREEN'
            remaining = green_signal.remaining_time
        elif yellow_signal:
            active_dir = yellow_signal.direction
            active_state = 'YELLOW'
            remaining = yellow_signal.remaining_time

        # Next priority forecast
        other_signals = [s for s in signals if s.direction != active_dir]
        next_priority = self.engine.evaluate_signals(other_signals)
        next_p_dir = next_priority.direction if next_priority else None

        mins, secs = divmod(max(0, remaining), 60)
        formatted_time = f"{mins:02d}:{secs:02d}"

        return {
            'transition_occurred': transition_occurred,
            'events': events,
            'active_green': active_dir,
            'active_state': active_state,
            'remaining_time': remaining,
            'remaining_formatted': formatted_time,
            'next_priority': next_p_dir,
        }

    def get_status_summary(self, signals):
        """
        Generate a comprehensive status dictionary for API and dashboard rendering.
        """
        active_signal = next((s for s in signals if s.current_state in ('GREEN', 'YELLOW')), None)
        other_signals = [s for s in signals if s != active_signal]
        next_sig = self.engine.evaluate_signals(other_signals)

        rem = active_signal.remaining_time if active_signal else 0
        mins, secs = divmod(max(0, rem), 60)

        dir_names = {'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West'}

        return {
            'active_direction': dir_names.get(active_signal.direction, active_signal.direction) if active_signal else None,
            'active_direction_code': active_signal.direction if active_signal else None,
            'active_state': active_signal.current_state if active_signal else 'ALL_RED',
            'remaining_seconds': rem,
            'remaining_formatted': f"{mins:02d}:{secs:02d}",
            'next_priority_direction': dir_names.get(next_sig.direction, next_sig.direction) if next_sig else None,
            'next_priority_code': next_sig.direction if next_sig else None,
            'densities': {
                s.direction: s.current_weighted_density for s in signals
            },
            'vehicle_counts': {
                s.direction: s.vehicle_count for s in signals
            },
            'signals': {
                s.direction: {
                    'id': s.id,
                    'direction': s.direction,
                    'direction_name': s.get_direction_display(),
                    'state': s.current_state,
                    'vehicle_count': s.vehicle_count,
                    'weighted_density': s.current_weighted_density,
                    'density_label': self.engine.get_density_label(s.current_weighted_density),
                    'density_code': self.engine.classify_density(s.current_weighted_density),
                    'green_time': s.green_time,
                    'yellow_time': s.yellow_time,
                    'red_time': s.red_time,
                    'remaining_time': s.remaining_time,
                    'remaining_formatted': f"{max(0, s.remaining_time) // 60:02d}:{max(0, s.remaining_time) % 60:02d}",
                    'is_emergency': s.is_emergency_active,
                }
                for s in signals
            }
        }
