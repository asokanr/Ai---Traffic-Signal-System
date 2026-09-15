from rest_framework import viewsets, status
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse

from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Avg, Count, Q, F, Max

from .models import (
    TrafficSignal, TrafficLog, VehicleCount, EmergencyLog,
    SignalTiming, Junction, AdminActionLog, AccidentAlert,
    PollutionReading, UserProfile
)
from .serializers import (
    TrafficSignalSerializer, TrafficLogSerializer,
    JunctionSerializer, EmergencyLogSerializer,
    AdminActionLogSerializer, AccidentAlertSerializer,
    PollutionReadingSerializer
)
from .logic import TrafficEngine, EmergencyManager
from .decorators import admin_only

# Initialize Logic Engines
traffic_engine = TrafficEngine()
emergency_manager = EmergencyManager()

# =====================================================
# REST API VIEWSET — Traffic Signals
# =====================================================
class TrafficSignalViewSet(viewsets.ModelViewSet):
    queryset = TrafficSignal.objects.all()
    serializer_class = TrafficSignalSerializer

    @action(detail=False, methods=['get'])
    def all_signals(self, request):
        junction_id = request.query_params.get('junction')
        qs = TrafficSignal.objects.all()
        if junction_id:
            qs = qs.filter(junction_id=junction_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='state')
    def state(self, request):
        junction_id = request.query_params.get('junction')
        signals = TrafficSignal.objects.all()
        if junction_id:
            signals = signals.filter(junction_id=junction_id)
        _, _, _, controller = _get_services()
        summary = controller.get_status_summary(list(signals))
        return Response(summary)

    # 
    #     Receives detailed vehicle counts, updates system state.
    #     
    @action(detail=True, methods=['post'], url_path='update_count')
    def update_vehicle_count(self, request, pk=None):
        signal = self.get_object()
        data = request.data

        two_wheeler = int(data.get('two_wheeler', 0))
        four_wheeler = int(data.get('four_wheeler', 0))
        heavy_vehicle = int(data.get('heavy_vehicle', 0))
        emergency_vehicle = int(data.get('emergency_vehicle', 0))

        counts = {
            'two_wheeler': two_wheeler,
            'four_wheeler': four_wheeler,
            'heavy_vehicle': heavy_vehicle,
            'emergency_vehicle': emergency_vehicle,
        }

        weighted_density = traffic_engine.calculate_weighted_density(counts)

        with transaction.atomic():
            vc = VehicleCount.objects.create(
                signal=signal,
                two_wheeler=two_wheeler,
                four_wheeler=four_wheeler,
                heavy_vehicle=heavy_vehicle,
                emergency_vehicle=emergency_vehicle,
            )

            emergency_triggered = emergency_manager.handle_emergency_detection(signal, counts)

            # Persist density and vehicle count directly to the signal model
            signal.vehicle_count = vc.total_vehicles
            signal.current_weighted_density = weighted_density

            if not emergency_triggered:
                new_green = traffic_engine.calculate_green_time(weighted_density)
                signal.green_time = new_green

            signal.save()

            TrafficLog.objects.create(
                signal=signal,
                vehicle_count=vc.total_vehicles,
                weighted_density=vc.weighted_score,
                signal_state=signal.current_state,
                waiting_time=signal.red_time if signal.current_state == 'RED' else 0,
                is_emergency=emergency_triggered,
            )

        signal.refresh_from_db()
        serializer = self.get_serializer(signal)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle_sos')
    def toggle_sos(self, request, pk=None):
        signal = self.get_object()
        active = request.data.get('active', False)
        
        if active:
            emergency_manager._activate_emergency(signal)
            action_desc = f"Manual SOS activated on {signal.get_direction_display()} lane"
        else:
            emergency_manager._resolve_emergency(signal)
            action_desc = f"Manual SOS deactivated on {signal.get_direction_display()} lane"

        # Log admin action if user is authenticated
        if request.user.is_authenticated:
            try:
                AdminActionLog.objects.create(
                    user=request.user,
                    action_type='EMERGENCY_TOGGLE',
                    junction=signal.junction,
                    description=action_desc
                )
            except Exception:
                pass
        
        signals = TrafficSignal.objects.all()
        serializer = self.get_serializer(signals, many=True)
        return Response({
            'status': 'EMERGENCY_UPDATED',
            'is_emergency_active': active,
            'direction': signal.direction,
            'signals': serializer.data
        })

    @action(detail=False, methods=['post'], url_path='cycle')
    def cycle_signals(self, request):
        junction_id = request.data.get('junction_id')
        
        if junction_id:
            signals = TrafficSignal.objects.filter(junction_id=junction_id)
        else:
            signals = TrafficSignal.objects.all()

        if emergency_manager.is_system_in_emergency():
            return Response({
                'status': 'EMERGENCY_ACTIVE',
                'message': 'System in emergency mode. Cycle skipped.',
            })

        now = timezone.now()
        results = []

        with transaction.atomic():
            green_signal = signals.filter(current_state='GREEN').first()
            yellow_signal = signals.filter(current_state='YELLOW').first()

            if yellow_signal:
                elapsed = (now - yellow_signal.state_start_time).total_seconds()
                if elapsed >= yellow_signal.yellow_time:
                    SignalTiming.objects.create(
                        signal=yellow_signal,
                        green_start_time=yellow_signal.state_start_time,
                        green_end_time=now
                    )
                    yellow_signal.current_state = 'RED'
                    yellow_signal.state_start_time = now
                    yellow_signal.save()
                    results.append(f"{yellow_signal.get_direction_display()}: YELLOW → RED")

                    # Select the next green signal from other RED signals (avoid repeating the same one immediately)
                    other_red_signals = list(signals.filter(current_state='RED').exclude(id=yellow_signal.id))
                    candidate_signals = other_red_signals if other_red_signals else list(signals.filter(current_state='RED'))

                    next_signal = traffic_engine.evaluate_signals(candidate_signals)
                    if next_signal:
                        next_signal.current_state = 'GREEN'
                        next_signal.state_start_time = now
                        new_green = traffic_engine.calculate_green_time(
                            next_signal.current_weighted_density
                        )
                        next_signal.green_time = new_green
                        next_signal.save()
                        results.append(f"{next_signal.get_direction_display()}: RED → GREEN ({new_green}s)")
                else:
                    results.append(f"{yellow_signal.get_direction_display()}: YELLOW ({int(elapsed)}s/{yellow_signal.yellow_time}s)")

            elif green_signal:
                elapsed = (now - green_signal.state_start_time).total_seconds()
                if elapsed >= green_signal.green_time:
                    SignalTiming.objects.create(
                        signal=green_signal,
                        green_start_time=green_signal.state_start_time,
                        green_end_time=now
                    )
                    green_signal.current_state = 'YELLOW'
                    green_signal.yellow_time = traffic_engine.YELLOW_TIME
                    green_signal.state_start_time = now
                    green_signal.save()
                    results.append(f"{green_signal.get_direction_display()}: GREEN → YELLOW")
                else:
                    remaining = max(0, green_signal.green_time - int(elapsed))
                    results.append(f"{green_signal.get_direction_display()}: GREEN ({remaining}s remaining)")
            else:
                best = traffic_engine.evaluate_signals(signals)
                if best:
                    best.current_state = 'GREEN'
                    best.state_start_time = now
                    new_green = traffic_engine.calculate_green_time(best.current_weighted_density)
                    best.green_time = new_green
                    best.save()
                    results.append(f"{best.get_direction_display()}: → GREEN ({new_green}s)")

        all_signals = self.get_serializer(signals, many=True)
        return Response({
            'status': 'CYCLE_COMPLETE',
            'transitions': results,
            'signals': all_signals.data
        })

    @action(detail=False, methods=['post'], url_path='reset')
    def reset_system(self, request):
        with transaction.atomic():
            VehicleCount.objects.all().delete()
            TrafficLog.objects.all().delete()
            EmergencyLog.objects.all().delete()
            SignalTiming.objects.all().delete()

            TrafficSignal.objects.all().update(
                current_state='RED',
                vehicle_count=0,
                current_weighted_density=0.0,
                is_emergency_active=False,
                mode='ADAPTIVE',
                green_time=30,
                yellow_time=5,
                red_time=10,
                state_start_time=timezone.now()
            )

        # Log admin action
        if request.user.is_authenticated:
            AdminActionLog.objects.create(
                user=request.user,
                action_type='SYSTEM_RESET',
                description='Full system reset — all logs and counts cleared.'
            )

        return Response({'status': 'SYSTEM_RESET', 'message': 'All data cleared. Signals reset to RED.'})

    @action(detail=False, methods=['get'], url_path='global_stats')
    def global_stats(self, request):
        signals = TrafficSignal.objects.all()
        total_vehicles = signals.aggregate(total=Sum('vehicle_count'))['total'] or 0
        total_crossed = VehicleCount.objects.aggregate(total=Sum('vehicles_passed'))['total'] or 0
        green_signal = signals.filter(current_state='GREEN').first()

        return Response({
            'total_vehicles': total_vehicles,
            'total_crossed': total_crossed,
            'active_green': green_signal.get_direction_display() if green_signal else '--',
            'active_green_remaining': green_signal.remaining_time if green_signal else 0,
        })

    @action(detail=False, methods=['post'], url_path='reset_stats')
    def reset_stats(self, request):
        VehicleCount.objects.all().delete()
        TrafficSignal.objects.all().update(vehicle_count=0, current_weighted_density=0.0)
        return Response({'status': 'Stats reset'})

    @action(detail=False, methods=['get'])
    def history(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        direction = request.query_params.get('direction')

        qs = TrafficLog.objects.all()
        if direction:
            qs = qs.filter(signal__direction=direction)

        total = qs.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        logs = qs[start:end]

        serializer = TrafficLogSerializer(logs, many=True)
        return Response({
            'results': serializer.data,
            'page': page,
            'total_pages': total_pages,
            'total_count': total,
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        signal = self.get_object()
        logs = signal.logs.all()[:20]
        serializer = TrafficLogSerializer(logs, many=True)
        return Response(serializer.data)

    # =====================================================
    # MANUAL OVERRIDE (Admin Only)
    # =====================================================
    @action(detail=True, methods=['post'], url_path='manual_override')
    @admin_only
    def manual_override(self, request, pk=None):
        signal = self.get_object()
        new_state = request.data.get('state', '').upper()

        if new_state not in ['RED', 'YELLOW', 'GREEN']:
            return Response({'error': 'Invalid state. Must be RED, YELLOW, or GREEN.'},
                            status=status.HTTP_400_BAD_REQUEST)

        old_state = signal.current_state
        signal.current_state = new_state
        signal.mode = 'MANUAL'
        signal.state_start_time = timezone.now()
        signal.save()

        AdminActionLog.objects.create(
            user=request.user,
            action_type='MANUAL_OVERRIDE',
            description=f"Changed {signal.get_direction_display()} from {old_state} to {new_state}",
            junction=signal.junction,
            signal=signal
        )

        serializer = self.get_serializer(signal)
        return Response({
            'status': 'OVERRIDE_APPLIED',
            'old_state': old_state,
            'new_state': new_state,
            'signal': serializer.data
        })

    # =====================================================
    # REMOTE TIMING CONFIGURATION (Admin Only)
    # =====================================================
    @action(detail=True, methods=['post'], url_path='configure_timing')
    @admin_only
    def configure_timing(self, request, pk=None):
        signal = self.get_object()
        green = request.data.get('green_time')
        yellow = request.data.get('yellow_time')
        red = request.data.get('red_time')

        changes = []
        if green is not None:
            signal.green_time = int(green)
            changes.append(f"green={green}s")
        if yellow is not None:
            signal.yellow_time = int(yellow)
            changes.append(f"yellow={yellow}s")
        if red is not None:
            signal.red_time = int(red)
            changes.append(f"red={red}s")

        signal.save()

        AdminActionLog.objects.create(
            user=request.user,
            action_type='TIMING_CONFIG',
            description=f"Timing updated for {signal.get_direction_display()}: {', '.join(changes)}",
            junction=signal.junction,
            signal=signal
        )

        serializer = self.get_serializer(signal)
        return Response({'status': 'TIMING_UPDATED', 'signal': serializer.data})


# =====================================================
# JUNCTION VIEWSET
# =====================================================
class JunctionViewSet(viewsets.ModelViewSet):
    queryset = Junction.objects.all()
    serializer_class = JunctionSerializer

    @action(detail=True, methods=['get'], url_path='status')
    def junction_status(self, request, pk=None):
        junction = self.get_object()
        signals = TrafficSignal.objects.filter(junction=junction)
        signal_serializer = TrafficSignalSerializer(signals, many=True)

        total_vehicles = signals.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_density = signals.aggregate(avg=Avg('current_weighted_density'))['avg'] or 0
        emergency_active = signals.filter(is_emergency_active=True).exists()

        return Response({
            'junction': JunctionSerializer(junction).data,
            'signals': signal_serializer.data,
            'total_vehicles': total_vehicles,
            'avg_density': round(avg_density, 2),
            'emergency_active': emergency_active,
        })

    @action(detail=True, methods=['get'])
    def signals(self, request, pk=None):
        junction = self.get_object()
        signals = TrafficSignal.objects.filter(junction=junction)
        serializer = TrafficSignalSerializer(signals, many=True)
        return Response(serializer.data)


# =====================================================
# EMERGENCY VIEWSET
# =====================================================
class EmergencyViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='live')
    def live(self, request):
        """Live ambulance tracking — returns active emergency events."""
        active = EmergencyLog.objects.filter(resolved=False)
        serializer = EmergencyLogSerializer(active, many=True)

        # Also return affected junctions
        affected_junctions = set()
        for log in active:
            if log.signal and log.signal.junction:
                affected_junctions.add(log.signal.junction_id)

        return Response({
            'active_emergencies': serializer.data,
            'affected_junction_ids': list(affected_junctions),
            'emergency_mode': active.exists(),
        })

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Emergency event history with pagination."""
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        qs = EmergencyLog.objects.all()
        total = qs.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        logs = qs[start:start + page_size]

        serializer = EmergencyLogSerializer(logs, many=True)
        return Response({
            'results': serializer.data,
            'page': page,
            'total_pages': total_pages,
            'total_count': total,
        })


# =====================================================
# HEATMAP VIEWSET
# =====================================================
class HeatmapViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='data')
    def data(self, request):
        """Aggregated density data for all active junctions."""
        junctions = Junction.objects.filter(is_active=True)
        result = []

        for jn in junctions:
            signals = jn.signals.all()
            total_density = signals.aggregate(total=Sum('current_weighted_density'))['total'] or 0
            total_vehicles = signals.aggregate(total=Sum('vehicle_count'))['total'] or 0
            max_density = signals.aggregate(max=Max('current_weighted_density'))['max'] or 0

            # Congestion level
            if max_density > 35:
                level = 'heavy'
            elif max_density > 15:
                level = 'moderate'
            else:
                level = 'smooth'

            result.append({
                'junction_id': jn.id,
                'name': jn.name,
                'code': jn.code,
                'lat': jn.latitude,
                'lng': jn.longitude,
                'total_density': round(total_density, 2),
                'total_vehicles': total_vehicles,
                'congestion_level': level,
            })

        return Response(result)


# =====================================================
# ANALYTICS VIEWSET (Enhanced)
# =====================================================

class AnalyticsViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='direction/(?P<direction>[NSEW])/summary')
    def direction_summary(self, request, direction=None):
        signals = TrafficSignal.objects.filter(direction=direction)
        if not signals.exists():
            return Response({'error': 'No signals found for this direction'}, status=404)

        signal = signals.first()
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs_today = TrafficLog.objects.filter(signal__direction=direction, timestamp__gte=today_start)

        total_vehicles_today = logs_today.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs_today.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergency_count = logs_today.filter(is_emergency=True).count()
        total_logs = logs_today.count()

        latest_counts = VehicleCount.objects.filter(signal__direction=direction).order_by('-timestamp').first()
        breakdown = {
            'two_wheeler': latest_counts.two_wheeler if latest_counts else 0,
            'four_wheeler': latest_counts.four_wheeler if latest_counts else 0,
            'heavy_vehicle': latest_counts.heavy_vehicle if latest_counts else 0,
            'emergency_vehicle': latest_counts.emergency_vehicle if latest_counts else 0,
        }

        total_passed = VehicleCount.objects.filter(
            signal__direction=direction, timestamp__gte=today_start
        ).aggregate(total=Sum('vehicles_passed'))['total'] or 0

        return Response({
            'direction': direction,
            'current_state': signal.current_state,
            'current_density': signal.current_weighted_density,
            'density_percentage': signal.density_percentage,
            'total_vehicles_today': total_vehicles_today,
            'total_passed_today': total_passed,
            'average_wait_time': round(avg_wait, 1),
            'emergency_events': emergency_count,
            'log_count': total_logs,
            'vehicle_breakdown': breakdown,
        })

    @action(detail=False, methods=['get'], url_path='direction/(?P<direction>[NSEW])/charts')
    def direction_charts(self, request, direction=None):
        hours = int(request.query_params.get('hours', 6))
        cutoff = timezone.now() - timedelta(hours=hours)

        logs = TrafficLog.objects.filter(
            signal__direction=direction,
            timestamp__gte=cutoff
        ).order_by('timestamp')

        labels = []
        vehicle_data = []
        density_data = []

        for log in logs:
            labels.append(log.timestamp.strftime('%H:%M'))
            vehicle_data.append(log.vehicle_count)
            density_data.append(round(log.weighted_density, 2))

        return Response({
            'labels': labels,
            'vehicles': vehicle_data,
            'density': density_data,
        })

    @action(detail=False, methods=['get'], url_path='direction/(?P<direction>[NSEW])/insights')
    def direction_insights(self, request, direction=None):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs = TrafficLog.objects.filter(
            signal__direction=direction,
            timestamp__gte=today_start
        )

        hourly = {}
        for log in logs:
            h = log.timestamp.hour
            hourly[h] = hourly.get(h, 0) + log.vehicle_count

        peak_hour = max(hourly, key=hourly.get) if hourly else None
        peak_volume = hourly.get(peak_hour, 0) if peak_hour is not None else 0

        return Response({
            'peak_hour': f"{peak_hour}:00" if peak_hour is not None else '--:--',
            'peak_volume': peak_volume,
            'hourly_distribution': hourly,
        })

    @action(detail=False, methods=['get'], url_path='emergency_stats')
    def emergency_stats(self, request):
        total = EmergencyLog.objects.count()
        resolved = EmergencyLog.objects.filter(resolved=True).count()
        avg_clearance = EmergencyLog.objects.filter(resolved=True).aggregate(
            avg=Avg('clearance_time'))['avg'] or 0

        return Response({
            'total_emergencies': total,
            'resolved': resolved,
            'unresolved': total - resolved,
            'avg_clearance_time': round(avg_clearance, 2),
        })

    @action(detail=False, methods=['get'], url_path='global_stats')
    def global_stats(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs_today = TrafficLog.objects.filter(timestamp__gte=today_start)
        total = logs_today.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs_today.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergency_count = EmergencyLog.objects.filter(start_time__gte=today_start).count()

        return Response({
            'total_vehicles_today': total,
            'avg_waiting_time': round(avg_wait, 1),
            'emergency_events_today': emergency_count,
        })

    @action(detail=False, methods=['get'], url_path='efficiency_stats')
    def efficiency_stats(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        timings = SignalTiming.objects.filter(date__gte=today)
        total_green = timings.aggregate(total=Sum('total_green_time'))['total'] or 0

        total_vehicles = TrafficLog.objects.filter(timestamp__gte=today_start).aggregate(
            total=Sum('vehicle_count'))['total'] or 0
        total_passed = VehicleCount.objects.filter(timestamp__gte=today_start).aggregate(
            total=Sum('vehicles_passed'))['total'] or 0

        throughput = (total_passed / max(1, total_vehicles)) * 100 if total_vehicles > 0 else 0

        avg_wait = TrafficLog.objects.filter(timestamp__gte=today_start).aggregate(
            avg=Avg('waiting_time'))['avg'] or 0

        avg_emergency_response = EmergencyLog.objects.filter(
            start_time__gte=today_start, resolved=True
        ).aggregate(avg=Avg('clearance_time'))['avg'] or 0

        # Signal efficiency = green utilization
        elapsed_today = (timezone.now() - today_start).total_seconds()
        signal_count = TrafficSignal.objects.count()
        max_possible_green = elapsed_today * signal_count if signal_count > 0 else 1
        signal_efficiency = min(100, (total_green / max(1, max_possible_green)) * 100)

        return Response({
            'total_green_time': total_green,
            'vehicle_throughput_rate': round(throughput, 1),
            'average_waiting_time': round(avg_wait, 1),
            'emergency_response_time': round(avg_emergency_response, 2),
            'signal_efficiency': round(signal_efficiency, 1),
        })

    # =====================================================
    # DAILY / WEEKLY / MONTHLY REPORTS
    # =====================================================
    @action(detail=False, methods=['get'], url_path='daily_report')
    def daily_report(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        logs = TrafficLog.objects.filter(timestamp__gte=today_start)
        total_vehicles = logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergencies = EmergencyLog.objects.filter(start_time__gte=today_start).count()
        passed = VehicleCount.objects.filter(timestamp__gte=today_start).aggregate(
            total=Sum('vehicles_passed'))['total'] or 0

        # Per-direction
        directions = []
        for code, name in TrafficSignal.DIRECTION_CHOICES:
            dir_logs = logs.filter(signal__direction=code)
            dir_total = dir_logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
            dir_wait = dir_logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
            directions.append({
                'direction': code,
                'name': name,
                'total_vehicles': dir_total,
                'avg_wait': round(dir_wait, 1),
            })

        return Response({
            'date': str(today),
            'total_vehicles': total_vehicles,
            'vehicles_passed': passed,
            'avg_waiting_time': round(avg_wait, 1),
            'emergency_events': emergencies,
            'directions': directions,
        })

    @action(detail=False, methods=['get'], url_path='weekly_report')
    def weekly_report(self, request):
        today = timezone.now().date()
        week_start = today - timedelta(days=7)
        week_start_dt = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))

        daily_data = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            logs = TrafficLog.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            total = logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
            avg_wait = logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
            emergencies = EmergencyLog.objects.filter(
                start_time__gte=day_start, start_time__lt=day_end
            ).count()

            daily_data.append({
                'date': str(day),
                'day_name': day.strftime('%A'),
                'total_vehicles': total,
                'avg_wait': round(avg_wait, 1),
                'emergencies': emergencies,
            })

        return Response({
            'week_start': str(week_start),
            'week_end': str(today),
            'daily_data': daily_data,
        })

    @action(detail=False, methods=['get'], url_path='monthly_report')
    def monthly_report(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_start_dt = timezone.make_aware(timezone.datetime.combine(month_start, timezone.datetime.min.time()))

        logs = TrafficLog.objects.filter(timestamp__gte=month_start_dt)
        total = logs.aggregate(total=Sum('vehicle_count'))['total'] or 0
        avg_wait = logs.aggregate(avg=Avg('waiting_time'))['avg'] or 0
        emergencies = EmergencyLog.objects.filter(start_time__gte=month_start_dt).count()
        passed = VehicleCount.objects.filter(timestamp__gte=month_start_dt).aggregate(
            total=Sum('vehicles_passed'))['total'] or 0

        # Weekly breakdown within the month
        weekly_data = []
        week_num = 1
        cursor = month_start
        while cursor <= today:
            w_end = min(cursor + timedelta(days=6), today)
            w_start_dt = timezone.make_aware(timezone.datetime.combine(cursor, timezone.datetime.min.time()))
            w_end_dt = timezone.make_aware(timezone.datetime.combine(w_end, timezone.datetime.min.time())) + timedelta(days=1)

            w_logs = logs.filter(timestamp__gte=w_start_dt, timestamp__lt=w_end_dt)
            w_total = w_logs.aggregate(total=Sum('vehicle_count'))['total'] or 0

            weekly_data.append({
                'week': week_num,
                'start': str(cursor),
                'end': str(w_end),
                'total_vehicles': w_total,
            })

            cursor = w_end + timedelta(days=1)
            week_num += 1

        return Response({
            'month': month_start.strftime('%B %Y'),
            'total_vehicles': total,
            'vehicles_passed': passed,
            'avg_waiting_time': round(avg_wait, 1),
            'emergency_events': emergencies,
            'weekly_breakdown': weekly_data,
        })

    @action(detail=False, methods=['get'], url_path='export_pdf')
    def export_pdf(self, request):
        from .reports import generate_daily_report_pdf, REPORTLAB_AVAILABLE

        if not REPORTLAB_AVAILABLE:
            return Response(
                {'error': 'reportlab is not installed. Run: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        buffer = generate_daily_report_pdf()
        if buffer is None:
            return Response({'error': 'Failed to generate PDF'}, status=500)

        response = HttpResponse(buffer, content_type='application/pdf')
        today = timezone.now().date()
        response['Content-Disposition'] = f'attachment; filename="traffic_report_{today}.pdf"'
        return response


# =====================================================
# ALERTS VIEWSET
# =====================================================
class AlertsViewSet(viewsets.ModelViewSet):
    queryset = AccidentAlert.objects.all()
    serializer_class = AccidentAlertSerializer

    @action(detail=False, methods=['get'], url_path='active')
    def active_alerts(self, request):
        active = AccidentAlert.objects.filter(is_active=True)
        serializer = self.get_serializer(active, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve_alert(self, request, pk=None):
        alert = self.get_object()
        alert.is_active = False
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'status': 'Alert resolved'})


# =====================================================
# POLLUTION VIEWSET
# =====================================================
class PollutionViewSet(viewsets.ModelViewSet):
    queryset = PollutionReading.objects.all()
    serializer_class = PollutionReadingSerializer

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """Latest pollution reading per junction."""
        junctions = Junction.objects.filter(is_active=True)
        result = []
        for jn in junctions:
            reading = PollutionReading.objects.filter(junction=jn).first()
            if reading:
                result.append(PollutionReadingSerializer(reading).data)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Pollution readings from the last 24 hours for trend chart."""
        cutoff = timezone.now() - timedelta(hours=24)
        readings = PollutionReading.objects.filter(
            timestamp__gte=cutoff
        ).order_by('timestamp')
        serializer = PollutionReadingSerializer(readings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='simulate')
    def simulate(self, request):
        """Generate random pollution data for all active junctions."""
        import random
        junctions = Junction.objects.filter(is_active=True)
        created = 0
        for jn in junctions:
            # Create multiple readings spread over the last 24 hours
            for i in range(12):
                ts = timezone.now() - timedelta(hours=i * 2, minutes=random.randint(0, 59))
                aqi = random.randint(20, 250)
                PollutionReading.objects.create(
                    junction=jn,
                    aqi=aqi,
                    pm25=round(random.uniform(5, 150), 1),
                    pm10=round(random.uniform(10, 200), 1),
                    co_level=round(random.uniform(0.1, 8.0), 2),
                    no2_level=round(random.uniform(5, 120), 2),
                    timestamp=ts,
                )
                created += 1
        return Response({
            'status': 'OK',
            'message': f'{created} pollution readings generated for {junctions.count()} junction(s).',
            'count': created,
        })


# =====================================================
# ADMIN ACTION LOG VIEWSET
# =====================================================
class AdminActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminActionLog.objects.all()
    serializer_class = AdminActionLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        action_type = self.request.query_params.get('action_type')
        if action_type:
            qs = qs.filter(action_type=action_type)
        return qs


# =====================================================
# DASHBOARD VIEW
# =====================================================
@login_required
def dashboard(request):
    signals = TrafficSignal.objects.all()
    junctions = Junction.objects.filter(is_active=True)
    context = {
        'signals': signals,
        'junctions': junctions,
        'debug': True,
    }
    return render(request, 'dashboard.html', context)


@login_required
def dashboard_data(request):
    signals = TrafficSignal.objects.all()
    data = TrafficSignalSerializer(signals, many=True).data
    return JsonResponse(data, safe=False)


# =====================================================
# ANALYTICS DASHBOARD VIEW
# =====================================================
@login_required
def analytics_dashboard(request):
    return render(request, 'analytics.html')


# =====================================================
# AI ANALYSIS VIEWS — Video Upload & Live Camera
# =====================================================
import os
import json
import threading
from signal_app.models import VideoAnalysis, TrafficSignal, VehicleCount, TrafficLog

# Lazy-loaded service singletons
_detector_instance = None
_roi_manager_instance = None
_traffic_engine_instance = None
_signal_controller_instance = None
_service_lock = threading.Lock()


def _get_services():
    """Lazy-load and cache AI detector, ROI manager, and traffic controller."""
    global _detector_instance, _roi_manager_instance, _traffic_engine_instance, _signal_controller_instance
    if _detector_instance is None:
        with _service_lock:
            if _detector_instance is None:
                from signal_app.logic import TrafficEngine, ROIManager, SignalController, VehicleDetector
                _traffic_engine_instance = TrafficEngine()
                _roi_manager_instance = ROIManager()
                _signal_controller_instance = SignalController(_traffic_engine_instance)
                _detector_instance = VehicleDetector(
                    roi_manager=_roi_manager_instance,
                    traffic_engine=_traffic_engine_instance
                )
    return _detector_instance, _roi_manager_instance, _traffic_engine_instance, _signal_controller_instance


def ai_analysis_page(request):
    """Redirect to dashboard — AI Analysis is embedded in dashboard.html."""
    from django.shortcuts import redirect
    return redirect('dashboard')


def list_media_videos(request):
    """
    GET: Scan the configured Django MEDIA_ROOT directory and subdirectories
    for available traffic video files (MP4, AVI, MOV, MKV, WebM).
    Returns list of discovered videos with name, relative path, size, modified time, and URL.
    """
    from django.conf import settings
    import datetime

    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
    os.makedirs(media_root, exist_ok=True)
    os.makedirs(os.path.join(media_root, 'video_uploads'), exist_ok=True)
    os.makedirs(os.path.join(media_root, 'processed_videos'), exist_ok=True)

    valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
    videos = []

    for root, dirs, files in os.walk(media_root):
        # Exclude processed_videos from the input video list to avoid recursion
        if os.path.basename(root) == 'processed_videos':
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, media_root).replace('\\', '/')
                try:
                    stat = os.stat(full_path)
                    size_mb = round(stat.st_size / (1024 * 1024), 2)
                    mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    timestamp = stat.st_mtime
                except Exception:
                    size_mb = 0
                    mod_time = '--'
                    timestamp = 0

                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                video_url = f"{media_url.rstrip('/')}/{rel_path}"

                videos.append({
                    'name': file,
                    'rel_path': rel_path,
                    'full_path': full_path,
                    'size_mb': size_mb,
                    'modified': mod_time,
                    'timestamp': timestamp,
                    'url': video_url,
                })

    # Sort newest first
    videos.sort(key=lambda x: x['timestamp'], reverse=True)

    return JsonResponse({
        'success': True,
        'count': len(videos),
        'media_root': media_root,
        'videos': videos
    })


def analyze_media_video(request):
    """
    POST or GET: Analyze a video file located inside the media folder.
    Accepts 'video_path' (relative to MEDIA_ROOT or filename).
    If no video_path is specified, auto-detects the most recently modified video in MEDIA_ROOT.
    Executes real frame-by-frame YOLOv8 + ByteTrack tracking, 4-direction ROI lane mapping,
    and adaptive green timing calculations.
    Zero random or fake values.
    """
    from django.conf import settings

    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
    os.makedirs(media_root, exist_ok=True)
    os.makedirs(os.path.join(media_root, 'processed_videos'), exist_ok=True)

    # Get requested video path
    if request.method == 'POST':
        try:
            if request.body and request.content_type == 'application/json':
                body = json.loads(request.body)
                requested_path = body.get('video_path', '').strip()
                sample_rate = int(body.get('sample_rate', 3))
                junction_id = body.get('junction_id')
                auto_apply = bool(body.get('auto_apply', False))
            else:
                requested_path = request.POST.get('video_path', '').strip()
                sample_rate = int(request.POST.get('sample_rate', 3))
                junction_id = request.POST.get('junction_id')
                auto_apply = request.POST.get('auto_apply', 'false').lower() == 'true'
        except Exception:
            requested_path = request.POST.get('video_path', '').strip()
            sample_rate = 3
            junction_id = None
            auto_apply = False
    else:
        requested_path = request.GET.get('video_path', '').strip()
        sample_rate = int(request.GET.get('sample_rate', 3))
        junction_id = request.GET.get('junction_id')
        auto_apply = False

    sample_rate = max(1, min(sample_rate, 15))

    target_file_path = None

    if requested_path:
        # Check direct relative path or filename
        cand1 = os.path.join(media_root, requested_path)
        cand2 = os.path.join(media_root, 'video_uploads', requested_path)
        if os.path.isfile(cand1):
            target_file_path = cand1
        elif os.path.isfile(cand2):
            target_file_path = cand2
        elif os.path.isabs(requested_path) and os.path.isfile(requested_path):
            target_file_path = requested_path
        else:
            # Try searching in media_root
            for root, _, files in os.walk(media_root):
                if os.path.basename(root) == 'processed_videos':
                    continue
                if requested_path in files:
                    target_file_path = os.path.join(root, requested_path)
                    break

    # If still not found or no path provided, auto-detect latest video in media/
    if not target_file_path:
        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
        found_videos = []
        for root, _, files in os.walk(media_root):
            if os.path.basename(root) == 'processed_videos':
                continue
            for file in files:
                if os.path.splitext(file)[1].lower() in valid_extensions:
                    full_p = os.path.join(root, file)
                    found_videos.append((full_p, os.path.getmtime(full_p)))

        if found_videos:
            found_videos.sort(key=lambda x: x[1], reverse=True)
            target_file_path = found_videos[0][0]

    if not target_file_path or not os.path.isfile(target_file_path):
        return JsonResponse({
            'error': 'No traffic video file found in the media folder. Please place an MP4/AVI/MOV video in media/ or upload one.',
            'media_folder': media_root,
            'simulated': False
        }, status=404)

    detector, roi_manager, engine, controller = _get_services()
    if not detector.is_ready:
        return JsonResponse({
            'error': 'YOLO model is currently unavailable. Please verify yolov8n.pt exists in the project root.',
            'ai_status': 'OFFLINE',
            'simulated': False
        }, status=503)

    # Prepare output processed video path
    filename_base = os.path.splitext(os.path.basename(target_file_path))[0]
    out_video_name = f"processed_{filename_base}.mp4"
    processed_video_dest = os.path.join(media_root, 'processed_videos', out_video_name)

    from signal_app.logic.yolo_detector import process_video
    results = process_video(
        target_file_path,
        detector=detector,
        roi_manager=roi_manager,
        traffic_engine=engine,
        sample_rate=sample_rate,
        output_video_path=processed_video_dest,
        generate_video=True
    )

    if 'error' in results:
        return JsonResponse(results, status=400)

    # Relative URLs
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    raw_rel = os.path.relpath(target_file_path, media_root).replace('\\', '/')
    results['raw_video_url'] = f"{media_url.rstrip('/')}/{raw_rel}"
    results['processed_video_url'] = f"{media_url.rstrip('/')}/processed_videos/{out_video_name}"
    results['video_filename'] = os.path.basename(target_file_path)

    # Record in database
    analysis = VideoAnalysis.objects.create(
        mode='MEDIA_FILE',
        video_file=raw_rel,
        total_frames=results.get('total_frames', 0),
        processed_frames=results.get('processed_frames', 0),
        total_vehicles=results.get('total_unique_vehicles', results.get('total_vehicles', 0)),
        density_label=results.get('density', 'Low Traffic'),
        lane_data=results.get('lane_data', {}),
        counts_detail=results.get('counts', {}),
        emergency_detected=results.get('emergency_detected', False),
    )

    results['analysis_id'] = analysis.id
    results['ai_status'] = 'ACTIVE'

    # Auto-apply to database signals if requested
    if junction_id and auto_apply:
        _apply_lane_data_to_database(results.get('lane_data', {}), junction_id=junction_id)

    return JsonResponse(results)


def upload_video_analysis(request):
    """
    POST: Accept an uploaded traffic video, save to media/video_uploads/,
    run real YOLOv8 detection & ByteTrack tracking, generate annotated processed video,
    map vehicles to normalized 4-direction ROIs, and calculate real adaptive timings.
    Zero fake or random values.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    video_file = request.FILES.get('video')
    if not video_file:
        return JsonResponse({'error': 'No video file provided'}, status=400)

    # Save uploaded file
    from django.conf import settings
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'video_uploads')
    processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed_videos')
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, video_file.name)
    with open(file_path, 'wb+') as dest:
        for chunk in video_file.chunks():
            dest.write(chunk)

    detector, roi_manager, engine, controller = _get_services()
    if not detector.is_ready:
        return JsonResponse({
            'error': 'YOLO model is currently unavailable on this server. Please ensure yolov8n.pt is available.',
            'ai_status': 'OFFLINE',
            'simulated': False
        }, status=503)

    sample_rate = int(request.POST.get('sample_rate', 3))
    sample_rate = max(1, min(sample_rate, 15))

    filename_base = os.path.splitext(video_file.name)[0]
    out_video_name = f"processed_{filename_base}.mp4"
    processed_video_dest = os.path.join(processed_dir, out_video_name)

    from signal_app.logic.yolo_detector import process_video
    results = process_video(
        file_path,
        detector=detector,
        roi_manager=roi_manager,
        traffic_engine=engine,
        sample_rate=sample_rate,
        output_video_path=processed_video_dest,
        generate_video=True
    )

    if 'error' in results:
        return JsonResponse(results, status=400)

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    results['raw_video_url'] = f"{media_url.rstrip('/')}/video_uploads/{video_file.name}"
    results['processed_video_url'] = f"{media_url.rstrip('/')}/processed_videos/{out_video_name}"
    results['video_filename'] = video_file.name

    # Save record in database
    analysis = VideoAnalysis.objects.create(
        mode='UPLOAD',
        video_file=f'video_uploads/{video_file.name}',
        total_frames=results.get('total_frames', 0),
        processed_frames=results.get('processed_frames', 0),
        total_vehicles=results.get('total_unique_vehicles', results.get('total_vehicles', 0)),
        density_label=results.get('density', 'Low Traffic'),
        lane_data=results.get('lane_data', {}),
        counts_detail=results.get('counts', {}),
        emergency_detected=results.get('emergency_detected', False),
    )

    results['analysis_id'] = analysis.id
    results['ai_status'] = 'ACTIVE'

    # Auto-apply to database signals if junction_id provided
    junction_id = request.POST.get('junction_id')
    auto_apply = request.POST.get('auto_apply', 'false').lower() == 'true'
    if junction_id and auto_apply:
        _apply_lane_data_to_database(results.get('lane_data', {}), junction_id=junction_id)

    return JsonResponse(results)


def analyze_frame(request):
    """
    POST: Receive a JPEG frame buffer, run real YOLO detection & ByteTrack tracking,
    map to normalized 4-direction ROIs, compute real-time metrics.
    Zero random numbers.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    frame_file = request.FILES.get('frame')
    if not frame_file:
        return JsonResponse({'error': 'No frame image provided', 'simulated': False}, status=400)

    from signal_app.logic.input_sources import BufferFrameInputSource
    input_source = BufferFrameInputSource(frame_file.read(), target_max_width=640)
    ret, frame, _ = input_source.get_frame()

    if not ret or frame is None:
        return JsonResponse({'error': 'Could not decode image frame', 'simulated': False}, status=400)

    detector, roi_manager, engine, controller = _get_services()
    if not detector.is_ready:
        return JsonResponse({
            'error': 'YOLO model is currently offline.',
            'ai_status': 'OFFLINE',
            'simulated': False
        }, status=503)

    frame_idx = int(request.POST.get('frame_idx', 0))
    result = detector.detect_frame(frame, frame_idx=frame_idx, use_tracking=True)

    lane_data = {}
    for d in ('N', 'S', 'E', 'W'):
        cnt = result['lane_counts'].get(d, 0)
        types = result['lane_types'].get(d, {})
        weighted_density = engine.calculate_weighted_density(types if cnt > 0 else {'car': cnt})
        green_time = engine.calculate_green_time(weighted_density)

        lane_data[d] = {
            'direction_name': roi_manager.DIRECTION_NAMES[d],
            'vehicle_count': cnt,
            'weighted_density': weighted_density,
            'density': engine.get_density_label(weighted_density),
            'density_code': engine.classify_density(weighted_density),
            'green': green_time,
            'yellow': engine.YELLOW_TIME,
            'red': engine.MIN_RED,
            'type_breakdown': types,
        }

    total_active = result['total_active_vehicles']
    overall_density = engine.get_density_label(sum(l['weighted_density'] for l in lane_data.values()) / 4.0)

    return JsonResponse({
        'counts': result['counts'],
        'density': overall_density,
        'lane_data': lane_data,
        'total_vehicles': total_active,
        'annotated_frame': detector.frame_to_base64(result['annotated_frame']),
        'ai_status': 'ACTIVE',
        'simulated': False,
    })


def apply_analysis_to_signals(request):
    """
    POST: Push analyzed traffic data from a VideoAnalysis session or explicit payload
    into the active TrafficSignal and VehicleCount records in the database.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        if request.body:
            body_data = json.loads(request.body)
        else:
            body_data = request.POST
    except Exception:
        body_data = request.POST

    analysis_id = body_data.get('analysis_id')
    junction_id = body_data.get('junction_id')
    custom_lane_data = body_data.get('lane_data')

    analysis = None
    if analysis_id:
        analysis = VideoAnalysis.objects.filter(id=analysis_id).first()

    lane_data = custom_lane_data or (analysis.lane_data if analysis else None)
    if not lane_data:
        return JsonResponse({'error': 'No lane data provided to apply'}, status=400)

    signals_updated = _apply_lane_data_to_database(lane_data, junction_id=junction_id)
    return JsonResponse({
        'success': True,
        'message': f'Successfully applied real traffic data to {len(signals_updated)} signals.',
        'signals': signals_updated,
    })


def roi_config_api(request):
    """
    GET: Return current normalized ROI layout configurations for frontend visualization.
    """
    detector, roi_manager, engine, controller = _get_services()
    return JsonResponse(roi_manager.get_roi_config())


def camera_check(request):
    """
    GET: Quick check if a camera device is available.
    """
    import cv2
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                return JsonResponse({
                    'camera_available': True,
                    'message': 'Camera device detected and ready for live streaming'
                })
            else:
                return JsonResponse({
                    'camera_available': False,
                    'message': 'Camera detected but could not capture frames. Please check camera permissions.'
                })
        else:
            cap.release()
            return JsonResponse({
                'camera_available': False,
                'message': 'No camera device detected. Please connect a webcam or IP camera and try again.'
            })
    except Exception as e:
        return JsonResponse({
            'camera_available': False,
            'message': f'Camera check error: {str(e)}'
        })


def live_camera_feed(request):
    """
    GET: Stream MJPEG with real YOLO bounding boxes and ROI overlays.
    """
    import cv2
    from django.http import StreamingHttpResponse

    detector, roi_manager, engine, controller = _get_services()

    def generate_frames():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            placeholder = _create_no_camera_frame()
            _, buffer = cv2.imencode('.jpg', placeholder)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            return

        frame_counter = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if detector.is_ready:
                    result = detector.detect_frame(frame, frame_idx=frame_counter, use_tracking=True)
                    frame = result['annotated_frame']
                frame_counter += 1

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        finally:
            cap.release()

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


def live_analysis_snapshot(request):
    """
    GET: Capture a single frame from webcam, run real detection, return JSON stats.
    """
    import cv2
    detector, roi_manager, engine, controller = _get_services()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        return JsonResponse({
            'error': 'no_camera',
            'message': 'No camera detected. Please connect a webcam or use Upload mode.',
            'ai_status': 'NO_CAMERA',
            'simulated': False
        }, status=404)

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return JsonResponse({'error': 'Failed to capture frame', 'simulated': False}, status=500)

    if detector.is_ready:
        result = detector.detect_frame(frame, use_tracking=True)
        lane_data = {}
        for d in ('N', 'S', 'E', 'W'):
            cnt = result['lane_counts'].get(d, 0)
            types = result['lane_types'].get(d, {})
            weighted_density = engine.calculate_weighted_density(types if cnt > 0 else {'car': cnt})
            green_time = engine.calculate_green_time(weighted_density)

            lane_data[d] = {
                'direction_name': roi_manager.DIRECTION_NAMES[d],
                'vehicle_count': cnt,
                'weighted_density': weighted_density,
                'density': engine.get_density_label(weighted_density),
                'density_code': engine.classify_density(weighted_density),
                'green': green_time,
                'yellow': engine.YELLOW_TIME,
                'red': engine.MIN_RED,
                'type_breakdown': types,
            }

        total_active = result['total_active_vehicles']
        overall_density = engine.get_density_label(sum(l['weighted_density'] for l in lane_data.values()) / 4.0)

        return JsonResponse({
            'counts': result['counts'],
            'density': overall_density,
            'lane_data': lane_data,
            'total_vehicles': total_active,
            'annotated_frame': detector.frame_to_base64(result['annotated_frame']),
            'ai_status': 'ACTIVE',
            'simulated': False,
        })
    else:
        return JsonResponse({
            'error': 'YOLO detector is offline',
            'ai_status': 'OFFLINE',
            'simulated': False
        }, status=503)


def analysis_history(request):
    """
    GET: Return list of past VideoAnalysis records ordered newest first.
    """
    analyses = VideoAnalysis.objects.order_by('-created_at')[:25]
    data = []
    for a in analyses:
        data.append({
            'id': a.id,
            'mode': a.mode,
            'video_file': str(a.video_file) if a.video_file else '',
            'total_vehicles': a.total_vehicles,
            'density_label': a.density_label,
            'total_frames': a.total_frames,
            'processed_frames': a.processed_frames,
            'lane_data': a.lane_data,
            'counts': a.counts_detail,
            'emergency_detected': a.emergency_detected,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'results': data})


def _create_no_camera_frame():
    """Create a placeholder frame when no camera is available."""
    import cv2
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (20, 20, 30)
    cv2.putText(frame, 'No Camera Detected', (120, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 100, 200), 2)
    cv2.putText(frame, 'Connect a webcam to use Live mode', (100, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 1)
    return frame


def _apply_lane_data_to_database(lane_data, junction_id=None):
    """
    Helper to update database TrafficSignal objects and create VehicleCount & TrafficLog records
    based on real video analysis lane metrics.
    Automatically assigns GREEN to highest priority lane and RED to all other lanes.
    """
    from django.db import transaction
    from django.utils import timezone
    from signal_app.models import TrafficSignal, VehicleCount, TrafficLog

    detector, roi_manager, engine, controller = _get_services()
    signals_qs = TrafficSignal.objects.all()
    if junction_id:
        signals_qs = signals_qs.filter(junction_id=junction_id)

    now = timezone.now()
    updated = []
    signals_to_evaluate = []

    with transaction.atomic():
        for d in ('N', 'S', 'E', 'W'):
            info = lane_data.get(d)
            if not info:
                continue

            sig = signals_qs.filter(direction=d).first()
            if not sig:
                sig = TrafficSignal.objects.create(
                    direction=d,
                    current_state='RED',
                    mode='ADAPTIVE'
                )

            cnt = info.get('vehicle_count', 0)
            weighted_density = float(info.get('weighted_density', 0.0))
            green_time = int(info.get('green', 30))
            breakdown = info.get('type_breakdown', {})

            two_w = breakdown.get('motorcycle', 0) + breakdown.get('bicycle', 0)
            four_w = breakdown.get('car', 0)
            heavy = breakdown.get('bus', 0) + breakdown.get('truck', 0)
            emerg = breakdown.get('emergency', 0)

            # Update signal basic data
            sig.vehicle_count = cnt
            sig.current_weighted_density = weighted_density
            sig.green_time = green_time
            sig.yellow_time = engine.YELLOW_TIME
            sig.is_emergency_active = bool(emerg > 0)
            sig.save()

            # Record VehicleCount entry
            VehicleCount.objects.create(
                signal=sig,
                two_wheeler=two_w,
                four_wheeler=four_w,
                heavy_vehicle=heavy,
                emergency_vehicle=emerg,
                total_vehicles=cnt,
                weighted_score=weighted_density
            )

            signals_to_evaluate.append(sig)

        # Select highest priority lane to turn GREEN based on fresh video traffic density
        best_signal = engine.evaluate_signals(signals_to_evaluate, waiting_times={s.direction: 0 for s in signals_to_evaluate})
        emergency_sig = next((s for s in signals_to_evaluate if s.is_emergency_active), None)
        active_sig = emergency_sig or best_signal or (signals_to_evaluate[0] if signals_to_evaluate else None)

        if active_sig:
            active_green_time = engine.calculate_green_time(active_sig.current_weighted_density) if not active_sig.is_emergency_active else 60
            for sig in signals_to_evaluate:
                if sig.id == active_sig.id:
                    sig.current_state = 'GREEN'
                    sig.green_time = active_green_time
                    sig.state_start_time = now
                else:
                    sig.current_state = 'RED'
                    sig.red_time = active_green_time + engine.YELLOW_TIME
                    sig.state_start_time = now
                sig.save()

                TrafficLog.objects.create(
                    signal=sig,
                    vehicle_count=sig.vehicle_count,
                    weighted_density=sig.current_weighted_density,
                    signal_state=sig.current_state,
                    waiting_time=sig.red_time if sig.current_state == 'RED' else 0,
                    is_emergency=sig.is_emergency_active
                )

                updated.append({
                    'direction': sig.direction,
                    'direction_name': sig.get_direction_display(),
                    'state': sig.current_state,
                    'vehicle_count': sig.vehicle_count,
                    'weighted_density': sig.current_weighted_density,
                    'green_time': sig.green_time,
                    'remaining_time': sig.remaining_time,
                    'is_emergency': sig.is_emergency_active,
                })

    return updated


def signal_state_api(request):
    """
    GET: Return full real-time snapshot of the traffic signal state machine,
    including countdown timer (seconds + formatted), active state, densities, and next priority direction.
    """
    junction_id = request.GET.get('junction')
    signals = TrafficSignal.objects.all()
    if junction_id:
        signals = signals.filter(junction_id=junction_id)
    _, _, _, controller = _get_services()
    summary = controller.get_status_summary(list(signals))
    return JsonResponse(summary)



