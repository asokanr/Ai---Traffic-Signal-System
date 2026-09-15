from django.db import transaction
from django.utils import timezone
from signal_app.models import TrafficSignal, EmergencyLog

class EmergencyManager:
    """
    Handles Emergency Vehicle Overrides.
    Ensures immediate priority and safety locking of other lanes.
    """

    def handle_emergency_detection(self, signal, vehicle_counts):
        """
        Check if emergency vehicle is present and trigger override if needed.
        Args:
            signal: TrafficSignal instance
            vehicle_counts: dict of counts
        Returns:
            bool: True if emergency mode was triggered/maintained
        """
        emerg_count = vehicle_counts.get('emergency_vehicle', 0)

        if emerg_count > 0:
            if not signal.is_emergency_active:
                self._activate_emergency(signal)
            return True
        else:
            # If emergency vehicle count cleared and mode is not locked, resolve
            return signal.is_emergency_active

    def _activate_emergency(self, active_signal):
        """
        Force the active signal to GREEN and High Priority.
        Force others to RED.
        """
        with transaction.atomic():
            # Record previous green time if it was green
            if active_signal.current_state == 'GREEN':
                from signal_app.models import SignalTiming
                # Capture timing before we overwrite state_start_time
                SignalTiming.objects.create(
                    signal=active_signal,
                    green_start_time=active_signal.state_start_time,
                    green_end_time=timezone.now()
                )

            active_signal.is_emergency_active = True
            active_signal.mode = 'EMERGENCY'
            active_signal.current_state = 'GREEN'
            active_signal.green_time = 60 # Max time for emergency
            active_signal.state_start_time = timezone.now()
            active_signal.save()



            # 2. Log Start
            EmergencyLog.objects.create(
                signal=active_signal,
                start_time=timezone.now(),
                resolved=False
            )

            # 3. Lock others to RED
            others = TrafficSignal.objects.exclude(id=active_signal.id)
            others.update(current_state='RED') # Efficient update

    def _resolve_emergency(self, signal):
        """
        Deactivate emergency mode and log resolution.
        """
        now = timezone.now()
        
        # Record the Emergency Green Duration
        if signal.current_state == 'GREEN' and signal.is_emergency_active:
             from signal_app.models import SignalTiming
             SignalTiming.objects.create(
                 signal=signal,
                 green_start_time=signal.state_start_time,
                 green_end_time=now
             )

        signal.is_emergency_active = False
        signal.mode = 'ADAPTIVE'
        
        # Recalculate Green Time based on current density (likely low now)
        from .traffic_engine import TrafficEngine
        engine = TrafficEngine()
        # We need current counts. Signal object has cached density or we calculate it?
        # Signal model has `current_weighted_density` property if annotations used, 
        # but here we might need to fetch latest VehicleCount or use last known.
        # Let's rely on the last associated VehicleCount or just default to minimum?
        # Ideally, we trigger an immediate evaluation or set a short time.
        # Let's set it to valid calculated time.
        
        # We need to import VehicleCount to get data? 
        # Avoiding circular imports could be tricky if not careful.
        # But we can access signal.vehicle_counts (related_name is 'vehicle_counts')
        latest_count = signal.vehicle_counts.order_by('-timestamp').first()
        if latest_count:
             density = latest_count.weighted_score
             signal.green_time = engine.calculate_green_time(density)
        else:
             signal.green_time = 10 # Default MIN
             
        signal.state_start_time = now
        signal.save()

        # Close Log
        log = EmergencyLog.objects.filter(signal=signal, resolved=False).last()
        if log:
            log.end_time = now
            log.resolved = True
            
            # Helper to calculate clearance
            # Clearance time is essentially how long it took from START of log to the point the signal became GREEN.
            # IN our logic, the signal becomes GREEN *immediately* on start.
            # So clearance time is effectively 0 in this instant-override system.
            # However, if we had a delay (e.g. 5s yellow for others), we would track that.
            # For now, we'll log the total duration of the emergency event as 'Response Time' 
            # and set clearance to 0 or small delta.
            
            # Let's say clearance_time is time from Start -> Signal Green.
            # Since we force green immediately, it is 0.
            log.clearance_time = 0.0 
            
            log.save()
            
    def is_system_in_emergency(self):
        """
        Check if ANY signal is currently in Emergency Mode.
        """
        return TrafficSignal.objects.filter(is_emergency_active=True).exists()
