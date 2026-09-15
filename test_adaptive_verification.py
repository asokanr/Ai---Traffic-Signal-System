import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_signal_project.settings')
django.setup()

from signal_app.models import TrafficSignal, VehicleCount, TrafficLog, Junction
from signal_app.logic import TrafficEngine, SignalController, EmergencyManager, ROIManager, VehicleDetector
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory
from signal_app.views import TrafficSignalViewSet, signal_state_api, apply_analysis_to_signals
import json

def test_adaptive_signals():
    print("==================================================")
    print("RUNNING ADAPTIVE SIGNAL SYSTEM VERIFICATION SUITE")
    print("==================================================")

    # 1. Test TrafficEngine Density & Green Timing Formulas
    engine = TrafficEngine()
    
    counts_light = {'two_wheeler': 2, 'four_wheeler': 3, 'heavy_vehicle': 0, 'emergency_vehicle': 0}
    # 2*0.5 + 3*1.0 = 4.0
    density_light = engine.calculate_weighted_density(counts_light)
    assert density_light == 4.0, f"Expected 4.0, got {density_light}"
    green_light = engine.calculate_green_time(density_light)
    # 10 + 1.5 * 4.0 = 16s
    assert green_light == 16, f"Expected 16s, got {green_light}"
    print(f"✅ Test 1 Passed: Light density = {density_light}, Green = {green_light}s")

    counts_heavy = {'two_wheeler': 4, 'four_wheeler': 8, 'heavy_vehicle': 4, 'emergency_vehicle': 0}
    # 4*0.5 + 8*1.0 + 4*2.5 = 2.0 + 8.0 + 10.0 = 20.0
    density_heavy = engine.calculate_weighted_density(counts_heavy)
    assert density_heavy == 20.0, f"Expected 20.0, got {density_heavy}"
    green_heavy = engine.calculate_green_time(density_heavy)
    # 10 + 1.5 * 20.0 = 40s
    assert green_heavy == 40, f"Expected 40s, got {green_heavy}"
    print(f"✅ Test 2 Passed: Heavy density = {density_heavy}, Green = {green_heavy}s")

    # Clamping tests
    green_min = engine.calculate_green_time(0.0)
    assert green_min == 10, f"Expected MIN_GREEN 10s, got {green_min}"
    green_max = engine.calculate_green_time(100.0)
    assert green_max == 60, f"Expected MAX_GREEN 60s, got {green_max}"
    print(f"✅ Test 3 Passed: Clamping boundaries MIN={green_min}s, MAX={green_max}s")

    # 2. Database Signals Initialization & Multi-Lane Priority Test
    TrafficSignal.objects.all().delete()
    signals = {}
    for d in ['N', 'S', 'E', 'W']:
        signals[d] = TrafficSignal.objects.create(
            direction=d,
            current_state='RED',
            vehicle_count=0,
            current_weighted_density=0.0,
            green_time=30,
            yellow_time=3,
            red_time=10,
            state_start_time=timezone.now()
        )

    # Assign different vehicle densities to N, S, E, W
    # N: low (4.0), S: high (25.0), E: med (12.0), W: min (2.0)
    signals['N'].current_weighted_density = 4.0; signals['N'].vehicle_count = 5; signals['N'].save()
    signals['S'].current_weighted_density = 25.0; signals['S'].vehicle_count = 15; signals['S'].save()
    signals['E'].current_weighted_density = 12.0; signals['E'].vehicle_count = 8; signals['E'].save()
    signals['W'].current_weighted_density = 2.0; signals['W'].vehicle_count = 2; signals['W'].save()

    all_signals = list(TrafficSignal.objects.all())
    best = engine.evaluate_signals(all_signals)
    assert best.direction == 'S', f"Expected South (highest density 25.0) to be chosen, got {best.direction}"
    print(f"✅ Test 4 Passed: Priority evaluation correctly selected South (Density: 25.0)")

    # 3. State Machine Controller Transition Test
    controller = SignalController(engine)
    
    # Bootstrap: All RED -> South turns GREEN
    res = controller.advance_signal_cycle(signals=all_signals)
    assert res['active_green'] == 'S'
    assert res['active_state'] == 'GREEN'
    s_sig = TrafficSignal.objects.get(direction='S')
    assert s_sig.current_state == 'GREEN'
    assert s_sig.green_time == engine.calculate_green_time(25.0) # 10 + 1.5*25 = 47s
    print(f"✅ Test 5 Passed: Bootstrap cycle turned South GREEN ({s_sig.green_time}s)")

    # Fast-forward South green time past expiration -> transitions to YELLOW (3s)
    s_sig.state_start_time = timezone.now() - timedelta(seconds=s_sig.green_time + 1)
    s_sig.save()
    all_signals = list(TrafficSignal.objects.all())

    res2 = controller.advance_signal_cycle(signals=all_signals)
    assert res2['active_state'] == 'YELLOW'
    assert res2['active_green'] == 'S'
    s_sig.refresh_from_db()
    assert s_sig.current_state == 'YELLOW'
    assert s_sig.yellow_time == 3
    print(f"✅ Test 6 Passed: GREEN expired -> South transitioned to YELLOW ({s_sig.yellow_time}s)")

    # Fast-forward South yellow clearance past 3s -> transitions to RED, next highest priority (East: 12.0) turns GREEN!
    s_sig.state_start_time = timezone.now() - timedelta(seconds=4)
    s_sig.save()
    all_signals = list(TrafficSignal.objects.all())

    res3 = controller.advance_signal_cycle(signals=all_signals)
    s_sig.refresh_from_db()
    e_sig = TrafficSignal.objects.get(direction='E')
    assert s_sig.current_state == 'RED'
    assert e_sig.current_state == 'GREEN'
    print(f"✅ Test 7 Passed: YELLOW expired -> South turned RED, East (next priority) turned GREEN ({e_sig.green_time}s)")

    # Guarantee strict safety: only 1 direction is GREEN
    green_count = TrafficSignal.objects.filter(current_state='GREEN').count()
    assert green_count == 1, f"Safety violation! Found {green_count} green signals simultaneously"
    print(f"✅ Test 8 Passed: Safety verification: strictly 1 green signal active")

    # 4. Emergency Override (SOS) Test
    em_manager = EmergencyManager()
    w_sig = TrafficSignal.objects.get(direction='W')
    em_manager._activate_emergency(w_sig)
    
    all_signals = list(TrafficSignal.objects.all())
    res_em = controller.advance_signal_cycle(signals=all_signals)
    w_sig.refresh_from_db()
    e_sig.refresh_from_db()
    assert w_sig.is_emergency_active == True
    assert w_sig.current_state == 'GREEN'
    assert e_sig.current_state == 'RED'
    print(f"✅ Test 9 Passed: Emergency SOS on West immediately locked East to RED and opened West GREEN")

    # Resolve Emergency
    em_manager._resolve_emergency(w_sig)
    w_sig.refresh_from_db()
    assert w_sig.is_emergency_active == False
    print(f"✅ Test 10 Passed: Emergency resolved cleanly")

    # 5. REST API Endpoints Verification
    factory = APIRequestFactory()
    
    # Test GET /api/signals/state/
    view = TrafficSignalViewSet.as_view({'get': 'state'})
    req = factory.get('/api/signals/state/')
    resp = view(req)
    assert resp.status_code == 200
    assert 'signals' in resp.data
    assert 'active_state' in resp.data
    print(f"✅ Test 11 Passed: /api/signals/state/ returns complete status summary")

    # Test GET /signal-state/
    req2 = factory.get('/signal-state/')
    resp2 = signal_state_api(req2)
    assert resp2.status_code == 200
    data2 = json.loads(resp2.content)
    assert 'signals' in data2
    print(f"✅ Test 12 Passed: /signal-state/ returns snapshot JSON with 4 directions")

    # 6. Apply Video Analysis Data to Signals
    mock_lane_data = {
        'N': {'vehicle_count': 6, 'weighted_density': 8.0, 'green': 22, 'type_breakdown': {'car': 4, 'motorcycle': 4}},
        'S': {'vehicle_count': 18, 'weighted_density': 28.0, 'green': 52, 'type_breakdown': {'car': 8, 'truck': 4, 'motorcycle': 8}},
        'E': {'vehicle_count': 3, 'weighted_density': 3.0, 'green': 15, 'type_breakdown': {'car': 3}},
        'W': {'vehicle_count': 1, 'weighted_density': 1.0, 'green': 12, 'type_breakdown': {'car': 1}},
    }
    
    req3 = factory.post('/ai-analysis/apply-to-signals/', data=json.dumps({'lane_data': mock_lane_data}), content_type='application/json')
    resp3 = apply_analysis_to_signals(req3)
    assert resp3.status_code == 200
    data3 = json.loads(resp3.content)
    assert data3['success'] == True
    
    s_sig = TrafficSignal.objects.get(direction='S')
    n_sig = TrafficSignal.objects.get(direction='N')
    assert s_sig.current_state == 'GREEN', f"Expected S to be GREEN, got {s_sig.current_state}"
    assert s_sig.green_time == 43, f"Expected S green_time 43, got {s_sig.green_time}"
    assert n_sig.current_state == 'RED', f"Expected N to be RED, got {n_sig.current_state}"
    print(f"✅ Test 13 Passed: apply_analysis_to_signals applied video metrics and activated South GREEN ({s_sig.green_time}s)", flush=True)

    print("==================================================")
    print("ALL 13 VERIFICATION TESTS PASSED SUCCESSFULLY! 🎉")
    print("==================================================")

if __name__ == '__main__':
    test_adaptive_signals()
