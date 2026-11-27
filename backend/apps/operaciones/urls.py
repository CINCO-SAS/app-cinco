from rest_framework.routers import DefaultRouter
from apps.operaciones.views import ActividadViewSet, AgendaViewSet, IncidenteViewSet

router = DefaultRouter()
router.register(r'actividades', ActividadViewSet, basename='actividades')
router.register(r'agenda', AgendaViewSet, basename='agenda')
router.register(r'incidentes', IncidenteViewSet, basename='incidentes')

urlpatterns = router.urls