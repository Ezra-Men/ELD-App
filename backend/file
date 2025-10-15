from django.test import TestCase, Client
from django.urls import reverse
import json
from unittest.mock import patch, MagicMock

class TripViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.trip_url = reverse('create_trip')

    @patch('eld_app.views.requests.post')
    @patch('eld_app.views.config')
    def test_valid_trip_creation(self, mock_config, mock_post):
        # Mock API key
        mock_config.return_value = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRhNTczMDgzZThhNDQ0ZDQ5ZTAyYWIzNmQxZmVhMTA3IiwiaCI6Im11cm11cjY0In0='
        
        # Mock successful API responses (both routes)
        def mock_post_side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'features': [{
                    'geometry': {'coordinates': [[-87.6298, 41.8781], [-90.2500, 38.6270]]},
                    'properties': {'segments': [{'distance': 500000, 'duration': 18000}]}
                }]
            }
            return mock_response
        
        mock_post.side_effect = mock_post_side_effect
        
        data = {
            'currentLocation': 'Chicago, IL',
            'pickupLocation': 'St. Louis, MO',
            'dropoffLocation': 'Dallas, TX',
            'cycleHours': 20
        }
        
        response = self.client.post(self.trip_url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('route', response.json())
        self.assertIn('eld_logs', response.json())
        self.assertIn('coordinates', response.json()['route'])
        self.assertIn('stops', response.json()['route'])
        self.assertGreater(len(response.json()['eld_logs']), 0)
        self.assertGreater(len(response.json()['route']['stops']), 0)
        print("✅ test_valid_trip_creation PASSED")

    @patch('eld_app.views.requests.get')
    def test_invalid_location(self, mock_get):
        # Mock geocoding to fail for current location
        def mock_get_side_effect(url, **kwargs):
            if 'InvalidPlace' in url:
                mock_response = MagicMock()
                mock_response.json.return_value = []
                return mock_response
            else:
                mock_response = MagicMock()
                mock_response.json.return_value = [{'lat': '38.6270', 'lon': '-90.2500'}]
                return mock_response
        
        mock_get.side_effect = mock_get_side_effect
        
        data = {
            'currentLocation': 'InvalidPlace',
            'pickupLocation': 'St. Louis, MO',
            'dropoffLocation': 'Dallas, TX',
            'cycleHours': 20
        }
        
        response = self.client.post(self.trip_url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertIn('Invalid locations', response.json()['error'])
        print("✅ test_invalid_location PASSED")

    @patch('eld_app.views.requests.post')
    @patch('eld_app.views.config')
    def test_70hr_limit_enforcement(self, mock_config, mock_post):
        # Mock API key
        mock_config.return_value = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRhNTczMDgzZThhNDQ0ZDQ5ZTAyYWIzNmQxZmVhMTA3IiwiaCI6Im11cm11cjY0In0='
        
        # Mock API responses for a longer trip that triggers 70hr limit
        def mock_post_side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'features': [{
                    'geometry': {'coordinates': [[-87.6298, 41.8781], [-96.8005, 32.7767]]},
                    'properties': {'segments': [{'distance': 2000000, 'duration': 72000}]}
                }]
            }
            return mock_response
        
        mock_post.side_effect = mock_post_side_effect
        
        data = {
            'currentLocation': 'Chicago, IL',
            'pickupLocation': 'St. Louis, MO',
            'dropoffLocation': 'Dallas, TX',
            'cycleHours': 60  # High cycle hours to test 70hr limit
        }
        
        response = self.client.post(self.trip_url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('route', response.json())
        self.assertIn('eld_logs', response.json())
        # Verify multiple days are generated due to 70hr limit
        self.assertGreater(len(response.json()['eld_logs']), 1)
        print("✅ test_70hr_limit_enforcement PASSED")