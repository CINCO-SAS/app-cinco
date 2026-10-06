from django.db import models
from django.conf import settings


# 1. TABLA CABECERA CENTRAL DE ACTIVIDADES
class SmuActividad(models.Model):
    CATEGORIA_CHOICES = [
        ('preventivos', 'Preventivos'),
        ('correctivos', 'Correctivos'),
        ('emergencias', 'Emergencias'),
        ('correctivos_capex', 'Correctivos CAPEX'),
    ]

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviado', 'Enviado'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    # Enumeración de `tipo_formulario` (los 6 formularios del módulo).
    # Vive como constante de la clase —igual que CATEGORIA_CHOICES— y la
    # exige `SmuActividadSerializer.tipo_formulario` vía `ChoiceField`, para
    # no dejar una migración pendiente sin generar por agregar `choices=`
    # al campo (los choices no se guardan en la BD, pero Django sí los
    # registra en el estado de los modelos).
    TIPO_FORMULARIO_CHOICES = [
        ('aire_acondicionado', 'Aire acondicionado'),
        ('planta', 'Planta eléctrica'),
        ('estandar', 'Estándar'),
        ('tipologia1', 'Tipología 1'),
        ('tipologia3', 'Tipología 3'),
        ('tipologia5', 'Tipología 5'),
    ]

    id = models.BigAutoField(primary_key=True)
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    tipo_formulario = models.CharField(
        max_length=50,
        help_text='planta, aire_acondicionado, tipologia1, tipologia3, tipologia5, estandar'
    )
    codigo_ot = models.CharField(max_length=60, null=True, blank=True)
    actividad_operaciones = models.ForeignKey(
        'operaciones.Actividad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='smu_actividades',
        db_column='operacion_actividad_id',
        db_index=True,
        help_text='Vínculo con la orden de trabajo de operaciones central'
    )
    numero_inc = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        help_text='Numero de Incidente (Correctivos y Emergencias)'
    )
    numero_tas = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        help_text='Numero TAS'
    )
    estacion = models.ForeignKey(
        'SmuEstacion',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='actividades',
        db_column='estacion_id',
        db_index=True,
        help_text='Clave foránea con la tabla maestra de estaciones'
    )
    nombre_estacion = models.CharField(max_length=150, help_text='Snapshot histórico / nombre de estación')
    tipo_estacion = models.CharField(max_length=80, null=True, blank=True)
    tipo_sitio = models.CharField(max_length=80, null=True, blank=True)
    categoria_criticidad = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Criticidad del reporte (ej: 1. ALTA) - formulario estándar'
    )
    site_owner = models.CharField(max_length=100, null=True, blank=True)
    regional = models.CharField(max_length=80, null=True, blank=True)
    departamento = models.CharField(max_length=80, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='actividades_responsable_smu',
        db_column='responsable_usuario_id',
        db_index=True,
        help_text='Usuario central autenticado responsable del reporte'
    )
    responsable_cedula = models.CharField(
        max_length=30,
        help_text='Cedula del usuario que documenta en sistema'
    )
    responsable_nombre = models.CharField(max_length=150, null=True, blank=True)
    coordinador_aliado = models.CharField(max_length=150, null=True, blank=True)
    empresa = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text='Empresa aliada/contratista que ejecuta la actividad'
    )
    implica_exclusion = models.BooleanField(default=False)
    observaciones = models.TextField(null=True, blank=True)
    hallazgos = models.TextField(null=True, blank=True)
    recomendaciones = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smu_actividades'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['categoria', 'tipo_formulario'], name='idx_actividades_categoria_tipo'),
            models.Index(fields=['codigo_ot'], name='idx_actividades_ot'),
            models.Index(fields=['numero_inc'], name='idx_actividades_inc'),
            models.Index(fields=['nombre_estacion'], name='idx_actividades_estacion'),
            models.Index(fields=['responsable_cedula'], name='idx_actividades_cedula'),
            models.Index(fields=['fecha_inicio', 'fecha_fin'], name='idx_actividades_fechas'),
        ]

    def __str__(self):
        return f"SmuActividad #{self.id} - {self.nombre_estacion} ({self.categoria})"


# 2. TÉCNICOS EJECUTORES Y SOPORTES DE FINALIZACIÓN
class SmuActividadTecnico(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='tecnicos',
        db_column='actividad_id'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tecnico_actividades_smu',
        db_column='usuario_id',
        db_index=True,
        help_text='Usuario central del técnico'
    )
    cedula = models.CharField(max_length=30)
    nombre = models.CharField(max_length=150)
    es_principal = models.BooleanField(
        default=False,
        help_text='1 para el técnico principal, 0 para auxiliares/apoyos'
    )
    ruta_firma = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        help_text='Ruta de la imagen con la firma del técnico'
    )
    ruta_certificado = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        help_text='Ruta del documento/certificado (ej. CONTE, Alturas)'
    )
    ruta_foto = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        help_text='Ruta de la foto del técnico en sitio'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_actividad_tecnicos'
        ordering = ['id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_tecnicos_actividad'),
            models.Index(fields=['cedula'], name='idx_tecnicos_cedula'),
        ]

    def __str__(self):
        return f"Técnico {self.nombre} ({self.cedula}) - Actividad #{self.actividad_id}"


# 3. MATERIALES, INVENTARIOS Y MANO DE OBRA CONSUMIDA (LPU)
class SmuActividadMaterial(models.Model):
    TIPO_REGISTRO_CHOICES = [
        ('inventario_capex', 'Inventario CAPEX'),
        ('material_emergencia', 'Material Emergencia'),
        ('material_correctivo', 'Material Correctivo'),
        ('mano_obra_capex', 'Mano de Obra CAPEX'),
        ('inventario_preventivo', 'Inventario Preventivo'),
        ('mano_obra_preventivo', 'Mano de Obra Preventiva'),
    ]

    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='materiales',
        db_column='actividad_id'
    )
    material_lpu = models.ForeignKey(
        'SmuMatrizLpu',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usos_actividad',
        db_column='material_lpu_id',
        db_index=True,
        help_text='Vínculo con el catálogo oficial maestro LPU'
    )
    tipo_registro = models.CharField(max_length=50, choices=TIPO_REGISTRO_CHOICES)
    origen_material = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        help_text='Proveedor/origen del material (ej: CINCO SAS) - formulario estándar'
    )
    codigo_sap = models.CharField(max_length=50, null=True, blank=True)
    texto_sap = models.CharField(max_length=255, null=True, blank=True)
    alcance = models.TextField(null=True, blank=True)
    comentarios = models.TextField(
        null=True,
        blank=True,
        help_text='Comentarios de proceso del ítem (CAPEX insumos)'
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción de la actividad de mano de obra (CAPEX tipología 3 y 5)'
    )
    cantidad_estandar = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cantidad_real = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    unidad_medida = models.CharField(max_length=30, null=True, blank=True)
    comprado_operario = models.BooleanField(
        default=False,
        help_text='1 si fue comprado directamente en campo (fuera de catálogo)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_actividad_materiales'
        ordering = ['id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_materiales_actividad'),
            models.Index(fields=['codigo_sap'], name='idx_materiales_codigo_sap'),
        ]

    def __str__(self):
        return f"Material {self.codigo_sap or 'N/A'} ({self.tipo_registro}) - Actividad #{self.actividad_id}"



# 4. EVIDENCIAS FOTOGRÁFICAS Y DOCUMENTALES
class SmuActividadEvidencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='evidencias',
        db_column='actividad_id'
    )
    seccion = models.CharField(
        max_length=60,
        help_text='inventario, antes, durante, despues, transporte, spt, panoramica, refrigeracion, etc.'
    )
    campo_origen = models.CharField(
        max_length=80,
        help_text='Nombre del input file (ej: t1_fotos_antes, paa_foto_condensadora, cor_evidencia_1)'
    )
    material = models.ForeignKey(
        SmuActividadMaterial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidencias',
        db_column='material_id',
        help_text='Vinculo opcional si la foto corresponde a un insumo especifico'
    )
    ruta_archivo = models.CharField(max_length=350)
    nombre_original = models.CharField(max_length=255, null=True, blank=True)
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción o comentario que el usuario escribe sobre la foto'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_actividad_evidencias'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad', 'seccion'], name='idx_evidencias_act_seccion'),
            models.Index(fields=['campo_origen'], name='idx_evidencias_campo'),
        ]

    def __str__(self):
        return f"Evidencia {self.seccion}/{self.campo_origen} - Actividad #{self.actividad_id}"


# 5. REGISTRO DE TRANSPORTES Y TRASLADOS
class SmuActividadTransporte(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='transportes',
        db_column='actividad_id'
    )
    codigo_sap = models.CharField(max_length=50, null=True, blank=True)
    tipo_transporte = models.CharField(max_length=80, null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tiempo_traslado = models.CharField(max_length=50, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'smu_actividad_transportes'
        ordering = ['id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_transportes_actividad'),
        ]

    def __str__(self):
        return f"Transporte {self.tipo_transporte or 'N/A'} - Actividad #{self.actividad_id}"


# 5.1. FIRMAS DE CIERRE (entrega, aprobación, técnico y revisor)
class SmuActividadCierreFirma(models.Model):
    ROL_CHOICES = [
        ('tecnico', 'Técnico'),
        ('revisor', 'Revisor'),
        ('entrega', 'Responsable de entrega'),
        ('aprobador', 'Aprobador'),
    ]

    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='firmas_cierre',
        db_column='actividad_id'
    )
    rol = models.CharField(max_length=30, choices=ROL_CHOICES)
    nombre = models.CharField(max_length=150)
    cedula = models.CharField(max_length=30, null=True, blank=True)
    cargo = models.CharField(max_length=120, null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    ruta_firma = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        help_text='Ruta de la imagen de la firma'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_actividad_cierre_firmas'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_firmas_cierre_actividad'),
        ]

    def __str__(self):
        return f"Firma {self.get_rol_display()} - Actividad #{self.actividad_id}"


# 5.2. CERTIFICADOS Y SOPORTES TÉCNICOS (CONTE, Alturas, etc.)
class SmuActividadCertificado(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='certificados',
        db_column='actividad_id'
    )
    tipo = models.CharField(max_length=120, null=True, blank=True)
    categoria = models.CharField(max_length=120, null=True, blank=True)
    ruta_certificado = models.CharField(max_length=350, null=True, blank=True)
    ruta_foto_sitio = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        help_text='Foto del certificado en sitio'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_actividad_certificados'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_certificados_actividad'),
        ]

    def __str__(self):
        return f"Certificado {self.tipo or 'N/A'} - Actividad #{self.actividad_id}"


# 6. SUBTABLA: DETALLE PREVENTIVO AIRE ACONDICIONADO
class SmuDetallePreventivoAa(models.Model):
    actividad = models.OneToOneField(
        SmuActividad,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='detalle_preventivo_aa',
        db_column='actividad_id'
    )
    # Datos del Equipo
    marca = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    serial = models.CharField(max_length=100, null=True, blank=True)
    id_activo = models.CharField(max_length=80, null=True, blank=True)
    estado_equipo = models.CharField(max_length=50, null=True, blank=True)
    tipo_aire = models.CharField(max_length=80, null=True, blank=True)
    alimentacion_ac = models.CharField(max_length=50, null=True, blank=True)
    voltaje_entrada = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    corriente = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    capacidad_btu = models.PositiveIntegerField(default=0)
    gestion_remota_ip = models.CharField(max_length=60, null=True, blank=True)
    cantidad_compresores = models.PositiveSmallIntegerField(default=0)

    # Temperaturas y Termostato
    temp_cuarto = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    temp_entrada = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    temp_salida = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    temp_display = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    mp_termostato = models.CharField(max_length=100, null=True, blank=True)
    ajuste_termostato = models.CharField(max_length=100, null=True, blank=True)
    mp_termostato_post = models.CharField(max_length=100, null=True, blank=True)

    # Acciones y Mantenimiento Ejecutado
    # Cada respuesta SÍ/NO/N/A (y BUENO/REGULAR/MALO) vive en SmuPreventivoAaAccion
    # para poder repetir el bloque por cada unidad AA sin perder el tri-estado.
    acciones_observaciones = models.TextField(null=True, blank=True)
    plan_mejora = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'smu_detalle_preventivo_aa'

    def __str__(self):
        return f"Detalle Preventivo AA - Actividad #{self.actividad_id}"


# 7. CHECKLIST PREVENTIVO AIRE ACONDICIONADO (39 Puntos de Inspección)
class SmuDetallePreventivoAaChecklist(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='checklist_aa',
        db_column='actividad_id'
    )
    item_numero = models.PositiveSmallIntegerField(help_text='Del 1 al 39')
    estado = models.CharField(max_length=30, help_text='Bueno, Regular, Malo, NA, etc.')

    class Meta:
        db_table = 'smu_detalle_preventivo_aa_checklist'
        constraints = [
            models.UniqueConstraint(
                fields=['actividad', 'item_numero'],
                name='uk_aa_actividad_item'
            )
        ]

    def __str__(self):
        return f"Checklist AA #{self.item_numero}: {self.estado} - Actividad #{self.actividad_id}"


# 7.1. COMPRESORES POR UNIDAD DE AIRE ACONDICIONADO (N por actividad)
class SmuPreventivoAaCompresor(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='aa_compresores',
        db_column='actividad_id'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    marca = models.CharField(max_length=100, null=True, blank=True)
    serial = models.CharField(max_length=100, null=True, blank=True)
    tipo = models.CharField(max_length=80, null=True, blank=True)
    refrigerante = models.CharField(max_length=50, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    aislamiento_electrico = models.CharField(max_length=50, null=True, blank=True)
    presion_succion = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    presion_descarga = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    nivel_aceite = models.CharField(max_length=50, null=True, blank=True)
    vl1 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    vl2 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    vl3 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    amp_l1 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    amp_l2 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    amp_l3 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_preventivo_aa_compresores'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_aa_compresores_act'),
        ]

    def __str__(self):
        return f"Compresor {self.marca or 'N/A'} ({self.serial or 'S/N'}) - Actividad #{self.actividad_id}"


# 7.2. UNIDADES CONDENSADORAS (N por actividad)
class SmuPreventivoAaCondensadora(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='aa_condensadoras',
        db_column='actividad_id'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    marca = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    serial = models.CharField(max_length=100, null=True, blank=True)
    temperatura_entrada = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    temperatura_salida = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    diametro_eje = models.CharField(max_length=50, null=True, blank=True)
    diametro_aspas = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_preventivo_aa_condensadoras'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_aa_condensadoras_act'),
        ]

    def __str__(self):
        return f"Condensadora {self.marca or 'N/A'} ({self.serial or 'S/N'}) - Actividad #{self.actividad_id}"


# 7.3. UNIDADES MANEJADORAS (N por actividad)
class SmuPreventivoAaManejadora(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='aa_manejadoras',
        db_column='actividad_id'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    marca = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    tipo = models.CharField(max_length=80, null=True, blank=True)
    tipo_filtro = models.CharField(max_length=80, null=True, blank=True)
    tipo_correa = models.CharField(max_length=80, null=True, blank=True)
    marca_motor = models.CharField(max_length=100, null=True, blank=True)
    alimentacion_ac = models.CharField(max_length=50, null=True, blank=True)
    voltaje = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    corriente = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    aislamiento = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    serial_motor = models.CharField(max_length=100, null=True, blank=True)
    dimensiones_blower = models.CharField(max_length=80, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_preventivo_aa_manejadoras'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_aa_manejadoras_act'),
        ]

    def __str__(self):
        return f"Manejadora {self.marca or 'N/A'} ({self.serial_motor or 'S/N'}) - Actividad #{self.actividad_id}"


# 7.4. MANTENIMIENTO EJECUTADO: RESPUESTAS TRI-ESTADO (SÍ/NO/N-A, BUENO/REGULAR/MALO)
class SmuPreventivoAaAccion(models.Model):
    VALOR_CHOICES = [
        ('SI', 'SÍ'),
        ('NO', 'NO'),
        ('NA', 'N/A'),
        ('BUENO', 'Bueno'),
        ('REGULAR', 'Regular'),
        ('MALO', 'Malo'),
    ]

    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='aa_acciones',
        db_column='actividad_id'
    )
    clave = models.CharField(
        max_length=60,
        help_text='limpieza_serpentines, ajuste_elementos_control, adicion_refrigerante, '
                  'estado_drenajes, lubricacion_componentes, cambio_filtros_secado, '
                  'alineacion_poleas, cambio_componentes_electronicos, cambio_compresor, '
                  'cambio_correas_filtros, otras_reparaciones'
    )
    valor = models.CharField(max_length=20, choices=VALOR_CHOICES)
    orden = models.PositiveSmallIntegerField(
        default=1,
        help_text='Fila del formulario (1 por unidad AA registrada)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_preventivo_aa_acciones'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_aa_acciones_act'),
            models.Index(fields=['clave'], name='idx_aa_acciones_clave'),
        ]

    def __str__(self):
        return f"Acción {self.clave}={self.valor} (fila {self.orden}) - Actividad #{self.actividad_id}"


# Estados de las pruebas de planta (ficha oficial)
ESTADO_PRUEBA_CHOICES = [
    ('OK', 'OK'),
    ('NO OK', 'NO OK'),
    ('N/A', 'N/A'),
]

# Resultado del servicio de filtración
ESTADO_FILTRACION_CHOICES = [
    ('SÍ', 'SÍ'),
    ('NO', 'NO'),
    ('N/A', 'N/A'),
]


# 8. SUBTABLA: DETALLE PREVENTIVO PLANTA ELÉCTRICA / GRUPO ELECTRÓGENO
# (cabecera del formulario; los datos de cada planta viven en SmuPreventivoPlanta)
class SmuDetallePreventivoPlanta(models.Model):
    actividad = models.OneToOneField(
        SmuActividad,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='detalle_preventivo_planta',
        db_column='actividad_id'
    )
    jefatura = models.CharField(max_length=80, null=True, blank=True)
    zona_om = models.CharField(max_length=80, null=True, blank=True)
    modalidad = models.CharField(max_length=80, null=True, blank=True)
    cantidad_plantas = models.PositiveSmallIntegerField(default=1)

    # Datos generales del reporte
    estructura = models.CharField(max_length=120, null=True, blank=True)
    orden_trabajo_tas = models.CharField(max_length=60, null=True, blank=True)
    plan_mejora_estado = models.TextField(null=True, blank=True)
    fecha_elaboracion_informe = models.DateField(null=True, blank=True)

    # 4. Resultado de pruebas
    prueba_vacio = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_PRUEBA_CHOICES)
    prueba_con_carga = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_PRUEBA_CHOICES)
    prueba_transferencia_automatica = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_PRUEBA_CHOICES)
    prueba_planta_forzada = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_PRUEBA_CHOICES)
    observaciones_pruebas = models.TextField(null=True, blank=True)

    # 5. Servicio de filtración
    cambio_aceite = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    cambio_filtros_aire = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    cambio_filtros_combustible = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    cambio_filtros_aceite = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    cambio_mangueras_precalentador = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    cambio_refrigerante = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    cambio_baterias = models.CharField(max_length=20, null=True, blank=True, choices=ESTADO_FILTRACION_CHOICES)
    observaciones_filtracion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'smu_detalle_preventivo_planta'

    def __str__(self):
        return f"Detalle Preventivo Planta - Actividad #{self.actividad_id}"


# 8.1. PLANTAS ELÉCTRICAS REGISTRADAS (N por actividad, hasta 10 en el formulario)
class SmuPreventivoPlanta(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='plantas',
        db_column='actividad_id'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    nombre_unidad = models.CharField(max_length=120, null=True, blank=True)

    # Fila 1: Equipo
    equipo_marca = models.CharField(max_length=100, null=True, blank=True)
    equipo_modelo = models.CharField(max_length=100, null=True, blank=True)
    equipo_serial = models.CharField(max_length=100, null=True, blank=True)
    equipo_velocidad_motor = models.CharField(max_length=80, null=True, blank=True)
    equipo_admision_aire = models.CharField(max_length=80, null=True, blank=True)
    equipo_rpm = models.PositiveIntegerField(default=0)

    # Fila 2: Operación y Potencia
    equipo_horas_trabajo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    equipo_frecuencia_hz = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    equipo_capacidad_kva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    equipo_capacidad_kw = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    equipo_derrateo = models.CharField(max_length=80, null=True, blank=True)
    equipo_capacidad_derrateo = models.CharField(max_length=80, null=True, blank=True)

    # Fila 3: Motor
    motor_marca = models.CharField(max_length=100, null=True, blank=True)
    motor_modelo = models.CharField(max_length=100, null=True, blank=True)
    motor_serial = models.CharField(max_length=100, null=True, blank=True)
    motor_presion_aceite = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    motor_temp_aceite = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    motor_temp_refrigerante = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    # Fila 4: Generador
    generador_marca = models.CharField(max_length=100, null=True, blank=True)
    generador_modelo = models.CharField(max_length=100, null=True, blank=True)
    generador_serial = models.CharField(max_length=100, null=True, blank=True)
    generador_temp_ambiente = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    # Fila 5: Sistema de Baterías
    bateria_tipo = models.CharField(max_length=80, null=True, blank=True)
    bateria_estado = models.CharField(max_length=50, null=True, blank=True)
    bateria_estado_cargador = models.CharField(max_length=50, null=True, blank=True)
    bateria_voltaje = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    bateria_capacidad = models.CharField(max_length=50, null=True, blank=True)
    bateria_cantidad = models.PositiveSmallIntegerField(default=0)

    # Fila 6: Parámetros Eléctricos
    param_vac_l1_l2 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    param_vac_l1_l3 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    param_vac_l2_l3 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    param_amp_l1 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    param_amp_l2 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    param_amp_l3 = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    # Fila 7: Dimensionamiento / Cargabilidad
    dimensionamiento_capacidad_amp = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    dimensionamiento_carga_demanda = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    dimensionamiento_porc_carga = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_preventivo_plantas'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_plantas_actividad'),
        ]

    def __str__(self):
        return f"Planta {self.nombre_unidad or self.orden} - Actividad #{self.actividad_id}"


# 8.2. HALLAZGOS DEL PLAN DE MEJORA (sus evidencias se guardan en SmuActividadEvidencia)
class SmuPreventivoPlantaHallazgo(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='hallazgos_planta',
        db_column='actividad_id'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    descripcion = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_preventivo_planta_hallazgos'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_hallazgos_planta_act'),
        ]

    def __str__(self):
        return f"Hallazgo #{self.orden} - Actividad #{self.actividad_id}"


# 9. SISTEMAS Y DIAGNÓSTICO DE PLANTA (Checklist)
class SmuDetallePreventivoPlantaChecklist(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='checklist_planta',
        db_column='actividad_id'
    )
    sistema = models.CharField(
        max_length=50,
        help_text='combustible, lubricacion, aspiracion, refrigeracion, escape, electrico, transferencia'
    )
    componente = models.CharField(
        max_length=255,
        help_text='conexiones, abrazaderas, tanque, nivel_aceite, etc. '
                  '(se usa el texto completo de la ficha oficial)'
    )
    estado = models.CharField(max_length=50, null=True, blank=True)
    causa = models.TextField(null=True, blank=True)
    detectar = models.TextField(null=True, blank=True)
    corregir = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'smu_detalle_preventivo_planta_checklist'
        constraints = [
            models.UniqueConstraint(
                fields=['actividad', 'sistema', 'componente'],
                name='uk_planta_actividad_sistema_comp'
            )
        ]

    def __str__(self):
        return f"Checklist Planta {self.sistema}/{self.componente} - Actividad #{self.actividad_id}"


# 10. SUBTABLA: DETALLE DE FALLAS E INTERVENCIONES (Emergencias y Correctivos)
class SmuDetalleFallaIntervencion(models.Model):
    actividad = models.OneToOneField(
        SmuActividad,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='detalle_falla_intervencion',
        db_column='actividad_id'
    )
    tipo_actividad = models.CharField(max_length=100, null=True, blank=True)
    tipo_equipo_falla = models.CharField(max_length=100, null=True, blank=True)
    marca = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    afectacion_servicios = models.CharField(max_length=100, null=True, blank=True)
    tipo_intervencion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='reinstalacion, cambio, reparacion'
    )
    # El formulario estándar pregunta las 3 por separado (SÍ/NO/N/A), así que
    # cada una tiene su propia columna; tipo_intervencion queda como resumen.
    reinstalacion = models.CharField(max_length=20, null=True, blank=True)
    cambio = models.CharField(max_length=20, null=True, blank=True)
    reparacion = models.CharField(max_length=20, null=True, blank=True)
    descripcion_falla = models.TextField(null=True, blank=True)
    descripcion_solucion = models.TextField(null=True, blank=True)
    descripcion_fallas_componentes = models.TextField(null=True, blank=True)
    descripcion_generales = models.TextField(null=True, blank=True)
    detalles_plano = models.TextField(
        null=True,
        blank=True,
        help_text='Detalles del plano / croquis de la intervención - formulario estándar'
    )

    class Meta:
        db_table = 'smu_detalle_falla_intervencion'

    def __str__(self):
        return f"Detalle Falla/Intervención - Actividad #{self.actividad_id}"


# 11. SUBTABLA: DETALLE CAPEX (Tipologías 1, 3 y 5: SPT, Climatización, Subestaciones)
class SmuDetalleCapex(models.Model):
    TIPOLOGIA_CHOICES = [
        ('tipologia1', 'Tipología 1'),
        ('tipologia3', 'Tipología 3'),
        ('tipologia5', 'Tipología 5'),
    ]

    actividad = models.OneToOneField(
        SmuActividad,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='detalle_capex',
        db_column='actividad_id'
    )
    tipologia = models.CharField(max_length=50, choices=TIPOLOGIA_CHOICES)

    # Datos generales del reporte
    descripcion_general_actividades = models.TextField(null=True, blank=True)

    # Reforma SPT / Pararrayos (las medidas de la tabla Wenner están en
    # SmuDetalleCapexSptFila; ya no se guarda una sola resistividad)
    spt_naturaleza = models.CharField(max_length=150, null=True, blank=True)
    spt_recomendacion = models.TextField(null=True, blank=True)

    # Panorámica y recomendaciones aliadas
    panoramica_recomendacion = models.TextField(null=True, blank=True)

    # Actividades fuera del estándar (tipología 1)
    otras_actividades_1 = models.CharField(max_length=255, null=True, blank=True)
    otras_actividades_2 = models.CharField(max_length=255, null=True, blank=True)
    otras_actividades_3 = models.CharField(max_length=255, null=True, blank=True)
    texto_justificacion_otras_actividades = models.TextField(null=True, blank=True)

    # Soporte de matrícula profesional (la foto va en SmuActividadEvidencia)
    matricula_nombre = models.CharField(max_length=150, null=True, blank=True)
    matricula_numero = models.CharField(max_length=60, null=True, blank=True)
    matricula_fecha = models.DateField(null=True, blank=True)

    recomendaciones_aliado = models.TextField(null=True, blank=True)
    recomendacion_final = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'smu_detalle_capex'

    def __str__(self):
        return f"Detalle CAPEX ({self.tipologia}) - Actividad #{self.actividad_id}"


# 11.1. MEDIDAS DE RESISTIVIDAD SPT (tabla Wenner: hasta 5 filas por ficha)
class SmuDetalleCapexSptFila(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        SmuActividad,
        on_delete=models.CASCADE,
        related_name='spt_filas',
        db_column='actividad_id'
    )
    orden = models.PositiveSmallIntegerField(default=1)
    distancia = models.CharField(max_length=60, null=True, blank=True)
    medida_ohmio = models.CharField(max_length=60, null=True, blank=True)
    resistividad = models.CharField(max_length=60, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smu_detalle_capex_spt_filas'
        ordering = ['orden', 'id']
        indexes = [
            models.Index(fields=['actividad'], name='idx_spt_filas_actividad'),
        ]

    def __str__(self):
        return f"Fila SPT #{self.orden} ({self.resistividad or 'S/R'}) - Actividad #{self.actividad_id}"