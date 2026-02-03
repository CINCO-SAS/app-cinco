from django.urls import path
from apps.operaciones.views import ActividadesView

urlpatterns = [
    path("actividades/", ActividadesView.as_view(), name="actividades"),
]
