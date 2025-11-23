from django.urls import path
from .views import TripRequestCreateAPIView, RecommendationListAPIView, FeedbackCreateAPIView, RetrainAPIView, MapDataAPIView

urlpatterns = [
    path('trip_requests/', TripRequestCreateAPIView.as_view(), name='trip-create'),
    path('recommendations/', RecommendationListAPIView.as_view(), name='recommendations'),
    path('feedback/', FeedbackCreateAPIView.as_view(), name='feedback-create'),
    path('retrain/', RetrainAPIView.as_view(), name='retrain'),
    path('map-data/', MapDataAPIView.as_view(), name='map-data'),
]