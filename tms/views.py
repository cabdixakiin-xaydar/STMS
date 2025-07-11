import datetime
import os
from django.conf import settings
from django.utils import timezone  
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Sum, Count
from django.http import FileResponse, Http404, JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache
from django.db.models import Avg
from pydantic import ValidationError
from django.contrib.admin.views.decorators import staff_member_required

from accounts import admin


from .models import Driver 
from .models import (
    Destination, RoomType, TourPackage, TourGuide, Vehicle, 
    Accommodation, Booking, Payment, Review,
    Promotion, EmergencyContact, Notification,
    DestinationImage, AccommodationImage
)
from .forms import (
    DestinationForm, RoomTypeForm, TourPackageForm, TourGuideForm, UnavailabilityPeriodForm,
    VehicleForm, AccommodationForm, BookingForm,
    PaymentForm, ReviewForm, PromotionForm,
    EmergencyContactForm, DestinationImageForm,
    AccommodationImageForm
)
from accounts.models import CustomUser


from django.shortcuts import render

def home(request):
    return render(request, 'home.html')


# Helper functions
def generate_qr_code(booking):
    import qrcode
    from io import BytesIO
    from django.core.files import File
    from django.conf import settings
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    data = f"STMS Booking\nReference: {booking.booking_reference}\nCustomer: {booking.customer.get_full_name()}\n"
    if booking.tour_package:
        data += f"Package: {booking.tour_package.name}\n"
    data += f"Dates: {booking.start_date} to {booking.end_date}\n"
    data += f"Amount: ${booking.total_amount}"
    
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    file_name = f'qr_{booking.booking_reference}.png'
    booking.qr_code.save(file_name, File(buffer), save=True)
    
    return booking.qr_code.url

def send_booking_notification(booking):
    # Notification for customer
    Notification.objects.create(
        user=booking.customer,
        notification_type='BOOKING',
        title=_("Booking Confirmation"),
        message=_("Your booking #{ref} has been confirmed.").format(ref=booking.booking_reference),
        related_object_id=booking.id
    )
    
    # Notification for admin/staff (if applicable)
    if booking.tour_package and booking.tour_package.created_by:
        Notification.objects.create(
            user=booking.tour_package.created_by,
            notification_type='BOOKING',
            title=_("New Booking"),
            message=_("New booking #{ref} for package {package}").format(
                ref=booking.booking_reference,
                package=booking.tour_package.name
            ),
            related_object_id=booking.id
        )
class BookingCalendarView(ListView):
    template_name = 'tms/bookings/calendar.html'
    model = Booking
    context_object_name = 'bookings'

    def get_queryset(self):
        # Get bookings for the current month
        today = timezone.now().date()
        return Booking.objects.filter(
            start_date__month=today.month,
            start_date__year=today.year
        ).order_by('start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_month'] = timezone.now().date()
        return context



#Driver  

class DriverListView(ListView):
    model = Driver
    template_name = 'tms/drivers/list.html'
    context_object_name = 'drivers'


# Base Views
class StaffRequiredMixin:
    """Verify that the current user is staff or has operator/ministry role."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff or request.user.user_type in ['OPERATOR', 'MINISTRY']):
            raise PermissionDenied(_("You don't have permission to access this page."))
        return super().dispatch(request, *args, **kwargs)

class OwnerRequiredMixin:
    """Verify that the current user owns this item."""
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.created_by != request.user and not request.user.is_staff:
            raise PermissionDenied(_("You don't have permission to access this page."))
        return super().dispatch(request, *args, **kwargs)

class DestinationListView(ListView):
    model = Destination
    template_name = 'tms/destinations/list.html'
    context_object_name = 'destinations'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset()
        featured = self.request.GET.get('featured')
        search = self.request.GET.get('search')
        
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search) |
                Q(description__icontains=search)
            ).distinct()
        
        return queryset.order_by('-is_featured', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_count'] = Destination.objects.filter(is_featured=True).count()
        context['search_query'] = self.request.GET.get('search', '')
        context['featured_filter'] = self.request.GET.get('featured', '')
        return context

class DestinationDetailView(DetailView):
    model = Destination
    template_name = 'tms/destinations/detail.html'
    context_object_name = 'destination'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['packages'] = self.object.tourpackage_set.filter(is_active=True)[:4]
        context['featured_images'] = self.object.images.filter(is_featured=True)
        context['all_images'] = self.object.images.all()
        
        # Safely get today's bookings if the relationship exists
        if hasattr(self.object, 'bookings'):
            context['today_bookings'] = self.object.bookings.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).count()
        else:
            context['today_bookings'] = 0
            
        return context

@method_decorator(login_required, name='dispatch')
class DestinationCreateView(StaffRequiredMixin, CreateView):
    model = Destination
    form_class = DestinationForm
    template_name = 'tms/destinations/form.html'
    success_url = reverse_lazy('tms:destination-list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Destination created successfully!"))
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

@method_decorator(login_required, name='dispatch')
class DestinationUpdateView(StaffRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Destination
    form_class = DestinationForm
    template_name = 'tms/destinations/form.html'
    success_url = reverse_lazy('tms:destination-list')
    
    def form_valid(self, form):
        messages.success(self.request, _("Destination updated successfully!"))
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

@method_decorator(login_required, name='dispatch')
class DestinationDeleteView(StaffRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Destination
    template_name = 'tms/destinations/confirm_delete.html'
    success_url = reverse_lazy('tms:destination-list')
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _("Destination deleted successfully!"))
        return response

@login_required
def add_destination_image(request, pk):
    destination = get_object_or_404(Destination, pk=pk)
    
    if request.method == 'POST':
        form = DestinationImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.destination = destination
            image.uploaded_by = request.user
            image.save()
            messages.success(request, _("Image added successfully!"))
            return redirect('tms:destination-detail', pk=destination.pk)
    else:
        form = DestinationImageForm()
    
    return render(request, 'tms/destinations/add_image.html', {
        'destination': destination,
        'form': form
    })

# Tour Package Views
class TourPackageListView(ListView):
    model = TourPackage
    template_name = 'tms/packages/list.html'
    context_object_name = 'packages'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-staff users, only show active packages
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        # Filter by package type if provided
        package_type = self.request.GET.get('type')
        if package_type:
            queryset = queryset.filter(package_type=package_type)
        
        # Filter by destination if provided
        destination_id = self.request.GET.get('destination')
        if destination_id:
            queryset = queryset.filter(destinations__id=destination_id)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(destinations__name__icontains=search)
            ).distinct()
        
        return queryset.select_related('created_by').prefetch_related('destinations').order_by('-is_active', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['package_types'] = dict(TourPackage.PACKAGE_TYPES)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_destination'] = self.request.GET.get('destination', '')
        return context

class TourPackageDetailView(DetailView):
    model = TourPackage
    template_name = 'tms/packages/detail.html'
    context_object_name = 'package'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_packages'] = TourPackage.objects.filter(
            destinations__in=self.object.destinations.all(),
            is_active=True
        ).exclude(id=self.object.id).distinct()[:4]
        return context

@method_decorator(login_required, name='dispatch')
class TourPackageCreateView(StaffRequiredMixin, CreateView):
    model = TourPackage
    form_class = TourPackageForm
    template_name = 'tms/packages/form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Tour package created successfully!"))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('tms:package-detail', kwargs={'pk': self.object.pk})

@method_decorator(login_required, name='dispatch')
class TourPackageUpdateView(StaffRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = TourPackage
    form_class = TourPackageForm
    template_name = 'tms/packages/form.html'
    
    def form_valid(self, form):
        messages.success(self.request, _("Tour package updated successfully!"))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('tms:package-detail', kwargs={'pk': self.object.pk})

@method_decorator(login_required, name='dispatch')
class TourPackageDeleteView(StaffRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = TourPackage
    template_name = 'tms/packages/confirm_delete.html'
    success_url = reverse_lazy('tms:package-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Tour package deleted successfully!"))
        return super().delete(request, *args, **kwargs)

# Tour Guide Views
class TourGuideListView(ListView):
    model = TourGuide
    template_name = 'tms/guides/list.html'
    context_object_name = 'guides'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        
        # Filter by specialization if provided
        specialization = self.request.GET.get('specialization')
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)
        
        # Filter by language if provided
        language = self.request.GET.get('language')
        if language:
            queryset = queryset.filter(languages__icontains=language)
        
        return queryset.order_by('-is_available', '-rating')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specialization_filter'] = self.request.GET.get('specialization', '')
        context['language_filter'] = self.request.GET.get('language', '')
        return context

class TourGuideDetailView(DetailView):
    model = TourGuide
    template_name = 'tms/guides/detail.html'
    context_object_name = 'guide'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.request.user.is_staff or self.request.user.user_type in ['OPERATOR', 'MINISTRY']
        return context

class TourGuideCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = TourGuide
    form_class = TourGuideForm
    template_name = 'tms/guides/form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, _('Tour guide created successfully!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('tms:guide-detail', kwargs={'pk': self.object.pk})

class TourGuideUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = TourGuide
    form_class = TourGuideForm
    template_name = 'tms/guides/form.html'
    
    def form_valid(self, form):
        messages.success(self.request, _('Tour guide updated successfully!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('tms:guide-detail', kwargs={'pk': self.object.pk})

class TourGuideDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = TourGuide
    template_name = 'tms/guides/confirm_delete.html'
    success_url = reverse_lazy('tms:guide-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Tour guide deleted successfully!'))
        return super().delete(request, *args, **kwargs)

class TourGuideAvailabilityView(LoginRequiredMixin, DetailView):
    model = TourGuide
    template_name = 'tms/guides/availability.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unavailability_periods'] = self.object.unavailability_periods.all()
        context['can_edit'] = self.request.user.is_staff or self.request.user.user_type in ['OPERATOR', 'MINISTRY']
        return context

def add_unavailability_period(request, pk):
    guide = get_object_or_404(TourGuide, pk=pk)
    
    if not (request.user.is_staff or request.user.user_type in ['OPERATOR', 'MINISTRY']):
        messages.error(request, _('You do not have permission to perform this action.'))
        return redirect('tms:guide-availability', pk=guide.pk)
    
    if request.method == 'POST':
        form = UnavailabilityPeriodForm(request.POST)
        if form.is_valid():
            unavailability = form.save(commit=False)
            unavailability.guide = guide
            unavailability.save()
            messages.success(request, _('Unavailability period added successfully!'))
            return redirect('tms:guide-availability', pk=guide.pk)
    else:
        form = UnavailabilityPeriodForm()
    
    return render(request, 'tms/guides/availability.html', {
        'guide': guide,
        'form': form,
        'unavailability_periods': guide.unavailability_periods.all(),
        'show_modal': True
    })

def check_guide_availability(request, pk):
    guide = get_object_or_404(TourGuide, pk=pk)
    date = request.GET.get('date')
    
    if not date:
        return JsonResponse({'error': 'Date parameter is required'}, status=400)
    
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        is_available = guide.is_available_on_date(date_obj)
        
        return JsonResponse({
            'available': is_available,
            'message': 'Available' if is_available else 'Not available'
        })
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)


# Vehicle Views
class VehicleListView(LoginRequiredMixin, ListView):
    model = Vehicle
    template_name = 'tms/vehicles/list.html'
    context_object_name = 'vehicles'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset()
        vehicle_type = self.request.GET.get('type')
        
        if vehicle_type and vehicle_type in Vehicle.get_vehicle_types():
            queryset = queryset.filter(vehicle_type=vehicle_type)
        
        return queryset.order_by('make', 'model')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle_types'] = Vehicle.VEHICLE_TYPES
        return context

class VehicleDetailView(LoginRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'tms/vehicles/detail.html'
    context_object_name = 'vehicle'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upcoming_bookings'] = self.object.booking_set.filter(
            end_date__gte=timezone.now().date()
        ).order_by('start_date')[:5]
        return context

class VehicleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'tms/vehicles/form.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.user_type in ['OPERATOR', 'MINISTRY']
    
    def form_valid(self, form):
        messages.success(self.request, "Vehicle created successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('tms:vehicle-detail', kwargs={'pk': self.object.pk})

class VehicleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'tms/vehicles/form.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.user_type in ['OPERATOR', 'MINISTRY']
    
    def form_valid(self, form):
        messages.success(self.request, "Vehicle updated successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('tms:vehicle-detail', kwargs={'pk': self.object.pk})

class VehicleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Vehicle
    template_name = 'tms/vehicles/confirm_delete.html'
    success_url = reverse_lazy('tms:vehicle-list')
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.user_type in ['OPERATOR', 'MINISTRY']
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Vehicle deleted successfully!")
        return super().delete(request, *args, **kwargs)

class VehicleAvailabilityView(LoginRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'tms/vehicles/availability.html'
    context_object_name = 'vehicle'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upcoming_bookings'] = self.object.booking_set.filter(
            end_date__gte=timezone.now().date()
        ).order_by('start_date')
        return context

# Accommodation Views
class AccommodationListView(ListView):
    model = Accommodation
    template_name = 'tms/accommodations/list.html'
    context_object_name = 'accommodations'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('destination').prefetch_related('images')
        
        destination_id = self.request.GET.get('destination')
        if destination_id:
            queryset = queryset.filter(destination_id=destination_id)
        
        accommodation_type = self.request.GET.get('type')
        if accommodation_type:
            queryset = queryset.filter(accommodation_type=accommodation_type)
        
        min_stars = self.request.GET.get('min_stars')
        if min_stars:
            queryset = queryset.filter(star_rating__gte=min_stars)
        
        return queryset.order_by('-star_rating', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accommodation_types'] = dict(Accommodation.ACCOMMODATION_TYPES)
        return context

class AccommodationDetailView(DetailView):
    model = Accommodation
    template_name = 'tms/accommodations/detail.html'
    context_object_name = 'accommodation'
    
    def get_queryset(self):
        return super().get_queryset().select_related('destination').prefetch_related('images')

class AccommodationCreateView(CreateView):
    model = Accommodation
    form_class = AccommodationForm
    template_name = 'tms/accommodations/form.html'

    def form_valid(self, form):
        # Debug: Print form data before saving
        print("Form data:", form.cleaned_data)
        
        # Save the form
        self.object = form.save()
        
        # Debug: Print saved object
        print("Saved object:", self.object)
        
        messages.success(self.request, _("Accommodation created successfully!"))
        return super().form_valid(form)

    def form_invalid(self, form):
        # Debug: Print form errors
        print("Form errors:", form.errors)
        messages.error(self.request, _("Please correct the errors below."))
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('tms:accommodation-detail', kwargs={'pk': self.object.pk})

class AccommodationUpdateView(UpdateView):
    model = Accommodation
    form_class = AccommodationForm
    template_name = 'tms/accommodations/form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Accommodation updated successfully!"))
        return response
    
    def get_success_url(self):
        return reverse('tms:accommodation-detail', kwargs={'pk': self.object.pk})

class AccommodationDeleteView(DeleteView):
    model = Accommodation
    template_name = 'tms/accommodations/confirm_delete.html'
    success_url = reverse_lazy('tms:accommodation-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Accommodation deleted successfully!"))
        return super().delete(request, *args, **kwargs)

class AccommodationAddImageView(View):
    def post(self, request, pk):
        accommodation = get_object_or_404(Accommodation, pk=pk)
        form = AccommodationImageForm(request.POST, request.FILES)
        
        if form.is_valid():
            image = form.save(commit=False)
            image.accommodation = accommodation
            image.save()
            
            # If this is the first image, make it featured
            if not accommodation.images.filter(is_featured=True).exists():
                image.is_featured = True
                image.save()
            
            messages.success(request, _("Image added successfully!"))
        else:
            messages.error(request, _("Error adding image."))
        
        return redirect('tms:accommodation-detail', pk=accommodation.pk)

class AccommodationAvailabilityView(DetailView):
    model = Accommodation
    template_name = 'tms/accommodations/availability.html'
    context_object_name = 'accommodation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            start_date_str = self.request.GET.get('start_date')
            end_date_str = self.request.GET.get('end_date')
            
            if not start_date_str or not end_date_str:
                return context
                
            # Parse dates with validation
            start_date = self._parse_date(start_date_str)
            end_date = self._parse_date(end_date_str)
            
            # Validate date range
            if start_date > end_date:
                raise ValidationError(_("End date must be after start date."))
            
            # Check availability
            availability_info = self._check_availability(start_date, end_date)
            context.update(availability_info)
            
        except ValidationError as e:
            messages.error(self.request, str(e))
        except Exception as e:
            messages.error(self.request, _("An error occurred while checking availability."))
            # Log the full error for debugging
            print(f"Availability check error: {str(e)}")
        
        return context
    
    def _parse_date(self, date_str):
        """Parse date string with proper validation"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError(_("Invalid date format. Please use YYYY-MM-DD."))
    
    def _check_availability(self, start_date, end_date):
        """Check for conflicting bookings"""
        conflicting_bookings = self.object.bookings.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
            status__in=['CONFIRMED', 'PENDING']
        ).select_related('customer')
        
        return {
            'availability_results': {
                'is_available': not conflicting_bookings.exists(),
                'conflicting_bookings': conflicting_bookings,
                'start_date': start_date,
                'end_date': end_date
            }
        }
    
class AccommodationSetFeaturedImageView(View):
    def get(self, request, accommodation_pk, image_pk):
        accommodation = get_object_or_404(Accommodation, pk=accommodation_pk)
        image = get_object_or_404(AccommodationImage, pk=image_pk, accommodation=accommodation)
        
        # Set all images to not featured first
        AccommodationImage.objects.filter(accommodation=accommodation).update(is_featured=False)
        
        # Set the selected image as featured
        image.is_featured = True
        image.save()
        
        messages.success(request, _("Featured image updated successfully!"))
        return redirect('tms:accommodation-detail', pk=accommodation.pk)

class AccommodationDeleteImageView(View):
    def get(self, request, accommodation_pk, image_pk):
        accommodation = get_object_or_404(Accommodation, pk=accommodation_pk)
        image = get_object_or_404(AccommodationImage, pk=image_pk, accommodation=accommodation)
        
        # If deleting the featured image, set another one as featured
        if image.is_featured:
            other_images = accommodation.images.exclude(pk=image.pk).first()
            if other_images:
                other_images.is_featured = True
                other_images.save()
        
        image.delete()
        messages.success(request, _("Image deleted successfully!"))
        return redirect('tms:accommodation-detail', pk=accommodation.pk)

class RoomTypeListView(ListView):
    model = RoomType
    template_name = 'tms/accommodations/room_types.html'  # This should match your template path
    context_object_name = 'room_types'
    
    def get_queryset(self):
        self.accommodation = get_object_or_404(Accommodation, pk=self.kwargs['pk'])
        return super().get_queryset().filter(accommodation=self.accommodation)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accommodation'] = self.accommodation
        context['available_room_types'] = self.get_queryset().filter(is_available=True)
        context['average_price'] = self.get_queryset().aggregate(
            avg_price=Avg('price_per_night')
        )['avg_price'] or 0
        return context

class RoomTypeCreateView(CreateView):
    model = RoomType
    form_class = RoomTypeForm
    template_name = 'tms/accommodations/roomtype_form.html'

    def get_initial(self):
        initial = super().get_initial()
        self.accommodation = get_object_or_404(Accommodation, pk=self.kwargs['pk'])
        initial['accommodation'] = self.accommodation
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accommodation'] = get_object_or_404(Accommodation, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        form.instance.accommodation = get_object_or_404(Accommodation, pk=self.kwargs['pk'])
        response = super().form_valid(form)
        messages.success(self.request, _("Room type created successfully!"))
        return response

    def get_success_url(self):
        return reverse('tms:accommodation-room-types', kwargs={'pk': self.kwargs['pk']})

class RoomTypeUpdateView(UpdateView):
    model = RoomType
    form_class = RoomTypeForm
    template_name = 'tms/accommodations/roomtype_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Room type updated successfully!"))
        return response
    
    def get_success_url(self):
        return reverse('tms:accommodation-room-types', kwargs={'pk': self.object.accommodation.pk})

class RoomTypeDeleteView(DeleteView):
    model = RoomType
    template_name = 'tms/accommodations/roomtype_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, _("Room type deleted successfully!"))
        return reverse('tms:accommodation-room-types', kwargs={'pk': self.object.accommodation.pk})

class AccommodationAutocompleteView(View):
    def get(self, request):
        query = request.GET.get('query', '')
        accommodations = Accommodation.objects.filter(
            name__icontains=query,
            is_active=True
        ).values('id', 'name')[:10]
        return JsonResponse(list(accommodations), safe=False)

# Booking Views
@method_decorator(login_required, name='dispatch')
class BookingListView(ListView):
    model = Booking
    template_name = 'tms/bookings/list.html'
    context_object_name = 'bookings'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-staff users, only show their own bookings
        if not self.request.user.is_staff:
            queryset = queryset.filter(customer=self.request.user)
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by upcoming/past bookings
        timeframe = self.request.GET.get('timeframe')
        if timeframe == 'upcoming':
            queryset = queryset.filter(start_date__gte=timezone.now().date())
        elif timeframe == 'past':
            queryset = queryset.filter(end_date__lt=timezone.now().date())
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_staff:
            context['total_revenue'] = Booking.objects.filter(
                status='CONFIRMED'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
        return context

@method_decorator(login_required, name='dispatch')
class BookingDetailView(DetailView):
    model = Booking
    template_name = 'tms/bookings/detail.html'
    context_object_name = 'booking'
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return self.get_object().customer == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all()
        context['remaining_balance'] = self.object.total_amount - self.object.amount_paid
        return context

@method_decorator(login_required, name='dispatch')
class BookingCreateView(CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'tms/bookings/form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.customer = self.request.user
        form.instance.total_amount = form.instance.calculate_total()
        
        response = super().form_valid(form)
        
        # Generate QR code
        generate_qr_code(self.object)
        
        # Send notifications
        send_booking_notification(self.object)
        
        messages.success(self.request, _("Booking created successfully!"))
        return response
    
    def get_success_url(self):
        return reverse('tms:booking-detail', kwargs={'pk': self.object.pk})

@method_decorator(login_required, name='dispatch')
class BookingUpdateView(UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = 'tms/bookings/form.html'
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return self.get_object().customer == self.request.user
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.total_amount = form.instance.calculate_total()
        messages.success(self.request, _("Booking updated successfully!"))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('tms:booking-detail', kwargs={'pk': self.object.pk})

@method_decorator(login_required, name='dispatch')
class BookingDeleteView(DeleteView):
    model = Booking
    template_name = 'tms/bookings/confirm_delete.html'
    success_url = reverse_lazy('tms:booking-list')
    
    def test_func(self):
        if self.request.user.is_staff:
            return True
        return self.get_object().customer == self.request.user
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Booking cancelled successfully!"))
        return super().delete(request, *args, **kwargs)

@login_required
def process_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if user owns the booking or is staff
    if not request.user.is_staff and booking.customer != request.user:
        raise PermissionDenied
    
    remaining_balance = booking.total_amount - booking.amount_paid
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking
            
            # Validate payment amount doesn't exceed remaining balance
            if payment.amount > remaining_balance:
                form.add_error('amount', _("Payment amount exceeds remaining balance"))
                return render(request, 'tms/bookings/payment.html', {
                    'form': form,
                    'booking': booking,
                    'remaining_balance': remaining_balance
                })
            
            # Process payment
            payment.payment_status = 'COMPLETED'
            payment.save()
            
            # Update booking amount paid
            booking.amount_paid += payment.amount
            if booking.amount_paid >= booking.total_amount:
                booking.status = 'CONFIRMED'
            booking.save()
            
            # Send notification
            Notification.objects.create(
                user=booking.customer,
                notification_type='PAYMENT',
                title=_("Payment Received"),
                message=_("Your payment of %(amount)s for booking %(ref)s has been received.") % {
                    'amount': payment.amount,
                    'ref': booking.booking_reference
                },
                related_object_id=booking.id
            )
            
            messages.success(request, _("Payment processed successfully!"))
            return redirect('tms:booking-detail', pk=booking.id)
    else:
        # Pre-fill amount with remaining balance
        form = PaymentForm(initial={'amount': remaining_balance})
    
    return render(request, 'tms/bookings/payment.html', {
        'form': form,
        'booking': booking,
        'remaining_balance': remaining_balance
    })


class PaymentListView(ListView):
    model = Payment
    template_name = 'tms/payments/list.html'
    context_object_name = 'payments'

class PaymentDetailView(DetailView):
    model = Payment
    template_name = 'tms/payments/detail.html'
    context_object_name = 'payment'

# Helper functions
def generate_qr_code(booking):
    import qrcode
    from io import BytesIO
    from django.core.files import File
    from django.conf import settings
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    data = f"STMS Booking\nReference: {booking.booking_reference}\nCustomer: {booking.customer.get_full_name()}\n"
    if booking.tour_package:
        data += f"Package: {booking.tour_package.name}\n"
    data += f"Dates: {booking.start_date} to {booking.end_date}\n"
    data += f"Amount: ${booking.total_amount}"
    
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    file_name = f'qr_{booking.booking_reference}.png'
    booking.qr_code.save(file_name, File(buffer), save=True)
    
    return booking.qr_code.url

def send_booking_notification(booking):
    # Notification for customer
    Notification.objects.create(
        user=booking.customer,
        notification_type='BOOKING',
        title=_("Booking Confirmation"),
        message=_("Your booking #{ref} has been confirmed.").format(ref=booking.booking_reference),
        related_object_id=booking.id
    )
    
    # Notification for admin/staff (if applicable)
    if booking.tour_package and booking.tour_package.created_by:
        Notification.objects.create(
            user=booking.tour_package.created_by,
            notification_type='BOOKING',
            title=_("New Booking"),
            message=_("New booking #{ref} for package {package}").format(
                ref=booking.booking_reference,
                package=booking.tour_package.name
            ),
            related_object_id=booking.id
        )

def download_qr_code(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    if not booking.qr_code:
        raise Http404("QR code not generated for this booking")
    
    file_path = os.path.join(settings.MEDIA_ROOT, booking.qr_code.name)
    
    if not os.path.exists(file_path):
        raise Http404("QR code file not found")
    
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="booking-{booking.booking_reference}-qr.png"'
    return response

# Review Views
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, DetailView, UpdateView
from django.urls import reverse

from .models import Review, Booking
from .forms import ReviewForm


@method_decorator(login_required, name='dispatch')
class ReviewCreateView(CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'tms/reviews/form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=self.kwargs['booking_pk'])
        
        # Check if user owns the booking
        if not request.user.is_staff and self.booking.customer != request.user:
            raise PermissionDenied
        
        # Check if review already exists for this booking
        if hasattr(self.booking, 'review'):
            messages.warning(request, _("You have already reviewed this booking."))
            return redirect('booking-detail', pk=self.booking.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.booking
        return context
    
    def form_valid(self, form):
        form.instance.booking = self.booking
        form.instance.reviewer = self.request.user
        form.instance.is_approved = self.request.user.is_staff  # Auto-approve for staff
        
        # Update guide rating if this is a review for a guided tour
        if self.booking.guide:
            guide = self.booking.guide
            reviews = Review.objects.filter(booking__guide=guide, is_approved=True)
            avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            guide.rating = round(avg_rating, 1)
            guide.save()
        
        messages.success(self.request, _("Thank you for your review!"))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('booking-detail', kwargs={'pk': self.booking.pk})


class ReviewListView(ListView):
    model = Review
    template_name = 'tms/reviews/list.html'
    context_object_name = 'reviews'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_approved=True)
        
        # Staff can see their own pending reviews too
        if self.request.user.is_staff:
            queryset = Review.objects.filter(
                Q(is_approved=True) | Q(reviewer=self.request.user, is_approved=False))
        
        return queryset.select_related('booking', 'reviewer').order_by('-created_at')


@method_decorator(login_required, name='dispatch')
class ReviewDetailView(DetailView):
    model = Review
    template_name = 'tms/reviews/detail.html'
    context_object_name = 'review'
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Check permissions
        if not self.object.is_approved and self.object.reviewer != request.user and not request.user.is_staff:
            raise PermissionDenied(_("You don't have permission to view this review"))
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = (
            self.object.reviewer == self.request.user or 
            self.request.user.is_staff
        )
        return context


@method_decorator(login_required, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class ReviewManagementView(ListView):
    model = Review
    template_name = 'tms/reviews/management.html'
    context_object_name = 'reviews'
    paginate_by = 20
    
    def get_queryset(self):
        return Review.objects.all().select_related(
            'booking', 'reviewer'
        ).order_by('-created_at')


@login_required
@staff_member_required
def toggle_review_approval(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.is_approved = not review.is_approved
    review.save()
    
    # Update guide rating if this review affects a guide
    if review.booking.guide:
        guide = review.booking.guide
        reviews = Review.objects.filter(booking__guide=guide, is_approved=True)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        guide.rating = round(avg_rating, 1)
        guide.save()
    
    messages.success(request, 
        _("Review #{} has been {}").format(
            review.id,
            _("approved") if review.is_approved else _("unapproved")
        )
    )
    return redirect('review-management')


@method_decorator(login_required, name='dispatch')
class ReviewUpdateView(UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'tms/reviews/form.html'
    
    def dispatch(self, request, *args, **kwargs):
        review = self.get_object()
        if review.reviewer != request.user and not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Review updated successfully."))
        return response
    
    def get_success_url(self):
        return reverse('review-detail', kwargs={'pk': self.object.pk})


@method_decorator(login_required, name='dispatch')
class UserReviewListView(ListView):
    model = Review
    template_name = 'tms/reviews/user_reviews.html'
    context_object_name = 'reviews'
    paginate_by = 10
    
    def get_queryset(self):
        return Review.objects.filter(
            reviewer=self.request.user
        ).select_related('booking').order_by('-created_at')


# Promotion Views
class PromotionListView(ListView):
    model = Promotion
    template_name = 'tms/promotions/list.html'
    context_object_name = 'promotions'
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True, end_date__gte=timezone.now().date())
        
        # Filter by target audience if user is authenticated
        if self.request.user.is_authenticated:
            if self.request.user.user_type == 'DIASPORA':
                queryset = queryset.filter(Q(target_audience='DIASPORA') | Q(target_audience='ALL'))
            elif self.request.user.user_type == 'STUDENT':
                queryset = queryset.filter(Q(target_audience='STUDENTS') | Q(target_audience='ALL'))
            else:
                queryset = queryset.filter(target_audience='ALL')
        else:
            queryset = queryset.filter(target_audience='ALL')
        
        return queryset.order_by('-start_date')

# Emergency Contacts
class EmergencyContactListView(ListView):
    model = EmergencyContact
    template_name = 'tms/emergency/list.html'
    context_object_name = 'contacts'
    
    def get_queryset(self):
        return super().get_queryset().order_by('contact_type', 'name')

class EmergencyContactDetailView(DetailView):
    model = EmergencyContact
    template_name = 'tms/emergency/detail.html'
    context_object_name = 'contact'

class EmergencyContactCreateView(StaffRequiredMixin, CreateView):
    model = EmergencyContact
    form_class = EmergencyContactForm
    template_name = 'tms/emergency/form.html'
    success_url = reverse_lazy('tms:emergency-list')

    def form_valid(self, form):
        messages.success(self.request, "Emergency contact created successfully!")
        return super().form_valid(form)

class EmergencyContactUpdateView(StaffRequiredMixin, UpdateView):
    model = EmergencyContact
    form_class = EmergencyContactForm
    template_name = 'tms/emergency/form.html'
    success_url = reverse_lazy('tms:emergency-list')

    def form_valid(self, form):
        messages.success(self.request, "Emergency contact updated successfully!")
        return super().form_valid(form)

class EmergencyContactDeleteView(StaffRequiredMixin, DeleteView):
    model = EmergencyContact
    template_name = 'tms/emergency/confirm_delete.html'
    success_url = reverse_lazy('tms:emergency-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Emergency contact deleted successfully!")
        return super().delete(request, *args, **kwargs)

@login_required
def dashboard(request):
    user = request.user
    context = {'current_user': user}
    
    # Common data for all user types
    today = timezone.now().date()
    upcoming_week = today + datetime.timedelta(days=7)
    
    if user.user_type == 'ADMIN' or user.is_staff:
        # Admin Dashboard
        total_bookings = Booking.objects.count()
        confirmed_bookings = Booking.objects.filter(status='CONFIRMED').count()
        pending_bookings = Booking.objects.filter(status='PENDING').count()
        
        # Revenue calculations
        revenue_data = Booking.objects.filter(status='CONFIRMED').aggregate(
            total_revenue=Sum('total_amount'),
            monthly_revenue=Sum('total_amount', filter=Q(created_at__month=today.month)),
            weekly_revenue=Sum('total_amount', filter=Q(created_at__gte=upcoming_week))
        )
        
        # Guide approval stats
        pending_guides = CustomUser.objects.filter(
            user_type='GUIDE', 
            status='PENDING'
        ).count()
        
        # Package statistics
        popular_packages = TourPackage.objects.annotate(
            booking_count=Count('bookings')
        ).order_by('-booking_count')[:5]
        
        recent_bookings = Booking.objects.select_related(
            'customer', 'package'
        ).order_by('-created_at')[:10]
        
        context.update({
            'dashboard_type': 'admin',
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'pending_bookings': pending_bookings,
            'total_revenue': revenue_data['total_revenue'] or 0,
            'monthly_revenue': revenue_data['monthly_revenue'] or 0,
            'weekly_revenue': revenue_data['weekly_revenue'] or 0,
            'pending_guides': pending_guides,
            'popular_packages': popular_packages,
            'recent_bookings': recent_bookings,
        })

    elif user.user_type == 'TOURIST':
        # Tourist Dashboard
        user_bookings = Booking.objects.filter(
            customer=user
        ).select_related(
            'package', 'guide'
        ).order_by('-created_at')[:5]
        
        upcoming_trips = Booking.objects.filter(
            customer=user,
            start_date__gte=today,
            status='CONFIRMED'
        ).select_related('package')[:5]
        
        # Recommended packages (based on user's previous bookings)
        booked_categories = user.bookings.values_list(
            'package__categories', flat=True
        ).distinct()
        
        recommended_packages = TourPackage.objects.filter(
            categories__in=booked_categories
        ).exclude(
            bookings__customer=user
        ).annotate(
            rating=Avg('reviews__rating')
        ).order_by('-rating')[:3]
        
        context.update({
            'dashboard_type': 'tourist',
            'user_bookings': user_bookings,
            'upcoming_trips': upcoming_trips,
            'recommended_packages': recommended_packages,
        })

    elif user.user_type == 'GUIDE':
        # Guide Dashboard
        if not hasattr(user, 'guide_profile'):
            raise PermissionDenied("Guide profile not found")
        
        if user.status != 'APPROVED':
            return render(request, 'accounts/guide/pending_approval.html')
        
        guide = user.guide_profile
        upcoming_tours = Booking.objects.filter(
            guide=user,
            status='CONFIRMED',
            start_date__gte=today
        ).select_related(
            'customer', 'package'
        ).order_by('start_date')[:5]
        
        # Today's schedule
        todays_tours = Booking.objects.filter(
            guide=user,
            status='CONFIRMED',
            start_date=today
        ).select_related('customer', 'package')
        
        # Stats
        guide_stats = {
            'completed_tours': Booking.objects.filter(
                guide=user,
                status='COMPLETED'
            ).count(),
            'upcoming_tours_count': Booking.objects.filter(
                guide=user,
                status='CONFIRMED',
                start_date__gte=today
            ).count(),
            'average_rating': user.guide_reviews.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
        }
        
        # Recent reviews
        recent_reviews = user.guide_reviews.select_related(
            'booking__customer'
        ).order_by('-created_at')[:3]
        
        context.update({
            'dashboard_type': 'guide',
            'upcoming_tours': upcoming_tours,
            'todays_tours': todays_tours,
            'guide_stats': guide_stats,
            'recent_reviews': recent_reviews,
            'guide': guide,
        })

    else:
        # Unknown user type
        return redirect('contact')
    
    return render(request, f'accounts/dashboards/{context["dashboard_type"]}_dashboard.html', context)
    
@login_required
def tourist_home(request):
    if request.user.user_type != 'TOURIST':
        raise PermissionDenied("This page is for tourists only")
    
    today = timezone.now().date()
    upcoming_week = today + datetime.timedelta(days=7)
    
    # Upcoming bookings
    upcoming_trips = Booking.objects.filter(
        customer=request.user,
        start_date__gte=today,
        status='CONFIRMED'
    ).select_related('package', 'guide')[:5]
    
    # Recent bookings
    recent_bookings = Booking.objects.filter(
        customer=request.user
    ).select_related('package').order_by('-created_at')[:5]
    
    # Recommended packages (based on categories from previous bookings)
    booked_categories = request.user.bookings.values_list(
        'package__categories', flat=True
    ).distinct()
    
    recommended_packages = TourPackage.objects.filter(
        categories__in=booked_categories
    ).exclude(
        bookings__customer=request.user
    ).annotate(
        avg_rating=Avg('reviews__rating')
    ).order_by('-avg_rating')[:3]
    
    context = {
        'upcoming_trips': upcoming_trips,
        'recent_bookings': recent_bookings,
        'recommended_packages': recommended_packages,
        'today': today,
    }
    return render(request, 'tms/tourist_home.html', context)

@login_required
def guide_dashboard(request):
    if not (request.user.user_type == 'GUIDE' and request.user.status == 'APPROVED'):
        raise PermissionDenied("Guide approval required")
    
    if not hasattr(request.user, 'guide_profile'):
        raise PermissionDenied("Guide profile not found")
    
    today = timezone.now().date()
    guide = request.user.guide_profile
    
    # Today's tours
    todays_tours = Booking.objects.filter(
        guide=request.user,
        status='CONFIRMED',
        start_date=today
    ).select_related('customer', 'package')
    
    # Upcoming tours
    upcoming_tours = Booking.objects.filter(
        guide=request.user,
        status='CONFIRMED',
        start_date__gte=today
    ).exclude(start_date=today).order_by('start_date')[:5]
    
    # Stats
    stats = {
        'completed_tours': Booking.objects.filter(
            guide=request.user,
            status='COMPLETED'
        ).count(),
        'upcoming_tours': Booking.objects.filter(
            guide=request.user,
            status='CONFIRMED',
            start_date__gte=today
        ).count(),
        'average_rating': Review.objects.filter(
            booking__guide=request.user
        ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
    }
    
    # Recent reviews
    recent_reviews = Review.objects.filter(
        booking__guide=request.user
    ).select_related('booking__customer').order_by('-created_at')[:3]
    
    context = {
        'guide': guide,
        'todays_tours': todays_tours,
        'upcoming_tours': upcoming_tours,
        'stats': stats,
        'recent_reviews': recent_reviews,
        'today': today,
    }
    return render(request, 'tms/guide_dashboard.html', context)

    # # Common context for all users
    # unread_notifications = Notification.objects.filter(
    #     user=user,
    #     is_read=False
    # ).order_by('-created_at')[:5]
    
    # promotions = Promotion.objects.filter(
    #     is_active=True,
    #     start_date__lte=timezone.now().date(),
    #     end_date__gte=timezone.now().date(),
    #     target_audience__in=[user.user_type, 'ALL']
    # )[:3]
    
    # context.update({
    #     'unread_notifications': unread_notifications,
    #     'promotions': promotions,
    # })
    
    # return render(request, 'tms/dashboard.html', context)

# API Views
def check_availability(request):
    from django.utils import timezone
    
    package_id = request.GET.get('package_id')
    vehicle_id = request.GET.get('vehicle_id')
    accommodation_id = request.GET.get('accommodation_id')
    date = request.GET.get('date', timezone.now().date())
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    results = {}
    
    try:
        if package_id:
            package = TourPackage.objects.get(id=package_id)
            results['package'] = {
                'available': package.is_active,
                'price': package.current_price(),
                'name': package.name
            }
        
        if vehicle_id:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            # Check if vehicle is booked on these dates
            is_booked = Booking.objects.filter(
                vehicle=vehicle,
                start_date__lte=end_date,
                end_date__gte=start_date,
                status__in=['CONFIRMED', 'PENDING']
            ).exists()
            results['vehicle'] = {
                'available': vehicle.is_available and not is_booked,
                'daily_rate': vehicle.daily_rate,
                'name': f"{vehicle.make} {vehicle.model}"
            }
        
        if accommodation_id:
            accommodation = Accommodation.objects.get(id=accommodation_id)
            # Check if accommodation is booked on these dates
            is_booked = Booking.objects.filter(
                accommodation=accommodation,
                start_date__lte=end_date,
                end_date__gte=start_date,
                status__in=['CONFIRMED', 'PENDING']
            ).exists()
            results['accommodation'] = {
                'available': not is_booked,
                'price_range': {
                    'min': accommodation.price_range_min,
                    'max': accommodation.price_range_max
                },
                'name': accommodation.name
            }
        
        return JsonResponse(results)
    
    except (TourPackage.DoesNotExist, Vehicle.DoesNotExist, Accommodation.DoesNotExist):
        return JsonResponse({'error': 'Resource not found'}, status=404)

# Search View
def search(request):
    query = request.GET.get('q', '')
    
    destinations = Destination.objects.filter(
        Q(name__icontains=query) | 
        Q(location__icontains=query) |
        Q(description__icontains=query)
    ).distinct()[:5]
    
    packages = TourPackage.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(destinations__name__icontains=query)
    ).distinct()[:5]
    
    accommodations = Accommodation.objects.filter(
        Q(name__icontains=query) |
        Q(destination__name__icontains=query)
    ).distinct()[:5]
    
    return render(request, 'tms/search_results.html', {
        'query': query,
        'destinations': destinations,
        'packages': packages,
        'accommodations': accommodations,
    })

# Notification Views
@login_required
@require_POST
def mark_notification_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'tms/notifications/list.html', {'notifications': notifications})

# Static Pages
class AboutView(TemplateView):
    template_name = 'tms/pages/about.html'

class ContactView(TemplateView):
    template_name = 'tms/pages/contact.html'

class FAQView(TemplateView):
    template_name = 'tms/pages/faq.html'