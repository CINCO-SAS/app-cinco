"""
ViewSets del módulo Transporte.

Contrato ADMCINCO (D-A3): ViewSet → Service → Serializer.
Las vistas solo enrutan; toda regla de negocio vive en services/.
"""
from .conductor_view import ConductorViewSet
from .cierre_view import FechaLimiteCierreViewSet
from .informe_view import InformeViewSet
from .jefe_view import JefeValidadorViewSet
from .kiosco_view import KioscoViewSet
from .liquidacion_view import LiquidacionViewSet
from .permiso_view import PermisoViewSet
from .planilla_view import PlanillaViewSet
from .reporte_fotografico_view import ReporteFotograficoViewSet
from .salida_view import SalidaViewSet
from .validacion_view import ValidacionViewSet
from .vehiculo_view import VehiculoViewSet
from .wfm_view import WfmViewSet

__all__ = [
    "ConductorViewSet",
    "FechaLimiteCierreViewSet",
    "InformeViewSet",
    "JefeValidadorViewSet",
    "KioscoViewSet",
    "LiquidacionViewSet",
    "PermisoViewSet",
    "PlanillaViewSet",
    "ReporteFotograficoViewSet",
    "SalidaViewSet",
    "ValidacionViewSet",
    "VehiculoViewSet",
    "WfmViewSet",
]
