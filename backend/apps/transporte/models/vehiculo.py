"""
Modelos de Conductores y Flota Vehicular.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.B.
Legacy: transporte_base_conductores (~108 filas) y transportadores_vehiculos (~1.246 filas).
"""
from django.db import models

from .base import AuditoriaModel
from .choices import (
    CategoriaLicencia,
    CiudadOperacion,
    EstadoLicencia,
    PoseeLicencia,
    TipoContrato,
    TipoDocumentoVehiculo,
    TipoMantenimiento,
    TipoVehiculo,
    TipoVinculacion,
)


class Conductor(AuditoriaModel):
    """
    Transportista externo autónomo de la nómina (CR-6 / D-A2: separación
    Conductor externo vs Empleado de nómina).

    Legacy `transporte_base_conductores`: se ELIMINAN del modelo (verificado):
    placa (→ FK inverso desde Vehiculo), nombre/celular_propietario (→ Vehiculo),
    tipo_vehiculo (duplica vehiculo.tipo), edad (DERIVADA de fecha_nacimiento,
    nunca persistida — corrige H2), estado texto (→ activo bool),
    edit/fecha_edit (→ AuditoriaModel).
    """
    cedula = models.CharField(max_length=20, unique=True, db_index=True)
    nombre_completo = models.CharField(max_length=150)
    celular = models.CharField(max_length=30)
    direccion = models.CharField(max_length=150, null=True, blank=True)
    barrio = models.CharField(max_length=100, null=True, blank=True)
    licencia_categoria = models.CharField(
        max_length=10, choices=CategoriaLicencia.choices, null=True, blank=True
    )
    licencia_vencimiento = models.DateField(null=True, blank=True)
    # Legacy `transportadores_vehiculos.licencia` (SI/NO/NO APLICA) y
    # `estado_licencia` (ACTIVA/INACTIVA). El docstring de esta clase decía
    # que "pertenecen al conductor", pero NO se habían añadido: era un hueco
    # real de información. Viven en el Conductor (y no duplicados en el
    # Vehiculo) porque la licencia es del conductor; el vehículo lo referencia
    # por FK. La ETL los rellena desde la fila legacy del vehículo SOLO si el
    # conductor aún no los tiene (así el orden de carga no altera el dato).
    #
    # NOMBRES: el semáforo de vencimiento que ya expone la API se llama
    # `estado_licencia` (VIGENTE/POR_VENCER/VENCIDA) y NO se toca. El flag
    # manual del legacy se llama `situacion_licencia` para no chocar con él.
    # Son cosas distintas: el semáforo se CALCULA de la fecha real; este lo
    # escribía una persona a mano (y por eso puede contradecir al semáforo).
    posee_licencia = models.CharField(
        max_length=12, choices=PoseeLicencia.choices, null=True, blank=True
    )
    situacion_licencia = models.CharField(
        max_length=10, choices=EstadoLicencia.choices, null=True, blank=True
    )
    tipo_vinculacion = models.CharField(
        max_length=20, choices=TipoVinculacion.choices, default=TipoVinculacion.EXTERNO
    )
    fecha_ingreso = models.DateField()
    # Legacy '0000-00-00' → NULL en la ETL (§4).
    fecha_egreso = models.DateField(null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "transporte_conductor"
        verbose_name = "Conductor"
        verbose_name_plural = "Conductores"

    def __str__(self):
        return f"{self.cedula} — {self.nombre_completo}"


class Vehiculo(AuditoriaModel):
    """
    Flota vehicular. Legacy `transportadores_vehiculos` (55 columnas → modelo acotado).

    Se ELIMINAN (verificado): nombre_conductor/cedual_conductor (→FK),
    tipo_conductor (→Conductor), como_cond (ambigua, no utilizada),
    codigo_barras (obsoleto; codigo_qr se persiste en media/transporte/codigos-qr/),
    6 columnas de mantenimiento (→ Mantenimiento 1:N), edit/fecha_edit (→ AuditoriaModel),
    estado texto (→ activo bool).

    # RECUPERADAS (hueco real detectado al auditar `base_transportadores.php`):
    # `cilindraje` (vuelve al Vehiculo) y `licencia`/`fecha_licencia`/
    # `estado_licencia`/`categoria` (vuelven al Conductor, que es de quien son:
    # el docstring decía "pertenecen al conductor" pero nunca se habían añadido).
    """
    placa = models.CharField(max_length=10, unique=True, db_index=True)
    tipo_vehiculo = models.CharField(max_length=50, choices=TipoVehiculo.choices)
    marca = models.CharField(max_length=50)
    referencia = models.CharField(max_length=50, null=True, blank=True)
    modelo_anio = models.PositiveSmallIntegerField()  # era varchar(11)
    # Legacy `cilindraje` varchar(11), documentado como "numérico como texto"
    # (DICCIONARIO §transportadores_vehiculos #6). Se conserva como TEXTO:
    # el legacy lo guardaba con strtoupper() y sin normalizar, y hay valores
    # con decimales ("1.6") que un entero no representaría.
    cilindraje = models.CharField(max_length=11, null=True, blank=True)
    color = models.CharField(max_length=40, null=True, blank=True)
    municipio_matricula = models.CharField(max_length=60, null=True, blank=True)
    numero_vin = models.CharField(max_length=50, null=True, blank=True)
    numero_motor = models.CharField(max_length=50, null=True, blank=True)
    tipo_combustible = models.CharField(max_length=30, null=True, blank=True)
    kilometraje = models.IntegerField(null=True, blank=True)  # era texto
    cajon = models.BooleanField(default=False)  # era 'SI'/'NO'
    logos = models.BooleanField(default=False)
    sistema_activo = models.TextField(null=True, blank=True)
    sistema_pasivo = models.TextField(null=True, blank=True)
    siniestros_viales = models.IntegerField(default=0)
    tipo_contrato = models.CharField(max_length=20, choices=TipoContrato.choices)
    ciudad_operacion = models.CharField(
        max_length=30, null=True, blank=True, choices=CiudadOperacion.choices
    )
    conductor_habitual = models.ForeignKey(
        Conductor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehiculos",
    )
    # El dueño vive SOLO aquí (verificado: estaba duplicado en conductores).
    nombre_propietario = models.CharField(max_length=150)
    cedula_propietario = models.CharField(max_length=20)
    celular_propietario = models.CharField(max_length=30, null=True, blank=True)
    # Módulo «Dueños» (2026-10-26): el dueño es ahora entidad propia
    # (1 dueño → N vehículos). Los campos *_propietario de ARRIBA se
    # MANTIENEN como compatibilidad (ETL, informes y tests); este FK es la
    # fuente de verdad del nuevo módulo. SET_NULL: borrar un dueño nunca
    # destruye vehículos (el service además lo rechaza mientras tenga vehículos).
    dueno = models.ForeignKey(
        "DuenoVehiculo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehiculos",
    )
    fecha_ingreso = models.DateField(null=True, blank=True)
    fecha_egreso = models.DateField(null=True, blank=True)  # '0000-00-00' → NULL
    fecha_soat = models.DateField(null=True, blank=True)
    fecha_cda = models.DateField(null=True, blank=True)
    valor_dia_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    codigo_qr = models.FileField(
        # Ruta local definida por negocio: backend/media/transporte/codigos-qr/
        upload_to="transporte/codigos-qr/",
        max_length=255,
        null=True,
        blank=True,
        help_text="Ruta del archivo PNG del código QR generado.",
    )
    activo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "transporte_vehiculo"
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return f"{self.placa} — {self.marca} {self.referencia or ''}".strip()


class DocumentoVehiculo(AuditoriaModel):
    """
    Reemplaza img_soat/img_cda/img_matricula/img_carro (rutas en texto plano)
    por filas consultables. SOAT/CDA alimentan el semáforo de vigencia.
    """
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.CASCADE, related_name="documentos"
    )
    tipo = models.CharField(max_length=30, choices=TipoDocumentoVehiculo.choices)
    archivo = models.FileField(upload_to="transporte/vehiculos/%Y/")
    fecha_vencimiento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "transporte_documento_vehiculo"
        verbose_name = "Documento de vehículo"
        verbose_name_plural = "Documentos de vehículos"
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo", "tipo"], name="uq_doc_vehiculo_tipo"
            )
        ]


class Mantenimiento(AuditoriaModel):
    """
    Historial 1:N de mantenimientos. El legacy guardaba SOLO el último
    (6 columnas en la fila del vehículo); aquí no se pierde historial.
    """
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.CASCADE, related_name="mantenimientos"
    )
    fecha = models.DateField()
    tipo = models.CharField(max_length=20, choices=TipoMantenimiento.choices)
    actividad_realizada = models.CharField(max_length=150)
    responsable = models.CharField(max_length=150)
    observacion = models.TextField(blank=True)
    proximo_mantenimiento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "transporte_mantenimiento"
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"


class DatosBancariosVehiculo(AuditoriaModel):
    """
    Desempaquetado del JSON `datos.bancarios[]` del legacy (CR-13 / §7.2).
    """
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.CASCADE, related_name="datos_bancarios"
    )
    cedula_titular = models.CharField(max_length=20)
    nombre_titular = models.CharField(max_length=150)
    banco = models.CharField(max_length=80)
    tipo_cuenta = models.CharField(max_length=30)
    numero_cuenta = models.CharField(max_length=30)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "transporte_datos_bancarios_vehiculo"
        verbose_name = "Dato bancario de vehículo"
        verbose_name_plural = "Datos bancarios de vehículos"
