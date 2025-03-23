from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .views import (
    UserRegistrationView,
    SimpleUserRegistrationView,
    UserProfileView,
    ChangePasswordView,
    LogoutView,
    CustomTokenObtainPairView,
)

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('simple-register/', SimpleUserRegistrationView.as_view(), name='simple_register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Profile endpoints
    path('me/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
] 