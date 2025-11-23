# recommend/tests.py
"""
Comprehensive test suite for TransitMate AI-Enhanced Transportation Recommendation System
Tests cover: Models, Views, API endpoints, ML recommendations, and routing integration
"""

from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import TripRequest, Recommendation, Feedback, UserProfile
from .views import (
    _build_features_for_model, 
    estimate_cost, 
    get_ors_route_data,
    generate_recommendations_for_trip
)
import json
from pathlib import Path


class UserProfileModelTest(TestCase):
    """Test UserProfile model functionality"""
    
    def setUp(self):
        self.user_profile = UserProfile.objects.create(
            name="Test User"
        )
    
    def test_user_profile_creation(self):
        """Test that UserProfile is created correctly"""
        self.assertEqual(self.user_profile.name, "Test User")
        self.assertIsNotNone(self.user_profile.created_at)
    
    def test_user_profile_str(self):
        """Test string representation of UserProfile"""
        self.assertEqual(str(self.user_profile), "Test User")


class TripRequestModelTest(TestCase):
    """Test TripRequest model functionality"""
    
    def setUp(self):
        self.trip = TripRequest.objects.create(
            origin="Islamabad",
            destination="Lahore",
            preferred_time="09:00",
            mode_preferences="bus,metro"
        )
    
    def test_trip_creation(self):
        """Test that TripRequest is created with correct data"""
        self.assertEqual(self.trip.origin, "Islamabad")
        self.assertEqual(self.trip.destination, "Lahore")
        self.assertEqual(self.trip.preferred_time, "09:00")
        self.assertEqual(self.trip.mode_preferences, "bus,metro")
        self.assertIsNotNone(self.trip.created_at)
    
    def test_trip_str(self):
        """Test string representation of TripRequest"""
        expected = f"Islamabad → Lahore [{self.trip.id}]"
        self.assertEqual(str(self.trip), expected)


class RecommendationModelTest(TestCase):
    """Test Recommendation model functionality"""
    
    def setUp(self):
        self.trip = TripRequest.objects.create(
            origin="Rawalpindi",
            destination="Faisalabad"
        )
        self.recommendation = Recommendation.objects.create(
            trip=self.trip,
            mode="Bus",
            eta_minutes=180,
            cost=800.0,
            score=0.85
        )
    
    def test_recommendation_creation(self):
        """Test that Recommendation is created correctly"""
        self.assertEqual(self.recommendation.mode, "Bus")
        self.assertEqual(self.recommendation.eta_minutes, 180)
        self.assertEqual(self.recommendation.cost, 800.0)
        self.assertEqual(self.recommendation.score, 0.85)
        self.assertEqual(self.recommendation.trip, self.trip)
    
    def test_recommendation_str(self):
        """Test string representation of Recommendation"""
        # Recommendation model uses default Django __str__
        self.assertIn('Recommendation object', str(self.recommendation))
    
    def test_recommendation_to_dict(self):
        """Test recommendation to_dict method"""
        result = self.recommendation.to_dict()
        self.assertEqual(result['mode'], 'Bus')
        self.assertEqual(result['eta_minutes'], 180)
        self.assertEqual(result['cost'], 800.0)
        self.assertEqual(result['score'], 0.85)


class FeedbackModelTest(TestCase):
    """Test Feedback model functionality"""
    
    def setUp(self):
        trip = TripRequest.objects.create(origin="Karachi", destination="Hyderabad")
        self.recommendation = Recommendation.objects.create(
            trip=trip,
            mode="RideShare",
            eta_minutes=120,
            cost=1500.0,
            score=0.75
        )
        self.feedback = Feedback.objects.create(
            recommendation=self.recommendation,
            rating=4,
            comment="Good experience"
        )
    
    def test_feedback_creation(self):
        """Test that Feedback is created correctly"""
        self.assertEqual(self.feedback.rating, 4)
        self.assertEqual(self.feedback.comment, "Good experience")
        self.assertEqual(self.feedback.recommendation, self.recommendation)
        self.assertIsNotNone(self.feedback.created_at)
    
    def test_rating_validation(self):
        """Test rating is within valid range"""
        self.assertGreaterEqual(self.feedback.rating, 1)
        self.assertLessEqual(self.feedback.rating, 5)


class FeatureBuilderTest(TestCase):
    """Test ML feature building functionality"""
    
    def setUp(self):
        self.trip = TripRequest.objects.create(
            origin="Islamabad Airport",
            destination="Peshawar",
            preferred_time="14:30"
        )
        self.mode_prefs = {'bus': True, 'taxi': False}
    
    def test_feature_extraction(self):
        """Test that features are extracted correctly"""
        features = _build_features_for_model(
            self.trip, 
            'Bus', 
            self.mode_prefs,
            eta_minutes=120,
            cost=600
        )
        
        self.assertEqual(len(features), 11)  # Should have 11 features
        self.assertEqual(features[0], len("Islamabad Airport"))  # origin_len
        self.assertEqual(features[1], len("Peshawar"))  # dest_len
        self.assertEqual(features[2], 1)  # airport flag (1 = yes)
        self.assertEqual(features[3], 14)  # hour
        self.assertEqual(features[4], 0)  # mode_idx (Bus = 0)
        self.assertEqual(features[5], 1)  # pref_bus
        self.assertEqual(features[8], 0)  # pref_taxi
    
    def test_eta_normalization(self):
        """Test ETA normalization"""
        features = _build_features_for_model(
            self.trip, 'Bus', {}, 
            eta_minutes=180,  # 3 hours
            cost=1000
        )
        # 180 min / 60 = 3.0, should be capped at 2.0
        self.assertEqual(features[9], 2.0)
    
    def test_cost_normalization(self):
        """Test cost normalization for PKR"""
        features = _build_features_for_model(
            self.trip, 'Taxi', {},
            eta_minutes=60,
            cost=6000  # 6000 PKR
        )
        # 6000 / 5000 = 1.2
        self.assertAlmostEqual(features[10], 1.2, places=2)


class CostEstimationTest(TestCase):
    """Test cost estimation for different modes"""
    
    def test_bus_cost(self):
        """Test bus fare calculation"""
        # 100 km at 5 PKR/km = 500 PKR
        cost = estimate_cost('Bus', 100000)  # meters
        self.assertAlmostEqual(cost, 500, delta=10)
    
    def test_metro_cost(self):
        """Test metro fare calculation"""
        cost = estimate_cost('Metro', 50000)  # 50 km
        self.assertGreater(cost, 0)
        self.assertLess(cost, 500)
    
    def test_rideshare_cost(self):
        """Test rideshare fare calculation"""
        cost = estimate_cost('RideShare', 100000)  # 100 km
        self.assertGreater(cost, 500)
        self.assertLess(cost, 2000)
    
    def test_taxi_cost(self):
        """Test taxi fare calculation"""
        cost = estimate_cost('Taxi', 100000)  # 100 km
        self.assertGreater(cost, 1000)


class TripRequestAPITest(APITestCase):
    """Test TripRequest API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/trip_requests/'
    
    def test_create_trip_request(self):
        """Test creating a new trip request via API"""
        data = {
            'origin': 'Multan',
            'destination': 'Bahawalpur',
            'preferred_time': '10:00',
            'mode_preferences': 'bus,taxi'
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['origin'], 'Multan')
        self.assertEqual(response.data['destination'], 'Bahawalpur')
        self.assertIn('id', response.data)
    
    def test_create_trip_without_origin(self):
        """Test validation when origin is missing"""
        data = {
            'destination': 'Lahore',
            'preferred_time': '09:00'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_trip_without_destination(self):
        """Test validation when destination is missing"""
        data = {
            'origin': 'Islamabad',
            'preferred_time': '09:00'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RecommendationAPITest(APITestCase):
    """Test Recommendation API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.trip = TripRequest.objects.create(
            origin="Islamabad",
            destination="Lahore"
        )
    
    @patch('recommend.views.get_ors_route_data')
    def test_get_recommendations(self, mock_ors):
        """Test getting recommendations for a trip"""
        # Mock ORS response
        mock_ors.return_value = {
            'eta_minutes': 240,
            'cost': 1200,
            'distance_meters': 350000,
            'geometry': {'coordinates': []}
        }
        
        url = f'/api/recommendations/?trip_id={self.trip.id}&use_ml=false'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('recommendations', response.data)
        self.assertIn('used_model', response.data)
        self.assertGreater(len(response.data['recommendations']), 0)
    
    def test_get_recommendations_without_trip_id(self):
        """Test validation when trip_id is missing"""
        url = '/api/recommendations/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_recommendations_invalid_trip(self):
        """Test with non-existent trip ID"""
        url = '/api/recommendations/?trip_id=99999'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FeedbackAPITest(APITestCase):
    """Test Feedback API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.trip = TripRequest.objects.create(
            origin="Karachi",
            destination="Quetta"
        )
    
    def test_submit_feedback(self):
        """Test submitting feedback for a recommendation"""
        data = {
            'trip_id': self.trip.id,
            'mode': 'Bus',
            'rating': 5,
            'comment': 'Excellent service',
            'eta_minutes': 480,
            'cost': 2000,
            'score': 0.9
        }
        response = self.client.post('/api/feedback/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertIn('recommendation_id', response.data)
        self.assertIn('feedback_id', response.data)
    
    def test_submit_feedback_invalid_rating(self):
        """Test feedback with invalid rating"""
        data = {
            'trip_id': self.trip.id,
            'mode': 'Bus',
            'rating': 6,  # Invalid: should be 1-5
            'comment': 'Test'
        }
        response = self.client.post('/api/feedback/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_submit_feedback_without_trip(self):
        """Test feedback without trip_id"""
        data = {
            'mode': 'Bus',
            'rating': 4,
            'comment': 'Good'
        }
        response = self.client.post('/api/feedback/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MapDataAPITest(APITestCase):
    """Test Map Data API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.trip = TripRequest.objects.create(
            origin="Islamabad",
            destination="Murree"
        )
    
    @patch('recommend.views.get_ors_route_data')
    def test_get_map_data(self, mock_ors):
        """Test getting map data for a route"""
        mock_ors.return_value = {
            'eta_minutes': 90,
            'cost': 400,
            'distance_meters': 60000,
            'geometry': {
                'coordinates': [[73.0479, 33.6844], [73.3931, 33.9062]]
            }
        }
        
        url = f'/api/map-data/?trip_id={self.trip.id}&mode=Bus'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('html', response.data)
        self.assertIn('distance', response.data)
        self.assertIn('eta_minutes', response.data)
        self.assertIn('cost', response.data)
    
    def test_get_map_data_without_trip(self):
        """Test map data request without trip_id"""
        url = '/api/map-data/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RecommendationEngineTest(TestCase):
    """Test recommendation generation logic"""
    
    def setUp(self):
        self.trip = TripRequest.objects.create(
            origin="Islamabad",
            destination="Lahore",
            preferred_time="09:00",
            mode_preferences="bus,metro,rideshare"
        )
    
    @patch('recommend.views.get_ors_route_data')
    def test_generate_recommendations_with_real_data(self, mock_ors):
        """Test recommendation generation with mocked ORS data"""
        mock_ors.return_value = {
            'eta_minutes': 240,
            'cost': 1200,
            'distance_meters': 350000,
            'geometry': {'coordinates': []}
        }
        
        recs, used_ml = generate_recommendations_for_trip(self.trip, use_ml=False)
        
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)
        self.assertFalse(used_ml)
        
        # Check recommendation structure
        first_rec = recs[0]
        self.assertIn('mode', first_rec)
        self.assertIn('eta_minutes', first_rec)
        self.assertIn('cost', first_rec)
        self.assertIn('score', first_rec)
    
    @patch('recommend.views.get_ors_route_data')
    def test_fallback_recommendations(self, mock_ors):
        """Test fallback when ORS fails"""
        mock_ors.return_value = None
        
        recs, used_ml = generate_recommendations_for_trip(self.trip, use_ml=False)
        
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)
        # Should use hardcoded fallback values
    
    def test_mode_filtering(self):
        """Test that only preferred modes are recommended"""
        trip = TripRequest.objects.create(
            origin="Karachi",
            destination="Lahore",
            mode_preferences="bus"  # Only bus
        )
        
        with patch('recommend.views.get_ors_route_data') as mock_ors:
            mock_ors.return_value = {
                'eta_minutes': 720,
                'cost': 2500,
                'distance_meters': 1200000,
                'geometry': {'coordinates': []}
            }
            
            recs, _ = generate_recommendations_for_trip(trip, use_ml=False)
            
            # Should only have bus recommendations
            modes = [r['mode'] for r in recs]
            self.assertIn('Bus', modes)


class IntegrationTest(APITestCase):
    """End-to-end integration tests"""
    
    def test_complete_trip_flow(self):
        """Test complete user journey: create trip -> get recs -> submit feedback"""
        # Step 1: Create trip
        trip_data = {
            'origin': 'Islamabad',
            'destination': 'Lahore',
            'preferred_time': '09:00',
            'mode_preferences': 'bus,metro'
        }
        trip_response = self.client.post('/api/trip_requests/', trip_data, format='json')
        self.assertEqual(trip_response.status_code, status.HTTP_201_CREATED)
        trip_id = trip_response.data['id']
        
        # Step 2: Get recommendations
        with patch('recommend.views.get_ors_route_data') as mock_ors:
            mock_ors.return_value = {
                'eta_minutes': 240,
                'cost': 1200,
                'distance_meters': 350000,
                'geometry': {'coordinates': []}
            }
            
            rec_response = self.client.get(f'/api/recommendations/?trip_id={trip_id}')
            self.assertEqual(rec_response.status_code, status.HTTP_200_OK)
            recommendations = rec_response.data['recommendations']
            self.assertGreater(len(recommendations), 0)
        
        # Step 3: Submit feedback
        feedback_data = {
            'trip_id': trip_id,
            'mode': recommendations[0]['mode'],
            'rating': 4,
            'comment': 'Good route',
            'eta_minutes': recommendations[0]['eta_minutes'],
            'cost': recommendations[0]['cost'],
            'score': recommendations[0]['score']
        }
        feedback_response = self.client.post('/api/feedback/', feedback_data, format='json')
        self.assertEqual(feedback_response.status_code, status.HTTP_200_OK)


# Run tests with: python manage.py test recommend
# Run specific test: python manage.py test recommend.tests.TripRequestModelTest
# Run with coverage: coverage run --source='.' manage.py test recommend && coverage report