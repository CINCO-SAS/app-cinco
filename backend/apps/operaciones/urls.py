from rest_framework.routers import DefaultRouter
from apps.operaciones.views import ActividadViewSet, AgendaViewSet

router = DefaultRouter()
router.register(r'actividades', ActividadViewSet, basename='actividades')
router.register(r'agenda', AgendaViewSet, basename='agenda')

urlpatterns = router.urls