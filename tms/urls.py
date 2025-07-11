# tms/urls.py
from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'tms'

urlpatterns = [
    # Home and Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
            # Dashboard/Home URLs
    path('tourist-home/', views.tourist_home, name='tourist_home'),
    path('guide-dashboard/', views.guide_dashboard, name='guide_dashboard'),

    path('', views.home, name='home'),
    
    # Destinations
    path('destinations/', views.DestinationListView.as_view(), name='destination-list'),
    path('destinations/<int:pk>/', views.DestinationDetailView.as_view(), name='destination-detail'),
    path('destinations/create/', views.DestinationCreateView.as_view(), name='destination-create'),
    path('destinations/<int:pk>/update/', views.DestinationUpdateView.as_view(), name='destination-update'),
    path('destinations/<int:pk>/delete/', views.DestinationDeleteView.as_view(), name='destination-delete'),
    path('destinations/<int:pk>/add-image/', views.add_destination_image, name='destination-add-image'),
    
    # Tour Packages
    path('packages/', views.TourPackageListView.as_view(), name='package-list'),
    path('packages/<int:pk>/', views.TourPackageDetailView.as_view(), name='package-detail'),
    path('packages/create/', views.TourPackageCreateView.as_view(), name='package-create'),
    path('packages/<int:pk>/update/', views.TourPackageUpdateView.as_view(), name='package-update'),
    path('packages/<int:pk>/delete/', views.TourPackageDeleteView.as_view(), name='package-delete'),
    
    # Bookings
    path('bookings/', views.BookingListView.as_view(), name='booking-list'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/create/', views.BookingCreateView.as_view(), name='booking-create'),
    path('bookings/<int:pk>/update/', views.BookingUpdateView.as_view(), name='booking-update'),
    path('bookings/<int:pk>/delete/', views.BookingDeleteView.as_view(), name='booking-delete'),
    path('bookings/<int:booking_id>/payment/', views.process_payment, name='booking-payment'),

     # QR Code Download
    path('bookings/<int:pk>/qr-code/', views.download_qr_code, name='qr-code'),
    
    # Tour Guides
    path('guides/', views.TourGuideListView.as_view(), name='guide-list'),
    path('guides/<int:pk>/', views.TourGuideDetailView.as_view(), name='guide-detail'),
    path('guides/create/', views.TourGuideCreateView.as_view(), name='guide-create'),
    path('guides/<int:pk>/update/', views.TourGuideUpdateView.as_view(), name='guide-update'),
    path('guides/<int:pk>/delete/', views.TourGuideDeleteView.as_view(), name='guide-delete'),
    path('guides/<int:pk>/availability/', views.TourGuideAvailabilityView.as_view(), name='guide-availability'),
    path('guides/<int:pk>/add-unavailability/', views.add_unavailability_period, name='guide-add-unavailability'),
    path('api/guides/<int:pk>/check-availability/', views.check_guide_availability, name='guide-check-availability'),
    
    # Vehicles
    path('vehicles/', views.VehicleListView.as_view(), name='vehicle-list'),
    path('vehicles/add/', views.VehicleCreateView.as_view(), name='vehicle-create'),
    path('vehicles/<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle-detail'),
    path('vehicles/<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='vehicle-update'),
    path('vehicles/<int:pk>/delete/', views.VehicleDeleteView.as_view(), name='vehicle-delete'),
    path('vehicles/<int:pk>/availability/', views.VehicleAvailabilityView.as_view(), name='vehicle-availability'),
    
    # Accommodations
    path('accommodations/', views.AccommodationListView.as_view(), name='accommodation-list'),
    path('accommodations/create/', views.AccommodationCreateView.as_view(), name='accommodation-create'),
    path('accommodations/<int:pk>/', views.AccommodationDetailView.as_view(), name='accommodation-detail'),
    path('accommodations/<int:pk>/update/', views.AccommodationUpdateView.as_view(), name='accommodation-update'),
    path('accommodations/<int:pk>/delete/', views.AccommodationDeleteView.as_view(), name='accommodation-delete'),
    path('accommodations/<int:pk>/add-image/', views.AccommodationAddImageView.as_view(), name='accommodation-add-image'),
    path('accommodations/<int:pk>/availability/', views.AccommodationAvailabilityView.as_view(), name='accommodation-availability'),
    path('accommodations/<int:pk>/room-types/', views.RoomTypeListView.as_view(), name='accommodation-room-types'),
    path('accommodations/<int:accommodation_pk>/set-featured-image/<int:image_pk>/', 
         views.AccommodationSetFeaturedImageView.as_view(), 
         name='accommodation-set-featured-image'),
    path('accommodations/<int:accommodation_pk>/delete-image/<int:image_pk>/', 
         views.AccommodationDeleteImageView.as_view(), 
         name='accommodation-delete-image'),
    
    # Room Types
    path('accommodations/<int:pk>/room-types/create/', views.RoomTypeCreateView.as_view(), name='roomtype-create'),
    path('room-types/<int:pk>/update/', views.RoomTypeUpdateView.as_view(), name='roomtype-update'),
    path('room-types/<int:pk>/delete/', views.RoomTypeDeleteView.as_view(), name='roomtype-delete'),
    
    # API Endpoints
    path('api/accommodations/autocomplete/', views.AccommodationAutocompleteView.as_view(), name='accommodation-autocomplete'),
    
     # Reviews
    path('bookings/<int:booking_pk>/review/', views.ReviewCreateView.as_view(), name='review-create'),
    path('reviews/', views.ReviewListView.as_view(), name='review-list'),
    path('reviews/<int:pk>/', views.ReviewDetailView.as_view(), name='review-detail'),  # Keep only this one
    path('reviews/<int:pk>/edit/', views.ReviewUpdateView.as_view(), name='review-update'),
    path('reviews/management/', views.ReviewManagementView.as_view(), name='review-management'),
    path('reviews/<int:pk>/toggle-approve/', views.toggle_review_approval, name='review-toggle-approve'),
    path('my-reviews/', views.UserReviewListView.as_view(), name='user-reviews'),


    # Promotions
    path('promotions/', views.PromotionListView.as_view(), name='promotion-list'),
    
    # Emergency Contacts
    path('emergency/', views.EmergencyContactListView.as_view(), name='emergency-list'),
    path('emergency/create/', views.EmergencyContactCreateView.as_view(), name='emergency-create'),
    path('emergency/<int:pk>/', views.EmergencyContactDetailView.as_view(), name='emergency-detail'),
    path('emergency/<int:pk>/update/', views.EmergencyContactUpdateView.as_view(), name='emergency-update'),
    path('emergency/<int:pk>/delete/', views.EmergencyContactDeleteView.as_view(), name='emergency-delete'),
    
    # Reports
    path('reports/bookings/', views.BookingListView.as_view(template_name='tms/reports/bookings.html'), name='report-bookings'),
    path('reports/revenue/', TemplateView.as_view(template_name='tms/reports/revenue.html'), name='report-revenue'),
    path('reports/tourism-stats/', TemplateView.as_view(template_name='tms/reports/tourism_stats.html'), name='report-tourism-stats'),
    
    # API Endpoints
    path('api/check-availability/', views.check_availability, name='check-availability'),
    
    # Search
    path('search/', views.search, name='search'),
    
    # Static Pages
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_as_read, name='mark-notification-read'),
    
    # System Settings (Admin only)
    path('system-settings/', TemplateView.as_view(template_name='tms/admin/system_settings.html'), name='system-settings'),


    # Add this to your urlpatterns list
    path('bookings/calendar/', views.BookingCalendarView.as_view(), name='booking-calendar'),
    path('drivers/', views.DriverListView.as_view(), name='driver-list'),

    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),

    path('reviews/', views.ReviewListView.as_view(), name='review-list'),
]