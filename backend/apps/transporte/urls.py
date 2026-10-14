"""
URLs del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §6 (matriz
funcionalidad → endpoint). Registro por fases:
- F2: /conductores/ y /vehiculos/ (activos)
- A1 (Tramo A): /parametros/cierres/ (B2/D2) y /parametros/jefes/ (D1)
  — canónico según matriz D1/D2; B2 '/cierres/' queda absorbido aquí
- F3: /kiosco/, /salidas/
- F4: backoffice salidas (aprobar-lote, rechazar, novedades)
- F5: /liquidaciones/, /planillas/, /informes/
"""
from rest_framework.routers import DefaultRouter

from .views import (
    ConductorViewSet,
    FechaLimiteCierreViewSet,
    JefeValidadorViewSet,
    VehiculoViewSet,
)

router = DefaultRouter()
router.register(r"conductores", ConductorViewSet, basename="conductores")
router.register(r"vehiculos", VehiculoViewSet, basename="vehiculos")
router.register(
    r"parametros/cierres", FechaLimiteCierreViewSet, basename="cierres"
)
router.register(
    r"parametros/jefes", JefeValidadorViewSet, basename="jefes-validadores"
)

urlpatterns = router.urls
