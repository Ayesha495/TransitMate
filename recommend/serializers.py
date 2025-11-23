from rest_framework import serializers
from .models import TripRequest, Recommendation


class TripRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripRequest
        fields = ['id', 'user', 'origin', 'destination', 'preferred_time', 'mode_preferences', 'created_at']


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = ['id', 'trip', 'mode', 'eta_minutes', 'cost', 'score']


class FeedbackCreateSerializer(serializers.Serializer):
    trip_id = serializers.IntegerField(required=True)
    mode = serializers.CharField(max_length=100)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(allow_blank=True, required=False)
    eta_minutes = serializers.IntegerField(required=False)
    cost = serializers.FloatField(required=False)
    score = serializers.FloatField(required=False)

    def validate_trip_id(self, value):
        from .models import TripRequest
        try:
            TripRequest.objects.get(pk=value)
        except TripRequest.DoesNotExist:
            raise serializers.ValidationError('TripRequest not found')
        return value
