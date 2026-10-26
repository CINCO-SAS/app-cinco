"""
ViewSets del módulo Transporte.

Contrato ADMCINCO (D-A3): ViewSet → Service → Serializer.
Las vistas solo enrutan; toda regla de negocio vive en services/.
"""
from .cierre_view import FechaLimiteCierreViewSet
from .conductor_view import ConductorViewSet
from .dueno_view import DuenoViewSet
from .informe_view import InformeViewSet
from .jefe_view import JefeValidadorViewSet
from .kiosco_view import KioscoViewSet
from .liquidacion_view import LiquidacionViewSet
from .permiso_view import PermisoViewSet
from .persona_view import PersonaViewSet
from .planilla_view import PlanillaViewSet
from .reporte_fotografico_view import ReporteFotograficoViewSet
from .salida_view import SalidaViewSet
from .validacion_view import ValidacionViewSet
from .vehiculo_view import VehiculoViewSet
from .wfm_view import WfmViewSet

__all__ = [
    "ConductorViewSet",
    "DuenoViewSet",
    "FechaLimiteCierreViewSet",
    "InformeViewSet",
    "JefeValidadorViewSet",
    "KioscoViewSet",
    "LiquidacionViewSet",
    "PermisoViewSet",
    "PersonaViewSet",
    "PlanillaViewSet",
    "ReporteFotograficoViewSet",
    "SalidaViewSet",
    "ValidacionViewSet",
    "VehiculoViewSet",
    "WfmViewSet",
]
