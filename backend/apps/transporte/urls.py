"""
URLs del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §6 (matriz
funcionalidad → endpoint). Los ViewSets se registrarán por fase:
- F2: /vehiculos/, /conductores/
- F3: /kiosco/, /salidas/
- F4: backoffice salidas (aprobar-lote, rechazar, novedades)
- F5: /liquidaciones/, /cierres/, /planillas/, /informes/
"""
from django.urls import path  # noqa: F401  # se usará al registrar ViewSets

urlpatterns = []
