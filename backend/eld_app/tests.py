"""
 Test Suite for ELD Trip Planner
Author: Ezra Joseph
Date: October 2025

This file contains both integration and unit tests for the main 
ELD (Electronic Logging Device) trip planner backend built with Django.

Tests include:
- Integration tests for the create_trip API endpoint
- Unit tests for utility functions: decode_geometry() and generate_log_image()


"""

from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from datetime import datetime
from io import BytesIO
from PIL import Image

from eld_app.views import decode_geometry, generate_log_image


# ===============================================================
# Integration Tests for API endpoint: create_trip
# ===============================================================
class CreateTripViewTests(TestCase):
    """Integration tests for trip creation and route logic"""

    @patch("eld_app.views.config")
    @patch("eld_app.views.requests.post")
    @patch("eld_app.views.requests.get")
    def test_successful_trip_creation(self, mock_get, mock_post, mock_config):
        """
        TEST: Full trip creation workflow with valid data.

        Objective:
        - Verify that valid inputs (U.S. cities) produce a successful JSON response.
        - Confirm that the API correctly combines geocoding, routing, and ELD log generation.
        - Ensure the structure of the returned JSON matches expected output.
        """

        # Mock geocoding API (Nominatim) for 3 valid cities
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [
            [{"lat": 32.7767, "lon": -96.7970}],  # Dallas
            [{"lat": 40.7128, "lon": -74.0060}],  # NYC
            [{"lat": 34.0522, "lon": -118.2437}],  # LA
        ]

        # Mock API key and OpenRouteService API response
        mock_config.return_value = "fake_api_key_123"

        # Return a dummy route for both legs of the trip
        def mock_post_func(url, json, headers):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "routes": [
                    {
                        "geometry": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",  # sample polyline
                        "summary": {"distance": 10000, "duration": 3600},
                    }
                ]
            }
            return mock_resp

        mock_post.side_effect = mock_post_func

        # Payload simulating user input from frontend
        payload = {
            "currentLocation": "Dallas, TX",
            "pickupLocation": "New York, NY",
            "dropoffLocation": "Los Angeles, CA",
            "cycleHours": 10,
        }

        response = self.client.post(reverse("create_trip"), data=payload, content_type="application/json")

        # Assertions: verify success response and structure
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("route", data)
        self.assertIn("eld_logs", data)
        self.assertIsInstance(data["route"]["coordinates"], list)
        self.assertGreater(len(data["eld_logs"]), 0)

    @patch("eld_app.views.requests.get")
    def test_invalid_geocode_locations(self, mock_get):
        """
         TEST: Invalid or unrecognized locations.

        Objective:
        - Simulate geocoding returning empty results for invalid inputs.
        - Confirm that the API responds with 400 Bad Request.
        - Validate that 'Invalid locations' is included in the error message.
        """

        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = []

        payload = {
            "currentLocation": "InvalidCity",
            "pickupLocation": "FakePlace",
            "dropoffLocation": "GhostTown",
            "cycleHours": 5,
        }

        response = self.client.post(reverse("create_trip"), data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid locations", response.json()["error"])

    @patch("eld_app.views.config")
    @patch("eld_app.views.requests.get")
    def test_missing_api_key(self, mock_get, mock_config):
        """
         TEST: Missing OpenRouteService API key.

        Objective:
        - Confirm that if the API key is not loaded from environment, 
          the backend returns a 500 Internal Server Error.
        """

        # Mock successful geocoding results
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [
            [{"lat": 1, "lon": 1}],
            [{"lat": 2, "lon": 2}],
            [{"lat": 3, "lon": 3}],
        ]

        # Simulate missing API key
        mock_config.return_value = None

        payload = {
            "currentLocation": "Dallas",
            "pickupLocation": "Austin",
            "dropoffLocation": "Houston",
        }

        response = self.client.post(reverse("create_trip"), data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 500)
        self.assertIn("API key", response.json()["error"])

    @patch("eld_app.views.requests.get")
    @patch("eld_app.views.requests.post")
    @patch("eld_app.views.config")
    def test_second_route_fails(self, mock_config, mock_post, mock_get):
        """
         TEST: Simulate 404 error during second route (pickup -> dropoff).

        Objective:
        - The first route should succeed (current -> pickup).
        - The second should fail with a 404.
        - Confirm the backend handles it gracefully and returns 400 with a clear message.
        """

        # Mock geocoding valid responses
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [
            [{"lat": 32.7767, "lon": -96.7970}],
            [{"lat": 40.7128, "lon": -74.0060}],
            [{"lat": 34.0522, "lon": -118.2437}],
        ]

        mock_config.return_value = "fake_api_key_123"

        # Simulate first route OK, second route error
        mock_post.side_effect = [
            MagicMock(status_code=200, json=lambda: {
                "routes": [
                    {
                        "geometry": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
                        "summary": {"distance": 10000, "duration": 3600},
                    }
                ]
            }),
            MagicMock(status_code=404, json=lambda: {"error": {"code": 2010, "message": "Could not find route"}}),
        ]

        payload = {
            "currentLocation": "Dallas, TX",
            "pickupLocation": "New York, NY",
            "dropoffLocation": "Los Angeles, CA",
            "cycleHours": 10,
        }

        response = self.client.post(reverse("create_trip"), data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Second route calculation failed", response.json()["error"])


# ===============================================================
# Unit Tests for Helper Functions
# ===============================================================
class HelperFunctionTests(TestCase):
    """Unit tests for core utility functions used in trip creation"""

    def test_decode_geometry(self):
        """
        TEST: decode_geometry()

        Objective:
        - Validate that OpenRouteService encoded geometry strings 
          are properly decoded into coordinate pairs (lon, lat).
        """

        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"  # Known example
        coords = decode_geometry(encoded)
        self.assertTrue(isinstance(coords, list))
        self.assertGreater(len(coords), 0)
        self.assertEqual(len(coords[0]), 2)

    def test_generate_log_image(self):
        """
        TEST: generate_log_image()

        Objective:
        - Ensure the log generation function produces a valid PNG image
          with correct structure and binary format.
        - Validates PNG header bytes and confirms a valid PIL image object.
        """

        events = [
            {"hours": 0, "status": 0, "location": "Start"},
            {"hours": 4, "status": 2, "location": "Driving"},
            {"hours": 6, "status": 0, "location": "Stop"},
        ]
        day = datetime(2025, 10, 15)

        img = generate_log_image(day, events)
        self.assertIsInstance(img, Image.Image)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()

        # PNG header bytes always start with \x89PNG
        self.assertTrue(data.startswith(b"\x89PNG"))
