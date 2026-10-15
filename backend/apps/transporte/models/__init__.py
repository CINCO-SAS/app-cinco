"""
Modelos del módulo Transporte (app-cinco).

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.
Decisiones clave:
- D-A5: todos los modelos extienden AuditoriaModel.
- D-A6: estados en mayúsculas (ver choices.py).
- D-A13: exclusión de motos (TipoVehiculo no incluye MOTO).
- Area/Festivo: pospuestos (vienen de otro archivo PHP); los campos que
  dependen de ellos quedan como CharField snapshot con TODO.
"""
from .base import AuditoriaModel
from .choices import (
    CategoriaLicencia,
    CiudadOperacion,
    EstadoSalida,
    TipoContrato,
    TipoDocumentoVehiculo,
    TipoMantenimiento,
    TipoNovedad,
    TipoPago,
    TipoVehiculo,
    TipoVinculacion,
)
from .vehiculo import (
    Conductor,
    DatosBancariosVehiculo,
    DocumentoVehiculo,
    Mantenimiento,
    Vehiculo,
)
from .salida import Novedad, Salida, SalidaHistorial
from .liquidacion import (
    ConsecutivoMensual,
    FechaLimiteCierre,
    JefeValidador,
    PagoVehiculoMensual,
    ValidacionSalida,
)
from .reporte_fotografico import ReporteFotograficoVehiculo, ReporteFotoImagen
from .auditoria import AuditoriaLog

__all__ = [
    "AuditoriaModel",
    "CategoriaLicencia",
    "CiudadOperacion",
    "EstadoSalida",
    "TipoContrato",
    "TipoDocumentoVehiculo",
    "TipoMantenimiento",
    "TipoNovedad",
    "TipoPago",
    "TipoVehiculo",
    "TipoVinculacion",
    "Conductor",
    "Vehiculo",
    "DocumentoVehiculo",
    "Mantenimiento",
    "DatosBancariosVehiculo",
    "Salida",
    "SalidaHistorial",
    "Novedad",
    "FechaLimiteCierre",
    "ConsecutivoMensual",
    "PagoVehiculoMensual",
    "JefeValidador",
    "ValidacionSalida",
    "ReporteFotograficoVehiculo",
    "ReporteFotoImagen",
    "AuditoriaLog",
]
