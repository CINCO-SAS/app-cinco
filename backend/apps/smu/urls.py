from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.smu.views import (
    SmuActividadViewSet,
    SmuEvidenciaViewSet,
    SmuEstacionViewSet,
    SmuMatrizLpuViewSet,
)

router = DefaultRouter()
router.register(r'actividades', SmuActividadViewSet, basename='smu-actividades')
router.register(r'evidencias', SmuEvidenciaViewSet, basename='smu-evidencias')
router.register(r'estaciones', SmuEstacionViewSet, basename='smu-estaciones')
router.register(r'materiales-lpu', SmuMatrizLpuViewSet, basename='smu-materiales-lpu')

urlpatterns = [
    path('', include(router.urls)),
]

