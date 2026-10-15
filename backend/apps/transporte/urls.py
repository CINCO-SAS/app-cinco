"""
URLs del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §6 (matriz
funcionalidad → endpoint). Registro por fases:
- F2: /conductores/ y /vehiculos/ (activos)
- A1 (Tramo A): /parametros/cierres/ (B2/D2) y /parametros/jefes/ (D1)
  — canónico según matriz D1/D2; B2 '/cierres/' queda absorbido aquí
- F3: /kiosco/, /salidas/ (B2: alta S6, consulta B1 y escaneo S1; las
  transiciones/novedades F4 son B4)
- F4: backoffice salidas (B4: aprobar-lote B12, rechazar B13, validar
  D-A11, eliminar B5, novedades B6/B7, historial) y /validaciones/
  (cierre mensual por área, legacy `get_valid_trans`)
- F5: /liquidaciones/, /planillas/, /informes/
  (A2: /liquidaciones/ con ?mes=&anio=, sábanas pago-mensual/pronto-pago,
  acciones /consecutivo/ y /pago/ — la ruta compuesta D3
  /liquidaciones/{anio}/{mes}/ queda como query param: DefaultRouter
  reserva /{pk}/)
"""
from rest_framework.routers import DefaultRouter

from .views import (
    ConductorViewSet,
    FechaLimiteCierreViewSet,
    InformeViewSet,
    JefeValidadorViewSet,
    KioscoViewSet,
    LiquidacionViewSet,
    ReporteFotograficoViewSet,
    SalidaViewSet,
    ValidacionViewSet,
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
router.register(
    r"liquidaciones", LiquidacionViewSet, basename="liquidaciones"
)
# F5: Tab 2 informes (I1) — F5-1 cuenta de cobro imprimible.
router.register(r"informes", InformeViewSet, basename="informes")
# F3/B2: alta + consulta (S6/B1); transiciones y novedades → F4 (B4).
router.register(r"salidas", SalidaViewSet, basename="salidas")
# F3/B2: S1 escaneo; S2–S4 llegan en entregas siguientes.
router.register(r"kiosco", KioscoViewSet, basename="kiosco")
# F3/B3: reporte fotográfico diario (guardar + pre-chequeo agenda + placa).
router.register(
    r"reportes-fotograficos", ReporteFotograficoViewSet, basename="reportes-fotograficos"
)

urlpatterns = router.urls
