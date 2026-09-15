from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import json

from signal_app.models import TrafficSignal, Junction, VideoAnalysis, VehicleCount, TrafficLog
from signal_app.logic import ROIManager, TrafficEngine, SignalController, VehicleDetector


class ROIManagerTestCase(TestCase):
    def setUp(self):
        self.roi = ROIManager()

    def test_assign_direction_four_quadrants(self):
        w, h = 640, 480
        self.assertEqual(self.roi.assign_direction(320, 50, w, h), 'N')
        self.assertEqual(self.roi.assign_direction(320, 430, w, h), 'S')
        self.assertEqual(self.roi.assign_direction(580, 240, w, h), 'E')
        self.assertEqual(self.roi.assign_direction(50, 240, w, h), 'W')

    def test_get_roi_config(self):
        config = self.roi.get_roi_config()
        self.assertIn('directions', config)
        self.assertIn('N', config['directions'])
        self.assertIn('S', config['directions'])
        self.assertIn('E', config['directions'])
        self.assertIn('W', config['directions'])
        self.assertEqual(len(config['directions']['N']), 4)


class TrafficEngineTestCase(TestCase):
    def setUp(self):
        self.engine = TrafficEngine()

    def test_calculate_weighted_density(self):
        # 2 motorcycles (0.5 each = 1.0) + 2 cars (1.0 each = 2.0) + 1 truck (2.5) = 5.5
        types = {'motorcycle': 2, 'car': 2, 'truck': 1}
        density = self.engine.calculate_weighted_density(types)
        self.assertEqual(density, 5.5)

    def test_classify_density(self):
        self.assertEqual(self.engine.classify_density(5.0), 'LOW')
        self.assertEqual(self.engine.classify_density(15.0), 'MEDIUM')
        self.assertEqual(self.engine.classify_density(32.0), 'HIGH')
        self.assertEqual(self.engine.classify_density(45.0), 'VERY HIGH')

    def test_calculate_green_time_boundaries(self):
        self.assertEqual(self.engine.calculate_green_time(0.0), 10)
        self.assertEqual(self.engine.calculate_green_time(100.0), 60)
        # Mid density test
        mid_time = self.engine.calculate_green_time(15.0)
        self.assertTrue(10 <= mid_time <= 60)

    def test_anti_starvation_priority(self):
        # Lane with density 5 waiting 60s should beat lane with density 20 waiting 0s
        score_waited = self.engine.calculate_priority_score(5.0, waiting_time=60)
        score_nowait = self.engine.calculate_priority_score(20.0, waiting_time=0)
        self.assertGreater(score_waited, score_nowait)


class SignalControllerTestCase(TestCase):
    def setUp(self):
        self.controller = SignalController()
        for d in ['N', 'S', 'E', 'W']:
            TrafficSignal.objects.create(
                direction=d,
                current_state='RED',
                vehicle_count=5,
                green_time=20
            )

    def test_advance_signal_cycle_green_to_yellow(self):
        n_sig = TrafficSignal.objects.get(direction='N')
        n_sig.current_state = 'GREEN'
        n_sig.green_time = 1
        n_sig.state_start_time = timezone.now() - timedelta(seconds=2)
        n_sig.save()

        signals = list(TrafficSignal.objects.all())
        result = self.controller.advance_signal_cycle(signals=signals)
        
        n_sig.refresh_from_db()
        self.assertEqual(n_sig.current_state, 'YELLOW')

    def test_advance_signal_cycle_yellow_to_red_and_next_green(self):
        n_sig = TrafficSignal.objects.get(direction='N')
        n_sig.current_state = 'YELLOW'
        n_sig.state_start_time = timezone.now() - timedelta(seconds=6)
        n_sig.save()

        signals = list(TrafficSignal.objects.all())
        result = self.controller.advance_signal_cycle(signals=signals)

        n_sig.refresh_from_db()
        self.assertEqual(n_sig.current_state, 'RED')

        # Check another signal turned green
        green_sig = TrafficSignal.objects.filter(current_state='GREEN').first()
        self.assertIsNotNone(green_sig)
        self.assertNotEqual(green_sig.id, n_sig.id)


class AIAnalysisAPITestCase(TestCase):
    def setUp(self):
        for d in ['N', 'S', 'E', 'W']:
            TrafficSignal.objects.create(
                direction=d,
                current_state='RED',
                vehicle_count=0,
                green_time=20
            )

    def test_roi_config_api(self):
        response = self.client.get('/api/ai-analysis/roi-config/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('directions', data)
        self.assertIn('N', data['directions'])
        self.assertIn('S', data['directions'])

    def test_camera_check_api(self):
        response = self.client.get('/api/ai-analysis/camera-check/')
        self.assertEqual(response.status_code, 200)

    def test_apply_analysis_to_signals_api(self):
        payload = {
            'lane_data': {
                'N': {'vehicle_count': 12, 'weighted_density': 15.0, 'green': 32, 'type_breakdown': {'car': 10, 'motorcycle': 2}},
                'S': {'vehicle_count': 4, 'weighted_density': 4.0, 'green': 16, 'type_breakdown': {'car': 4}},
                'E': {'vehicle_count': 8, 'weighted_density': 10.0, 'green': 25, 'type_breakdown': {'car': 8}},
                'W': {'vehicle_count': 2, 'weighted_density': 2.0, 'green': 13, 'type_breakdown': {'car': 2}},
            }
        }
        response = self.client.post(
            '/api/ai-analysis/apply-to-signals/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        n_sig = TrafficSignal.objects.get(direction='N')
        self.assertEqual(n_sig.vehicle_count, 12)
        self.assertEqual(n_sig.green_time, 32)
