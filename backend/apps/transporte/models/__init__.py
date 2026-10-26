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
from .auditoria import AuditoriaLog
from .base import AuditoriaModel
from .choices import (
    CategoriaLicencia,
    CiudadOperacion,
    EstadoLicencia,
    EstadoSalida,
    PoseeLicencia,
    TipoContrato,
    TipoDocumentoVehiculo,
    TipoMantenimiento,
    TipoNovedad,
    TipoPago,
    TipoVehiculo,
    TipoVinculacion,
)
from .dueno import DatosBancariosDueno, DuenoVehiculo
from .infraestructura_parametro import InfraestructuraParametro
from .liquidacion import (
    ConsecutivoMensual,
    FechaLimiteCierre,
    JefeValidador,
    PagoVehiculoMensual,
    ValidacionSalida,
)
from .reporte_fotografico import ReporteFotograficoVehiculo, ReporteFotoImagen
from .salida import Novedad, Salida, SalidaHistorial
from .vehiculo import (
    Conductor,
    DatosBancariosVehiculo,
    DocumentoVehiculo,
    Mantenimiento,
    Vehiculo,
)
from .wfm import AgendaLogistica, EstadoWfmJob, ResidencialWfm, WfmJob

__all__ = [
    "AgendaLogistica",
    "AuditoriaLog",
    "AuditoriaModel",
    "CategoriaLicencia",
    "CiudadOperacion",
    "Conductor",
    "ConsecutivoMensual",
    "DatosBancariosDueno",
    "DatosBancariosVehiculo",
    "DocumentoVehiculo",
    "DuenoVehiculo",
    "EstadoLicencia",
    "EstadoSalida",
    "EstadoWfmJob",
    "FechaLimiteCierre",
    "InfraestructuraParametro",
    "JefeValidador",
    "Mantenimiento",
    "Novedad",
    "PagoVehiculoMensual",
    "PoseeLicencia",
    "ReporteFotoImagen",
    "ReporteFotograficoVehiculo",
    "ResidencialWfm",
    "Salida",
    "SalidaHistorial",
    "TipoContrato",
    "TipoDocumentoVehiculo",
    "TipoMantenimiento",
    "TipoNovedad",
    "TipoPago",
    "TipoVehiculo",
    "TipoVinculacion",
    "ValidacionSalida",
    "Vehiculo",
    "WfmJob",
]
