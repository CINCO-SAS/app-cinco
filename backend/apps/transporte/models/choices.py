"""
Catálogos (choices) del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §2 (D-A6, D-A13).

D-A6: estados en MAYÚSCULAS. La ETL histórica normaliza el legacy que mezcla
caja ('reportado' vs 'APROBADO'); MySQL lo toleraba por collation, el ORM no.
"""
from django.db import models


class EstadoSalida(models.TextChoices):
    REPORTADO = "REPORTADO", "Reportado"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    ELIMINADO = "ELIMINADO", "Eliminado"
    VALIDADO = "VALIDADO", "Validado"


class TipoVehiculo(models.TextChoices):
    """D-A13: flota automotor 4+ ruedas. Exclusión dura de MOTO (CR-11)."""
    CAMIONETA = "CAMIONETA", "Camioneta"
    FURGON = "FURGON", "Furgón"
    VANS_CARGA = "VANS_CARGA", "Vans de carga"
    VANS_PASAJEROS = "VANS_PASAJEROS", "Vans de pasajeros"


class TipoContrato(models.TextChoices):
    """Reemplaza el campo legado 'contrato' SI/NO por la modalidad real."""
    PROPIO = "PROPIO", "Propio"
    EXTERNO = "EXTERNO", "Externo"
    RENTING = "RENTING", "Renting"


class CiudadOperacion(models.TextChoices):
    MEDELLIN = "MEDELLIN", "Medellín"
    MONTERIA = "MONTERIA", "Montería"
    SINCELEJO = "SINCELEJO", "Sincelejo"


class CategoriaLicencia(models.TextChoices):
    B1 = "B1", "B1"
    C1 = "C1", "C1"
    C2 = "C2", "C2"
    C3 = "C3", "C3"


class TipoVinculacion(models.TextChoices):
    """Normaliza caja del legacy ('externo'/'interno' minúsculas)."""
    EXTERNO = "EXTERNO", "Externo"
    INTERNO = "INTERNO", "Interno"


class TipoDocumentoVehiculo(models.TextChoices):
    """Reemplaza las 4 rutas en texto plano (img_soat/img_cda/img_matricula/img_carro)."""
    SOAT = "SOAT", "SOAT"
    CDA = "CDA", "CDA"
    MATRICULA = "MATRICULA", "Matrícula"
    FOTO_CARRO = "FOTO_CARRO", "Foto del vehículo"
    TARJETA_OPERACION = "TARJETA_OPERACION", "Tarjeta de operación"


class TipoMantenimiento(models.TextChoices):
    CORRECTIVO = "CORRECTIVO", "Correctivo"
    PREVENTIVO = "PREVENTIVO", "Preventivo"
    NO_APLICA = "NO_APLICA", "No aplica"


class TipoNovedad(models.TextChoices):
    ADICIONAL = "ADICIONAL", "Adicional"
    DESCUENTO = "DESCUENTO", "Descuento"


class TipoPago(models.TextChoices):
    MENSUAL = "MENSUAL", "Pago mensual"
    PRONTO_PAGO = "PRONTO_PAGO", "Pronto pago"
