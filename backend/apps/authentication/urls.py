from django.urls import path
from apps.authentication.views import LoginView, RefreshTokenView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
]
