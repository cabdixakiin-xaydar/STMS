from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView, ListView, UpdateView, DeleteView, DetailView
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)

from .forms import (
    TouristRegistrationForm, GuideRegistrationForm, LoginForm,
    GuideApprovalForm, ProfileUpdateForm, NotificationPreferencesForm,
    UserCreationFormWithPassword, UserEditForm, UserUpdateForm,
    CustomPasswordChangeForm
)
from .models import (
    CustomUser, UserProfile, NotificationPreferences,
    TouristProfile, GuideProfile
)

def redirect_after_login(user):
    if user.user_type == 'ADMIN' or user.is_staff:
        return redirect('tms:dashboard')
    elif user.user_type == 'GUIDE':
        if user.status == 'APPROVED':
            return redirect('tms:guide_dashboard')
        else:
            return redirect('accounts:pending_approval')
    elif user.user_type == 'TOURIST':
        return redirect('tms:tourist_home')
    return redirect('accounts:contact')

def user_login(request):
    if request.user.is_authenticated:
        return redirect_after_login(request.user)

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, _("You have been logged in successfully!"))
            return redirect_after_login(user)
        else:
            messages.error(request, _("Invalid username or password."))
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'title': _('Login')
    })

@login_required
def user_logout(request):
    if request.user.is_authenticated:
        request.user.last_logout = timezone.now()
        request.user.save(update_fields=['last_logout'])
    logout(request)
    messages.success(request, _("You have been logged out."))
    return redirect('accounts:login')

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.user_type == 'ADMIN')

class TouristRegisterView(CreateView):
    form_class = TouristRegistrationForm
    template_name = 'accounts/tourist_management/register_tourist.html'
    success_url = reverse_lazy('tms:tourist_home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, _("Tourist registration successful!"))
        return response

class GuideRegisterView(CreateView):
    form_class = GuideRegistrationForm
    template_name = 'accounts/guide/register_guide.html'
    success_url = reverse_lazy('accounts:pending_approval')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, _("Your guide application has been submitted for approval."))
        return response

@login_required
def pending_approval(request):
    if not request.user.user_type == 'GUIDE' or request.user.status == 'APPROVED':
        return redirect('tms:home')
    return render(request, 'accounts/pending_approval.html')

class GuideListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomUser
    template_name = 'accounts/guide_list.html'
    context_object_name = 'guides'
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_queryset(self):
        return CustomUser.objects.filter(
            user_type='GUIDE'
        ).select_related('guide_profile').order_by('status')

class GuideApprovalView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    form_class = GuideApprovalForm
    template_name = 'accounts/guide_approval.html'
    success_url = reverse_lazy('accounts:guide_list')
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 
            _("Guide %(username)s status updated to %(status)s") % {
                'username': self.object.username,
                'status': self.object.get_status_display()
            }
        )
        return response

@login_required
@user_passes_test(is_admin)
def approve_guide(request, pk):
    guide = get_object_or_404(CustomUser, pk=pk, user_type='GUIDE')
    guide.status = 'APPROVED'
    guide.save()
    messages.success(request, _("Guide %(username)s has been approved.") % {'username': guide.username})
    return redirect('accounts:guide_list')

@login_required
@user_passes_test(is_admin)
def reject_guide(request, pk):
    guide = get_object_or_404(CustomUser, pk=pk, user_type='GUIDE')
    guide.status = 'REJECTED'
    guide.save()
    messages.warning(request, _("Guide %(username)s has been rejected.") % {'username': guide.username})
    return redirect('accounts:guide_list')

# User Management Views
class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomUser
    template_name = 'accounts/user_management/user_list.html'
    context_object_name = 'users'

    def test_func(self):
        return is_admin(self.request.user)

class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CustomUser
    form_class = UserCreationFormWithPassword
    template_name = 'accounts/user_management/user_add.html'
    success_url = reverse_lazy('accounts:user-list')

    def test_func(self):
        return is_admin(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        UserProfile.objects.create(user=self.object)
        NotificationPreferences.objects.create(user=self.object)
        messages.success(self.request, _('User created successfully!'))
        return response

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    form_class = UserEditForm
    template_name = 'accounts/user_management/user_edit.html'
    context_object_name = 'target_user'

    def test_func(self):
        return is_admin(self.request.user)

    def get_success_url(self):
        messages.success(self.request, _('User updated successfully!'))
        return reverse_lazy('accounts:user-detail', kwargs={'pk': self.object.pk})

class UserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = CustomUser
    template_name = 'accounts/user_management/detail_user.html'
    context_object_name = 'target_user'

    def test_func(self):
        return is_admin(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = getattr(self.object, 'profile', None)
        context['notification_prefs'] = getattr(self.object, 'notification_preferences', None)
        return context

class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomUser
    template_name = 'accounts/user_management/delete_user.html'
    success_url = reverse_lazy('accounts:user-list')
    context_object_name = 'target_user'

    def test_func(self):
        return is_admin(self.request.user)

    def delete(self, request, *args, **kwargs):
        try:
            messages.success(request, _('User deleted successfully!'))
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, _('An error occurred while deleting the user.'))
            return redirect('accounts:user-detail', pk=self.get_object().pk)

# Profile Management Views
@login_required
def profile(request):
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("Your profile has been updated!"))
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'title': _('Profile Settings')
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.last_password_change = timezone.now()
            user.save(update_fields=['last_password_change'])
            login(request, user)
            messages.success(request, _("Your password has been changed successfully!"))
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {
        'form': form,
        'title': _('Change Password')
    })

@login_required
def notification_preferences(request):
    try:
        preferences = request.user.notification_preferences
    except NotificationPreferences.DoesNotExist:
        preferences = NotificationPreferences.objects.create(user=request.user)

    if request.method == 'POST':
        form = NotificationPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, _("Notification preferences updated!"))
            return redirect('accounts:notification-preferences')
    else:
        form = NotificationPreferencesForm(instance=preferences)

    user_activity = {
        'last_login': request.user.last_login,
        'last_logout': request.user.last_logout,
        'last_password_change': request.user.last_password_change,
        'date_joined': request.user.date_joined,
    }

    return render(request, 'accounts/notification_preferences.html', {
        'form': form,
        'title': _('Notification Preferences'),
        'user_activity': user_activity,
    })

@login_required
def complete_guide_profile(request):
    if request.user.user_type != 'GUIDE':
        return HttpResponseForbidden()

    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your guide profile has been completed!"))
            return redirect('tms:dashboard')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/complete_guide_profile.html', {
        'form': form,
        'title': _('Complete Guide Profile')
    })

@login_required
def delete_account(request):
    if request.method == 'POST':
        confirmation = request.POST.get('confirm', '').strip()
        if confirmation == 'DELETE':
            request.user.delete()
            messages.success(request, _("Your account has been deleted successfully."))
            return redirect('tms:home')
        else:
            messages.error(request, _("Confirmation text did not match. Account not deleted."))

    return render(request, 'accounts/delete_account.html', {
        'title': _('Delete Account')
    })

# Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    template_name = 'accounts/password_reset_form.html'
    success_url = reverse_lazy('accounts:password-reset-done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password-reset-complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'