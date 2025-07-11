from django.contrib import admin
from .models import Destination, Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'reviewer', 'rating', 'is_approved']
    list_filter = ['is_approved', 'rating']
    search_fields = ['booking__id', 'reviewer__username']

admin.register(Destination)