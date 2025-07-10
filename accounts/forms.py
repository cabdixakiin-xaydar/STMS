from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, 
    UserChangeForm, 
    AuthenticationForm, 
    PasswordChangeForm
)
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, UserProfile, NotificationPreferences, TouristProfile, GuideProfile
from django.contrib.auth import authenticate

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type',
                 'phone_number', 'profile_picture', 'password1', 'password2')
        labels = {
            'username': _('Username'),
            'email': _('Email'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'user_type': _('User Type'),
            'phone_number': _('Phone Number'),
            'profile_picture': _('Profile Picture'),
        }

class TouristRegistrationForm(UserCreationForm):
    address = forms.CharField(widget=forms.Textarea)
    gender = forms.ChoiceField(choices=[
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other'))
    ])
    age = forms.IntegerField(min_value=1, max_value=120)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 
                 'date_of_birth', 'password1', 'password2', 'address', 'gender', 'age')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'TOURIST'
        if commit:
            user.save()
            TouristProfile.objects.create(
                user=user,
                address=self.cleaned_data['address'],
                gender=self.cleaned_data['gender'],
                age=self.cleaned_data['age']
            )
            UserProfile.objects.create(user=user)
            NotificationPreferences.objects.create(user=user)
        return user

class GuideRegistrationForm(UserCreationForm):
    license_number = forms.CharField(max_length=50)
    spoken_languages = forms.CharField(max_length=255)
    biography = forms.CharField(widget=forms.Textarea)
    hourly_rate = forms.DecimalField(max_digits=6, decimal_places=2)
    years_experience = forms.IntegerField(min_value=0)
    specialization = forms.CharField(max_length=100)
    is_available = forms.BooleanField(required=False)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 
                 'password1', 'password2', 'license_number', 'spoken_languages', 
                 'biography', 'hourly_rate', 'years_experience', 'specialization', 'is_available')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'GUIDE'
        user.status = 'PENDING'
        if commit:
            user.save()
            GuideProfile.objects.create(
                user=user,
                license_number=self.cleaned_data['license_number'],
                spoken_languages=self.cleaned_data['spoken_languages'],
                biography=self.cleaned_data['biography'],
                hourly_rate=self.cleaned_data['hourly_rate'],
                years_experience=self.cleaned_data['years_experience'],
                specialization=self.cleaned_data['specialization'],
                is_available=self.cleaned_data['is_available']
            )
            UserProfile.objects.create(user=user)
            NotificationPreferences.objects.create(user=user)
        return user

class GuideApprovalForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['status']
        widgets = {
            'status': forms.Select(choices=CustomUser.STATUS_CHOICES)
        }

class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_('Username or Email'))
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise ValidationError(_("Please enter a correct username and password."))
            elif not self.user_cache.is_active:
                raise ValidationError(_("This account is inactive."))
        return self.cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'address', 'emergency_contact', 'emergency_phone']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'bio': _('About Me'),
            'address': _('Address'),
            'emergency_contact': _('Emergency Contact Name'),
            'emergency_phone': _('Emergency Contact Phone'),
        }

class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = NotificationPreferences
        fields = ['email_notifications', 'sms_notifications', 'push_notifications']
        labels = {
            'email_notifications': _('Receive email notifications'),
            'sms_notifications': _('Receive SMS notifications'),
            'push_notifications': _('Receive push notifications'),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
        labels = {
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email'),
            'phone_number': _('Phone Number'),
            'profile_picture': _('Profile Picture'),
        }

class UserCreationFormWithPassword(UserCreationForm):
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=_("Enter a strong password with at least 8 characters."),
    )
    password2 = forms.CharField(
        label=_("Password Confirmation"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'user_type', 'first_name', 'last_name', 
                 'phone_number', 'profile_picture', 'password1', 'password2')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                _("The two password fields didn't match."),
                code='password_mismatch',
            )
        validate_password(password2, self.instance)
        return password2

class UserEditForm(UserChangeForm):
    password = None  # Remove the password field

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 
                 'user_type', 'phone_number', 'profile_picture',
                 'date_of_birth', 'nationality', 'preferred_language',
                 'is_active', 'is_staff', 'is_superuser')
        
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(CustomPasswordChangeForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})