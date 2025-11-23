from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f'UserProfile {self.id}'


class TripRequest(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    origin = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    preferred_time = models.CharField(max_length=100, blank=True)
    mode_preferences = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.origin} → {self.destination} [{self.id}]'


class Recommendation(models.Model):
    trip = models.ForeignKey(TripRequest, on_delete=models.CASCADE, related_name='recommendations')
    mode = models.CharField(max_length=100)
    eta_minutes = models.IntegerField()
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    score = models.FloatField(default=0.0)

    def to_dict(self):
        return {
            'mode': self.mode,
            'eta_minutes': self.eta_minutes,
            'cost': float(self.cost),
            'score': self.score,
        }


class Feedback(models.Model):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
