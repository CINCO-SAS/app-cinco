# from django.urls import path
# from apps.operaciones.views import ActividadesView

# urlpatterns = [
#     path("actividades/", ActividadesView.as_view(), name="actividades"),
# ]

from rest_framework.routers import DefaultRouter
from apps.operaciones.views import ActividadViewSet

router = DefaultRouter()
router.register(r'actividades', ActividadViewSet, basename='actividades')

urlpatterns = router.urls