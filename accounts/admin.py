# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import CustomUser, UserProfile, NotificationPreferences
# from .forms import CustomUserCreationForm, CustomUserChangeForm

# class CustomUserAdmin(UserAdmin):
#     add_form = CustomUserCreationForm
#     form = CustomUserChangeForm
#     model = CustomUser
    
#     list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active')
#     list_filter = ('user_type', 'is_staff', 'is_active')
#     fieldsets = (
#         (None, {'fields': ('username', 'password')}),
#         ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 
#                                    'profile_picture', 'date_of_birth', 'nationality')}),
#         ('Preferences', {'fields': ('preferred_language',)}),
#         ('Permissions', {'fields': ('user_type', 'is_verified', 'is_active', 
#                                  'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login', 'date_joined')}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('username', 'email', 'password1', 'password2', 
#                       'user_type', 'is_staff', 'is_active')}
#         ),
#     )
#     search_fields = ('username', 'email', 'first_name', 'last_name')
#     ordering = ('-date_joined',)

# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'emergency_contact', 'emergency_phone')
#     search_fields = ('user__username', 'user__email', 'emergency_contact')
#     raw_id_fields = ('user',)

# @admin.register(NotificationPreferences)
# class NotificationPreferencesAdmin(admin.ModelAdmin):
#     list_display = ('user', 'email_notifications', 'sms_notifications', 'push_notifications')
#     list_editable = ('email_notifications', 'sms_notifications', 'push_notifications')
#     search_fields = ('user__username', 'user__email')

# admin.site.register(CustomUser, CustomUserAdmin)