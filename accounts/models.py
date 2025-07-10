from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        return self.create_user(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('TOURIST', 'Tourist'),
        ('GUIDE', 'Tour Guide'),
        ('ADMIN', 'System Admin'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Waiting to approve'),
        ('APPROVED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='TOURIST')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    preferred_language = models.CharField(max_length=10, blank=True, null=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)
    
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"Profile of {self.user.username}"

class TouristProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='tourist_profile')
    address = models.TextField()
    gender = models.CharField(max_length=10)
    age = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tourist Profile")
        verbose_name_plural = _("Tourist Profiles")

    def __str__(self):
        return f"Tourist Profile for {self.user.username}"

class GuideProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='guide_profile')
    license_number = models.CharField(max_length=50, unique=True)
    spoken_languages = models.CharField(max_length=255)
    biography = models.TextField()
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2)
    years_experience = models.PositiveIntegerField()
    specialization = models.CharField(max_length=100)
    is_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Guide Profile")
        verbose_name_plural = _("Guide Profiles")

    def __str__(self):
        return f"Guide Profile for {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            self.user.user_type = 'GUIDE'
            self.user.status = 'PENDING'
            self.user.save()
        super().save(*args, **kwargs)

class NotificationPreferences(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Notification Preference")
        verbose_name_plural = _("Notification Preferences")

    def __str__(self):
        return f"Notification preferences for {self.user.username}"