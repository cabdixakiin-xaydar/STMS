from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Destination, RoomType, TourPackage, TourGuide, UnavailabilityPeriod, Vehicle, 
    Accommodation, Booking, Payment, Review,
    Promotion, EmergencyContact, DestinationImage,
    AccommodationImage
)
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()

class DestinationForm(forms.ModelForm):
    class Meta:
        model = Destination
        fields = ['name', 'description', 'location', 'latitude', 'longitude', 'is_featured']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001'
            }),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_featured': _('Feature this destination'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add required attribute to required fields
        self.fields['name'].required = True
        self.fields['location'].required = True
        
        # Add placeholder text
        self.fields['latitude'].widget.attrs['placeholder'] = 'e.g. 2.0469'
        self.fields['longitude'].widget.attrs['placeholder'] = 'e.g. 45.3181'

class DestinationImageForm(forms.ModelForm):
    class Meta:
        model = DestinationImage
        fields = ['image', 'caption', 'is_featured']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Optional image caption'}),
        }

class TourPackageForm(forms.ModelForm):
    destinations = forms.ModelMultipleChoiceField(
        queryset=Destination.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        required=True,
        help_text=_("Select destinations included in this package")
    )
    
    class Meta:
        model = TourPackage
        fields = [
            'name', 'description', 'destinations', 'duration_days', 
            'price_usd', 'discount_percentage', 'package_type', 'is_active',
            'highlights', 'inclusions', 'exclusions'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_usd': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'package_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'highlights': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'inclusions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'exclusions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'price_usd': _("Base Price (USD)"),
            'discount_percentage': _("Discount (%)"),
        }
        help_texts = {
            'discount_percentage': _("Enter percentage discount (0-100)"),
            }

class TourGuideForm(forms.ModelForm):
    class Meta:
        model = TourGuide
        fields = [
            'license_number', 'languages', 'years_of_experience', 
            'specialization', 'is_available', 'hourly_rate', 'bio'
        ]
        widgets = {
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'languages': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'English, Somali, Arabic'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.01
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about your experience and expertise...'
            }),
        }
        labels = {
            'license_number': _('License Number'),
            'languages': _('Languages Spoken'),
            'years_of_experience': _('Years of Experience'),
            'specialization': _('Specialization'),
            'is_available': _('Currently Available'),
            'hourly_rate': _('Hourly Rate (USD)'),
            'bio': _('Biography'),
        }

    def clean_license_number(self):
        license_number = self.cleaned_data['license_number']
        if TourGuide.objects.filter(license_number=license_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_('A guide with this license number already exists.'))
        return license_number

class UnavailabilityPeriodForm(forms.ModelForm):
    class Meta:
        model = UnavailabilityPeriod
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for unavailability (optional)'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_('End date must be after start date.'))

        return cleaned_data

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'make', 'model', 'year', 'vehicle_type', 'capacity', 
            'license_plate', 'is_available', 'daily_rate', 'features', 'image'
        ]
        widgets = {
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'features': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_license_plate(self):
        license_plate = self.cleaned_data['license_plate'].upper()
        if Vehicle.objects.filter(license_plate=license_plate).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A vehicle with this license plate already exists.")
        return license_plate

class AccommodationForm(forms.ModelForm):
    class Meta:
        model = Accommodation
        fields = '__all__'  # Or specify your fields explicitly
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'accommodation_type': forms.Select(attrs={'class': 'form-control'}),
            'destination': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'star_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5
            }),
            'room_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'price_range_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'price_range_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'amenities': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control'
            }),
            'check_in_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'check_out_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        price_min = cleaned_data.get('price_range_min')
        price_max = cleaned_data.get('price_range_max')
        
        if price_min and price_max and price_min > price_max:
            raise forms.ValidationError(
                _("Maximum price must be greater than or equal to minimum price.")
            )
        return cleaned_data

class AccommodationImageForm(forms.ModelForm):
    class Meta:
        model = AccommodationImage
        fields = ['image', 'caption', 'is_featured']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class RoomTypeForm(forms.ModelForm):
    class Meta:
        model = RoomType
        fields = ['name', 'description', 'capacity', 'price_per_night', 'is_available', 'features']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'price_per_night': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
            'features': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': _('Comma separated list of features')
            }),
        }

class BookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set querysets based on user type
        if user and not user.is_staff:
            self.fields['tour_package'].queryset = TourPackage.objects.filter(is_active=True)
            self.fields['accommodation'].queryset = Accommodation.objects.all()
            self.fields['vehicle'].queryset = Vehicle.objects.filter(is_available=True)
            self.fields['guide'].queryset = TourGuide.objects.filter(is_available=True)
        
        # Set date inputs to use HTML5 date picker
        self.fields['start_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['end_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})

    class Meta:
        model = Booking
        fields = [
            'tour_package', 'accommodation', 'vehicle', 'guide',
            'start_date', 'end_date', 'number_of_people', 'special_requests'
        ]
        widgets = {
            'tour_package': forms.Select(attrs={'class': 'form-control'}),
            'accommodation': forms.Select(attrs={'class': 'form-control'}),
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'guide': forms.Select(attrs={'class': 'form-control'}),
            'number_of_people': forms.NumberInput(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date < timezone.now().date():
                raise ValidationError(_("Start date cannot be in the past"))
            if start_date > end_date:
                raise ValidationError(_("End date must be after start date"))
        
        return cleaned_data

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=Review.RATING_CHOICES, attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = [
            'title', 'description', 'discount_percentage', 
            'start_date', 'end_date', 'target_audience', 'is_active', 'image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'target_audience': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError(_("End date must be after start date"))
        
        return cleaned_data

class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = ['name', 'contact_type', 'phone_number', 'location', 'available_24_7', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_type': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'available_24_7': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Add any phone number validation here
        return phone_number

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'user_type', 'email', 'phone_number', 'first_name', 'last_name'
        )
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }