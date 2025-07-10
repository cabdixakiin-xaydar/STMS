from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Registration
    path('register/tourist/', views.TouristRegisterView.as_view(), name='register-tourist'),
    path('register/guide/', views.GuideRegisterView.as_view(), name='register-guide'),
    
    # Guide Management
    path('guides/', views.GuideListView.as_view(), name='guide_list'),
    path('guides/<int:pk>/approve/', views.approve_guide, name='approve_guide'),
    path('guides/<int:pk>/reject/', views.reject_guide, name='reject_guide'),
    path('guides/<int:pk>/update/', views.GuideApprovalView.as_view(), name='update_guide_status'),
    path('pending-approval/', views.pending_approval, name='pending_approval'),
    
    # Profile Management
    path('profile/', views.profile, name='profile'),
    path('profile/complete-guide/', views.complete_guide_profile, name='complete-guide-profile'),
    path('profile/notifications/', views.notification_preferences, name='notification-preferences'),
    path('profile/change-password/', views.change_password, name='change-password'),
    path('profile/delete/', views.delete_account, name='delete-account'),
    
    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', 
         views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # User Management (Admin)
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/add/', views.UserCreateView.as_view(), name='user-add'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user-edit'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user-delete'),
    
    # Contact
    # path('contact/', views.contact_page, name='contact'),
]