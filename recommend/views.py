from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import TripRequest, Recommendation
from .serializers import TripRequestSerializer, RecommendationSerializer
from .serializers import FeedbackCreateSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny
import subprocess
import sys
from pathlib import Path
import openrouteservice
from openrouteservice.directions import directions
from django.conf import settings
from django.http import HttpResponse
import json


def _build_features_for_model(trip, mode, mode_pref_flags, eta_minutes=0, cost=0.0):
    """Build same features as training script - UPDATED with ETA and cost"""
    
    # Original features
    origin_len = len(trip.origin or '')
    dest_len = len(trip.destination or '')
    airport = 1 if ('airport' in (trip.origin or '').lower() or 'airport' in (trip.destination or '').lower()) else 0
    
    try:
        hour = int((trip.preferred_time or '12').split(':')[0])
    except Exception:
        hour = 12
    
    mode_idx = {'Bus': 0, 'Metro': 1, 'RideShare': 2, 'Taxi': 3}.get(mode, 4)
    
    pref_bus = 1 if mode_pref_flags.get('bus') else 0
    pref_metro = 1 if mode_pref_flags.get('metro') else 0
    pref_rideshare = 1 if mode_pref_flags.get('rideshare') else 0
    pref_taxi = 1 if mode_pref_flags.get('taxi') else 0
    
    # NEW: Normalize ETA and cost (same as training script)
    eta_normalized = min(eta_minutes / 60.0, 2.0)  # cap at 2 hours
    cost_normalized = min(cost / 5000.0, 2.0)  # cap at 5000 PKR (adjusted for PKR)
    
    return [
        origin_len, 
        dest_len, 
        airport, 
        hour, 
        mode_idx, 
        pref_bus, 
        pref_metro, 
        pref_rideshare, 
        pref_taxi,
        eta_normalized,   # NEW
        cost_normalized   # NEW
    ]


def estimate_cost(mode, distance_meters):
    """Estimate cost based on mode and distance - PKR rates for Pakistan"""
    distance_km = distance_meters / 1000
    
    if mode == 'Bus':
        # Inter-city bus: ~6-7 PKR per km (Islamabad to Faisalabad = ~180km = 1600 PKR)
        return round((4 * distance_km), 2)
    elif mode == 'Metro':
        # Metro not available in most cities, use a basic estimate
        return round((3.5 * distance_km), 2)
    elif mode == 'RideShare':
        return round((25 * distance_km)/4,)
    elif mode == 'Taxi':
        # Taxi: ~65-70 PKR per km (Islamabad to Faisalabad = ~12000 PKR)
        return round((25 * distance_km),)
    return 0.0


def get_ors_route_data(origin, destination, mode):
    """Get route data from OpenRouteService API"""
    
    try:
        client = openrouteservice.Client(key=settings.ORS_API_KEY)
        
        # Map your modes to ORS profiles
        profile_mapping = {
            'Bus': 'driving-car',  # approximation
            'Metro': 'driving-car',  # approximation  
            'RideShare': 'driving-car',
            'Taxi': 'driving-car',
            'Walking': 'foot-walking',
            'Cycling': 'cycling-regular'
        }
        
        profile = profile_mapping.get(mode, 'driving-car')
        
        # Geocode addresses to coordinates first
        coords_origin = client.pelias_search(text=origin)
        coords_dest = client.pelias_search(text=destination)
        
        if not coords_origin['features'] or not coords_dest['features']:
            return None
            
        # Get coordinates [longitude, latitude] - note the order!
        start = coords_origin['features'][0]['geometry']['coordinates']
        end = coords_dest['features'][0]['geometry']['coordinates']
        
        # Get route
        route = client.directions(
            coordinates=[start, end],
            profile=profile,
            format='geojson'
        )
        
        if route and 'features' in route:
            feature = route['features'][0]
            props = feature['properties']
            
            # Extract duration (in seconds) and distance (in meters)
            duration_seconds = props['summary']['duration']
            distance_meters = props['summary']['distance']
            eta_minutes = int(duration_seconds / (60))
            
            # Estimate cost based on mode
            cost = estimate_cost(mode, distance_meters)
            
            return {
                'eta_minutes': eta_minutes,
                'cost': cost,
                'distance_meters': distance_meters,
                'geometry': feature['geometry']  # For displaying on map
            }
            
    except Exception as e:
        print(f"ORS API Error: {e}")
        return None


def generate_recommendations_for_trip(trip: TripRequest, use_ml: bool = True):
    """Updated recommendation generator with real routing"""
    
    # Parse user preferences
    mode_pref_flags = {}
    if trip.mode_preferences:
        for part in trip.mode_preferences.split(','):
            key = part.strip().lower()
            if key:
                mode_pref_flags[key] = True
    
    # Determine which modes to check
    all_modes = ['Bus', 'Metro', 'RideShare', 'Taxi']
    modes_to_check = [m for m in all_modes if m.lower() in mode_pref_flags] if mode_pref_flags else all_modes
    
    candidates = []
    
    # Get real routing data for each mode
    for mode in modes_to_check:
        route_data = get_ors_route_data(trip.origin, trip.destination, mode)
        
        if route_data:
            candidates.append({
                'mode': mode,
                'eta': route_data['eta_minutes'],
                'cost': route_data['cost'],  # Already in PKR from estimate_cost
                'distance': route_data['distance_meters']
            })
    
    # Fallback if no real data
    if not candidates:
        candidates = [
            {'mode': 'Bus', 'eta': 40, 'cost': 350},         # ~50km bus ride
            {'mode': 'Metro', 'eta': 25, 'cost': 180},       # ~25km metro
            {'mode': 'RideShare', 'eta': 20, 'cost': 700},   # ~20km rideshare
        ]
    
    # Now apply ML scoring
    model_path = Path(__file__).resolve().parent.parent / 'models' / 'recommender.pkl'
    model = None
    if use_ml and model_path.exists():
        try:
            import joblib
            model = joblib.load(model_path)
        except Exception:
            model = None
    
    recs = []
    if model is not None:
        # UPDATED: Pass eta and cost to feature builder
        feats = [
            _build_features_for_model(
                trip, 
                c['mode'], 
                mode_pref_flags,
                c['eta'],      # NEW: pass ETA
                c['cost']      # NEW: pass cost
            ) 
            for c in candidates
        ]
        try:
            scores = model.predict(feats)
        except Exception as e:
            print(f"Model prediction error: {e}")
            scores = [0.5] * len(candidates)
        
        for c, sc in zip(candidates, scores):
            recs.append({
                'mode': c['mode'],
                'eta_minutes': c['eta'],
                'cost': c['cost'],
                'score': float(sc)
            })
        recs.sort(key=lambda r: r['score'], reverse=True)
        return recs, True
    
    # Rule-based fallback
    for c in candidates:
        score = 0.6
        if c['mode'] == 'Metro':
            score = 0.8
        # Boost score for faster/cheaper options
        if c['eta'] < 20:
            score += 0.1
        # UPDATED: Adjusted threshold for PKR
        if c['cost'] < 1000:  # Less than 1000 PKR
            score += 0.05
        recs.append({
            'mode': c['mode'],
            'eta_minutes': c['eta'],
            'cost': c['cost'],
            'score': min(1.0, score)  # Cap at 1.0
        })
    
    return recs, False


class TripRequestCreateAPIView(APIView):
    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        if serializer.is_valid():
            trip = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecommendationListAPIView(APIView):
    def get(self, request):
        trip_id = request.query_params.get('trip_id')
        use_ml_param = request.query_params.get('use_ml')
        use_ml = True
        if use_ml_param is not None:
            use_ml = use_ml_param.lower() not in ('0','false','off')
        if not trip_id:
            return Response({'error': 'trip_id is required as a query parameter'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trip = TripRequest.objects.get(pk=trip_id)
        except TripRequest.DoesNotExist:
            return Response({'error': 'TripRequest not found'}, status=status.HTTP_404_NOT_FOUND)

        recs, used_model = generate_recommendations_for_trip(trip, use_ml=use_ml)
        return Response({'trip_id': trip_id, 'recommendations': recs, 'used_model': used_model})


class FeedbackCreateAPIView(APIView):
    """Accepts simple feedback and persists a Recommendation + Feedback record.

    Expected payload: { trip_id, mode, rating, comment, eta_minutes?, cost?, score? }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = FeedbackCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        trip = TripRequest.objects.get(pk=data['trip_id'])

        rec = Recommendation.objects.create(
            trip=trip,
            mode=data.get('mode', 'Unknown'),
            eta_minutes=data.get('eta_minutes', 0) or 0,
            cost=data.get('cost', 0.0) or 0.0,
            score=data.get('score', 0.0) or 0.0,
        )

        # Create feedback record
        from .models import Feedback

        fb = Feedback.objects.create(
            recommendation=rec,
            rating=data['rating'],
            comment=data.get('comment', '')
        )

        return Response({'status': 'ok', 'recommendation_id': rec.id, 'feedback_id': fb.id})


class RetrainAPIView(APIView):
    """Development-only endpoint to retrain the model by running the training script.

    POST /api/retrain/ will start training in a background process and return the PID.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        project_root = Path(__file__).resolve().parent.parent
        script = project_root / 'scripts' / 'train_recommender.py'
        if not script.exists():
            return Response({'error': 'training script not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # start the training script in background
            proc = subprocess.Popen([sys.executable, str(script)], cwd=str(project_root))
            return Response({'status': 'started', 'pid': proc.pid})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class MapDataAPIView(APIView):
    """Return map data as JSON for rendering in frontend"""
    permission_classes = [AllowAny]

    def get(self, request):
        trip_id = request.query_params.get('trip_id')
        mode = request.query_params.get('mode')
        
        if not trip_id:
            return Response({'error': 'trip_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            trip = TripRequest.objects.get(pk=trip_id)
        except TripRequest.DoesNotExist:
            return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get route data
        route_data = get_ors_route_data(trip.origin, trip.destination, mode or 'Bus')
        
        if not route_data:
            return Response({'error': 'Could not fetch route data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Extract coordinates from geometry
        coordinates = route_data['geometry']['coordinates']
        
        # Leaflet uses [lat, lng] but GeoJSON is [lng, lat], so we need to flip
        leaflet_coords = [[coord[1], coord[0]] for coord in coordinates]
        
        # Create HTML with embedded Leaflet map
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body {{ 
                    margin: 0; 
                    padding: 0; 
                    font-family: Arial, sans-serif;
                }}
                #map {{ 
                    position: absolute; 
                    top: 0; 
                    bottom: 0; 
                    width: 100%; 
                    height: 100%;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            
            <script>
                // Initialize the map
                var map = L.map('map');
                
                // Add OpenStreetMap tile layer
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }}).addTo(map);
                
                // Route coordinates
                var routeCoords = {json.dumps(leaflet_coords)};
                
                // Add route polyline
                var polyline = L.polyline(routeCoords, {{
                    color: '#4f46e5',
                    weight: 5,
                    opacity: 0.7
                }}).addTo(map);
                
                // Add start marker
                L.marker(routeCoords[0], {{
                    icon: L.divIcon({{
                        html: '<div style="background: #10b981; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                        className: 'custom-marker',
                        iconSize: [30, 30]
                    }})
                }}).addTo(map).bindPopup('<b>Start:</b> {trip.origin}');
                
                // Add end marker
                L.marker(routeCoords[routeCoords.length - 1], {{
                    icon: L.divIcon({{
                        html: '<div style="background: #ef4444; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                        className: 'custom-marker',
                        iconSize: [30, 30]
                    }})
                }}).addTo(map).bindPopup('<b>End:</b> {trip.destination}');
                
                // Fit map to show entire route
                map.fitBounds(polyline.getBounds(), {{padding: [50, 50]}});
            </script>
        </body>
        </html>
        """
        
        return Response({
            'html': html,
            'distance': route_data['distance_meters'],
            'eta_minutes': route_data['eta_minutes'],
            'cost': route_data['cost'],
            'origin': trip.origin,
            'destination': trip.destination
        })