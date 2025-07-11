from decimal import Decimal
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User

User = get_user_model()

class TimeStampedModel(models.Model):
    """Abstract base model with created and modified timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Destination(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"))
    location = models.CharField(_("Location"), max_length=100)
    latitude = models.DecimalField(
        _("Latitude"), 
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        _("Longitude"), 
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )
    is_featured = models.BooleanField(_("Featured"), default=False)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_destinations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Destination")
        verbose_name_plural = _("Destinations")
        ordering = ['-is_featured', 'name']

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('tms:destination-detail', kwargs={'pk': self.pk})
    
    @property
    def coordinates(self):
        if self.latitude and self.longitude:
            return f"{self.latitude}, {self.longitude}"
        return None

class DestinationImage(models.Model):
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_("Image"), upload_to='destination_images/')
    caption = models.CharField(_("Caption"), max_length=200, blank=True)
    is_featured = models.BooleanField(_("Featured Image"), default=False)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Uploaded By")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Destination Image")
        verbose_name_plural = _("Destination Images")
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.destination.name}"




class TourPackage(models.Model):
    PACKAGE_TYPES = (
        ('ADVENTURE', _('Adventure')),
        ('CULTURAL', _('Cultural')),
        ('HISTORICAL', _('Historical')),
        ('BEACH', _('Beach')),
        ('COMBINED', _('Combined')),
    )
    
    name = models.CharField(_("Package Name"), max_length=200)
    description = models.TextField(_("Description"))
    destinations = models.ManyToManyField('Destination', verbose_name=_("Destinations"))
    duration_days = models.PositiveIntegerField(_("Duration (days)"))
    price_usd = models.DecimalField(_("Base Price (USD)"), max_digits=10, decimal_places=2)
    discount_percentage = models.PositiveIntegerField(
        _("Discount Percentage"), 
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    package_type = models.CharField(_("Package Type"), max_length=20, choices=PACKAGE_TYPES)
    is_active = models.BooleanField(_("Active"), default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_packages')
    highlights = models.TextField(_("Package Highlights"), blank=True)
    inclusions = models.TextField(_("What's Included"), blank=True)
    exclusions = models.TextField(_("What's Not Included"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tour Package")
        verbose_name_plural = _("Tour Packages")
        ordering = ['-is_active', 'name']

    def current_price(self):
        discount_factor = Decimal(1) - Decimal(self.discount_percentage) / Decimal(100)
        return round(self.price_usd * discount_factor, 2)
    
    def __str__(self):
        return f"{self.name} ({self.duration_days} days)"
    
    def get_absolute_url(self):
        return reverse('tms:package-detail', kwargs={'pk': self.pk})


class UnavailabilityPeriod(models.Model):
    guide = models.ForeignKey('TourGuide', on_delete=models.CASCADE, related_name='unavailability_periods')
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    reason = models.TextField(_("Reason"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Unavailability Period")
        verbose_name_plural = _("Unavailability Periods")
        ordering = ['start_date']

    def __str__(self):
        return f"Unavailable from {self.start_date} to {self.end_date}"

class TourGuide(models.Model):
    LANGUAGES = (
        ('EN', _('English')),
        ('SO', _('Somali')),
        ('AR', _('Arabic')),
        ('FR', _('French')),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    license_number = models.CharField(_("License Number"), max_length=50, unique=True)
    languages = models.CharField(_("Languages"), max_length=100)
    years_of_experience = models.PositiveIntegerField(_("Years of Experience"))
    specialization = models.CharField(_("Specialization"), max_length=100)
    is_available = models.BooleanField(_("Available"), default=True)
    hourly_rate = models.DecimalField(_("Hourly Rate"), max_digits=6, decimal_places=2)
    rating = models.DecimalField(_("Rating"), max_digits=3, decimal_places=2, default=0.0)
    bio = models.TextField(_("Biography"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Tour Guide")
        verbose_name_plural = _("Tour Guides")
        ordering = ['-is_available', '-rating']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.specialization})"
    
    def get_absolute_url(self):
        return reverse('tms:guide-detail', kwargs={'pk': self.pk})
    
    def is_available_on_date(self, date):
        """Check if guide is available on a specific date"""
        if not self.is_available:
            return False
        return not self.unavailability_periods.filter(
            start_date__lte=date,
            end_date__gte=date
        ).exists()

class Vehicle(models.Model):
    VEHICLE_TYPES = (
        ('SEDAN', _('Sedan')),
        ('SUV', _('SUV')),
        ('MINIVAN', _('Minivan')),
        ('BUS', _('Bus')),
        ('4X4', _('4x4')),
    )
    
    make = models.CharField(_("Make"), max_length=50)
    model = models.CharField(_("Model"), max_length=50)
    year = models.PositiveIntegerField(_("Year"), validators=[MinValueValidator(1900)])
    vehicle_type = models.CharField(_("Type"), max_length=10, choices=VEHICLE_TYPES)
    capacity = models.PositiveIntegerField(_("Capacity"), validators=[MinValueValidator(1)])
    license_plate = models.CharField(_("License Plate"), max_length=20, unique=True)
    is_available = models.BooleanField(_("Available"), default=True)
    daily_rate = models.DecimalField(_("Daily Rate"), max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    features = models.TextField(_("Features"), blank=True)
    image = models.ImageField(_("Vehicle Image"), upload_to='vehicle_images/', blank=True, null=True)
    
    class Meta:
        verbose_name = _("Vehicle")
        verbose_name_plural = _("Vehicles")
        ordering = ['-is_available', 'make', 'model']

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.license_plate})"
    
    def get_absolute_url(self):
        return reverse('tms:vehicle-detail', kwargs={'pk': self.pk})
    
    def get_vehicle_types():
        return [choice[0] for choice in Vehicle.VEHICLE_TYPES]

class Accommodation(TimeStampedModel):
    ACCOMMODATION_TYPES = (
        ('HOTEL', _('Hotel')),
        ('LODGE', _('Lodge')),
        ('GUESTHOUSE', _('Guesthouse')),
        ('RESORT', _('Resort')),
        ('CAMP', _('Camp')),
    )
    
    name = models.CharField(_("Name"), max_length=100)
    accommodation_type = models.CharField(_("Type"), max_length=20, choices=ACCOMMODATION_TYPES)
    destination = models.ForeignKey('Destination', on_delete=models.CASCADE, verbose_name=_("Destination"))
    address = models.TextField(_("Address"))
    contact_phone = models.CharField(_("Contact Phone"), max_length=20)
    contact_email = models.EmailField(_("Contact Email"), blank=True)
    website = models.URLField(_("Website"), blank=True)
    star_rating = models.PositiveIntegerField(
        _("Star Rating"), 
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    room_capacity = models.PositiveIntegerField(_("Room Capacity"))
    price_range_min = models.DecimalField(_("Min Price"), max_digits=8, decimal_places=2)
    price_range_max = models.DecimalField(_("Max Price"), max_digits=8, decimal_places=2)
    amenities = models.TextField(_("Amenities"), blank=True)
    check_in_time = models.TimeField(_("Check-in Time"), default='14:00')
    check_out_time = models.TimeField(_("Check-out Time"), default='12:00')
    is_active = models.BooleanField(_("Active"), default=True)
    description = models.TextField(_("Description"), blank=True)
    
    class Meta:
        verbose_name = _("Accommodation")
        verbose_name_plural = _("Accommodations")
        ordering = ['-star_rating', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_accommodation_type_display()})"
    
    def get_absolute_url(self):
        return reverse('tms:accommodation-detail', kwargs={'pk': self.pk})
    
    @property
    def amenities_list(self):
        return [a.strip() for a in self.amenities.split(',') if a.strip()]

class AccommodationImage(models.Model):
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_("Image"), upload_to='accommodation_images/')
    caption = models.CharField(_("Caption"), max_length=200, blank=True)
    is_featured = models.BooleanField(_("Featured Image"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', 'created_at']
        verbose_name = _("Accommodation Image")
        verbose_name_plural = _("Accommodation Images")

    def __str__(self):
        return self.caption or f"Image for {self.accommodation.name}"

class RoomType(models.Model):
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(_("Room Type"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    capacity = models.PositiveIntegerField(_("Capacity"))
    price_per_night = models.DecimalField(_("Price per Night"), max_digits=8, decimal_places=2)
    is_available = models.BooleanField(_("Available"), default=True)
    features = models.TextField(_("Features"), blank=True)

    class Meta:
        verbose_name = _("Room Type")
        verbose_name_plural = _("Room Types")
        ordering = ['price_per_night']

    def __str__(self):
        return f"{self.name} - {self.accommodation.name}"

class Booking(TimeStampedModel):
    BOOKING_STATUS = (
        ('PENDING', _('Pending')),
        ('CONFIRMED', _('Confirmed')),
        ('CANCELLED', _('Cancelled')),
        ('COMPLETED', _('Completed')),
    )
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Customer"), related_name='bookings')
    tour_package = models.ForeignKey(
        TourPackage, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Tour Package")
    )
    accommodation = models.ForeignKey(
        Accommodation, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Accommodation")
    )
    vehicle = models.ForeignKey(
        Vehicle, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Vehicle")
    )
    guide = models.ForeignKey(
        TourGuide, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Guide")
    )
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    number_of_people = models.PositiveIntegerField(_("Number of People"), default=1)
    special_requests = models.TextField(_("Special Requests"), blank=True)
    status = models.CharField(
        _("Status"), 
        max_length=20, 
        choices=BOOKING_STATUS, 
        default='PENDING'
    )
    total_amount = models.DecimalField(_("Total Amount"), max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(
        _("Amount Paid"), 
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    booking_reference = models.CharField(
        _("Booking Reference"), 
        max_length=20, 
        unique=True
    )
    qr_code = models.ImageField(_("QR Code"), upload_to='qr_codes/', blank=True, null=True)
    
    class Meta:
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.booking_reference}"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        super().save(*args, **kwargs)
    
    def generate_booking_reference(self):
        from django.utils.crypto import get_random_string
        return f"STMS-{get_random_string(8, '0123456789ABCDEF')}"
    
    def calculate_total(self):
        total = 0
        if self.tour_package:
            days = (self.end_date - self.start_date).days or 1
            total += self.tour_package.current_price() * self.number_of_people * days
        
        if self.accommodation:
            days = (self.end_date - self.start_date).days or 1
            total += self.accommodation.price_range_max * self.number_of_people * days
        
        if self.vehicle:
            days = (self.end_date - self.start_date).days or 1
            total += self.vehicle.daily_rate * days
        
        if self.guide:
            days = (self.end_date - self.start_date).days or 1
            total += self.guide.hourly_rate * 8 * days  # 8 hours per day
        
        return round(total, 2)
    
    def get_absolute_url(self):
        return reverse('booking-detail', kwargs={'pk': self.pk})
    
    def days_remaining(self):
        return (self.start_date - timezone.now().date()).days
    
    def is_upcoming(self):
        return self.start_date > timezone.now().date() and self.status == 'CONFIRMED'

class Payment(TimeStampedModel):
    PAYMENT_METHODS = (
        ('EDAHAB', _('Edahab')),
        ('ZAAD', _('Zaad')),
        ('CASH', _('Cash')),
        ('CREDIT_CARD', _('Credit Card')),
        ('BANK_TRANSFER', _('Bank Transfer')),
    )
    
    PAYMENT_STATUS = (
        ('PENDING', _('Pending')),
        ('COMPLETED', _('Completed')),
        ('FAILED', _('Failed')),
        ('REFUNDED', _('Refunded')),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, verbose_name=_("Booking"), related_name='payments')
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        _("Payment Method"), 
        max_length=20, 
        choices=PAYMENT_METHODS
    )
    transaction_id = models.CharField(_("Transaction ID"), max_length=100)
    payment_status = models.CharField(
        _("Payment Status"), 
        max_length=20, 
        choices=PAYMENT_STATUS, 
        default='PENDING'
    )
    notes = models.TextField(_("Notes"), blank=True)
    
    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment of {self.amount} for {self.booking}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    def generate_transaction_id(self):
        from django.utils.crypto import get_random_string
        return f"PYMT-{get_random_string(12, '0123456789ABCDEF')}"

class Review(TimeStampedModel):
    RATING_CHOICES = [
        (1, '★☆☆☆☆ - Poor'),
        (2, '★★☆☆☆ - Fair'),
        (3, '★★★☆☆ - Good'),
        (4, '★★★★☆ - Very Good'),
        (5, '★★★★★ - Excellent'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, verbose_name=_("Booking"), related_name='review')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Reviewer"), related_name='reviews')
    rating = models.PositiveIntegerField(_("Rating"), choices=RATING_CHOICES)
    comment = models.TextField(_("Comment"))
    is_approved = models.BooleanField(_("Approved"), default=False)
    
    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.reviewer} for {self.booking}"
    
    def get_rating_stars(self):
        return '★' * self.rating + '☆' * (5 - self.rating)

class Promotion(TimeStampedModel):
    TARGET_AUDIENCE = (
        ('ALL', _('All Customers')),
        ('DIASPORA', _('Diaspora')),
        ('STUDENTS', _('Students')),
        ('FAMILIES', _('Families')),
        ('LOCALS', _('Local Residents')),
    )
    
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"))
    discount_percentage = models.PositiveIntegerField(
        _("Discount Percentage"), 
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    target_audience = models.CharField(
        _("Target Audience"), 
        max_length=20, 
        choices=TARGET_AUDIENCE, 
        default='ALL'
    )
    is_active = models.BooleanField(_("Active"), default=True)
    image = models.ImageField(_("Promotion Image"), upload_to='promotion_images/', blank=True, null=True)
    
    class Meta:
        verbose_name = _("Promotion")
        verbose_name_plural = _("Promotions")
        ordering = ['-is_active', '-start_date']

    def __str__(self):
        return f"{self.title} ({self.discount_percentage}% off)"
    
    def is_current(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date and self.is_active

class EmergencyContact(models.Model):
    CONTACT_TYPES = (
        ('POLICE', _('Police')),
        ('HOSPITAL', _('Hospital')),
        ('AMBULANCE', _('Ambulance')),
        ('FIRE', _('Fire Department')),
        ('TOURISM_POLICE', _('Tourism Police')),
        ('EMBASSY', _('Embassy')),
    )
    
    name = models.CharField(_("Name"), max_length=100)
    contact_type = models.CharField(_("Type"), max_length=20, choices=CONTACT_TYPES)
    phone_number = models.CharField(_("Phone Number"), max_length=20)
    location = models.CharField(_("Location"), max_length=100)
    available_24_7 = models.BooleanField(_("Available 24/7"), default=True)
    notes = models.TextField(_("Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Emergency Contact")
        verbose_name_plural = _("Emergency Contacts")
        ordering = ['contact_type', 'name']

    def __str__(self):
        return f"{self.get_contact_type_display()}: {self.name}"

class Notification(TimeStampedModel):
    NOTIFICATION_TYPES = (
        ('BOOKING', _('Booking')),
        ('PAYMENT', _('Payment')),
        ('WEATHER', _('Weather Alert')),
        ('SECURITY', _('Security Alert')),
        ('PROMOTION', _('Promotion')),
        ('SYSTEM', _('System Notification')),
        ('REVIEW', _('Review')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"), related_name='notifications')
    notification_type = models.CharField(_("Type"), max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(_("Title"), max_length=200)
    message = models.TextField(_("Message"))
    is_read = models.BooleanField(_("Read"), default=False)
    related_object_id = models.PositiveIntegerField(_("Related Object"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} notification for {self.user}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50)
    license_expiry = models.DateField()
    vehicle_assigned = models.ForeignKey('Vehicle', on_delete=models.SET_NULL, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.license_number})"