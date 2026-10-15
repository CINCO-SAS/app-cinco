"""
ViewSets del módulo Transporte.

Contrato ADMCINCO (D-A3): ViewSet → Service → Serializer.
Las vistas solo enrutan; toda regla de negocio vive en services/.
"""
from .conductor_view import ConductorViewSet
from .cierre_view import FechaLimiteCierreViewSet
from .jefe_view import JefeValidadorViewSet
from .kiosco_view import KioscoViewSet
from .liquidacion_view import LiquidacionViewSet
from .salida_view import SalidaViewSet
from .vehiculo_view import VehiculoViewSet

__all__ = [
    "ConductorViewSet",
    "FechaLimiteCierreViewSet",
    "JefeValidadorViewSet",
    "KioscoViewSet",
    "LiquidacionViewSet",
    "SalidaViewSet",
    "VehiculoViewSet",
]
