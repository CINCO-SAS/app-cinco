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
    """
    Categoría de la licencia de conducción.

    El legacy tenía DOS columnas distintas con nombre parecido:
      · `transporte_base_conductores.licencia` → la categoría (el diccionario
        la documenta como B1/C1/C2/C3).
      · `transportadores_vehiculos.categoria` → la categoría, y el formulario
        legacy ofrecía A1..C3 (8 valores: A1, A2, B1, B2, B3, C1, C2, C3).

    Se modela el SUPERCONJUNTO (8) a propósito: con el catálogo de 4 valores,
    la ETL convertía a NULL las licencias A1/A2/B2/B3 del legacy, es decir
    perdía datos de conductores que sí existían. Ampliar el catálogo no
    rompe la ETL de la tabla de conductores (allí el valor esperado sigue
    siendo una categoría válida) y evita esa pérdida.
    """

    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    B3 = "B3", "B3"
    C1 = "C1", "C1"
    C2 = "C2", "C2"
    C3 = "C3", "C3"


class PoseeLicencia(models.TextChoices):
    """
    Legacy `transportadores_vehiculos.licencia`: SI / NO / NO APLICA.

    NO es el número de licencia: es la respuesta a "¿el conductor de este
    vehículo tiene licencia?". El número/clase de licencia vive en
    `Conductor.licencia_categoria` y el vencimiento en
    `Conductor.licencia_vencimiento`.
    """

    SI = "SI", "Sí"
    NO = "NO", "No"
    NO_APLICA = "NO APLICA", "No aplica"


class EstadoLicencia(models.TextChoices):
    """
    Legacy `transportadores_vehiculos.estado_licencia`: ACTIVA / INACTIVA.

    NO es el semáforo de vencimiento de la API (`estado_licencia` =
    VIGENTE/POR_VENCER/VENCIDA, que se CALCULA de la fecha real). Este es el
    flag que una persona escribía a mano, y por eso puede contradecir al
    semáforo: por eso vive en el campo `situacion_licencia`.
    """

    ACTIVA = "ACTIVA", "Activa"
    INACTIVA = "INACTIVA", "Inactiva"


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
