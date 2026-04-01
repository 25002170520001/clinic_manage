
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterPatientView,
    LoginView,
    LogoutView,
    ChangePasswordView,
    UserProfileView,
    PatientProfileView,
    current_user_view
)

urlpatterns = [
    # Authentication
    path('register/', RegisterPatientView.as_view(), name='register-patient'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password management
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Profile
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('patient-profile/', PatientProfileView.as_view(), name='patient-profile'),
    path('current-user/', current_user_view, name='current-user'),
]

