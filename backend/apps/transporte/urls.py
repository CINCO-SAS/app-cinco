"""
URLs del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §6 (matriz
funcionalidad → endpoint). Registro por fases:
- F2: /conductores/ (activo) · /vehiculos/ (pendiente)
- F3: /kiosco/, /salidas/
- F4: backoffice salidas (aprobar-lote, rechazar, novedades)
- F5: /liquidaciones/, /cierres/, /planillas/, /informes/
"""
from rest_framework.routers import DefaultRouter

from .views import ConductorViewSet

router = DefaultRouter()
router.register(r"conductores", ConductorViewSet, basename="conductores")

urlpatterns = router.urls
