from django.contrib import admin
from .models import UserProfile, TripRequest, Recommendation, Feedback


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')


@admin.register(TripRequest)
class TripRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'origin', 'destination', 'created_at')


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip', 'mode', 'eta_minutes', 'cost', 'score')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation', 'rating', 'created_at')
