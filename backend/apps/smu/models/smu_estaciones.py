from django.db import models


class SmuEstacion(models.Model):
    """
    Tabla maestra que centraliza los sitios y estaciones de telecomunicaciones (SMU).
    Cumple con la Primera Forma Normal (1FN) separando atómicamente los atributos
    geográficos y técnicos, con restricción UNIQUE para el nombre del sitio.
    """
    id = models.BigAutoField(primary_key=True)
    nombre_sitio = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text='Nombre único oficial del sitio / estación'
    )

    # Atributos geográficos atómicos (1FN)
    regional = models.CharField(max_length=80, null=True, blank=True, db_index=True)
    departamento = models.CharField(max_length=80, null=True, blank=True, db_index=True)
    municipio = models.CharField(max_length=80, null=True, blank=True, db_index=True)
    zona = models.CharField(max_length=80, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Atributos técnicos y operativos
    tipo_estacion = models.CharField(max_length=80, null=True, blank=True)
    tipo_sitio = models.CharField(max_length=80, null=True, blank=True)
    site_owner = models.CharField(max_length=100, null=True, blank=True)
    categoria_criticidad = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Criticidad de la estación (ej: 1. ALTA, 2. MEDIA, 3. BAJA)'
    )

    activo = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Estado de disponibilidad operativa de la estación'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smu_estaciones'
        ordering = ['nombre_sitio']
        indexes = [
            models.Index(fields=['regional', 'departamento'], name='idx_smu_estaciones_reg_dep'),
            models.Index(fields=['tipo_estacion'], name='idx_smu_estaciones_tipo_est'),
            models.Index(fields=['activo'], name='idx_smu_estaciones_activo'),
        ]

    def __str__(self):
        return self.nombre_sitio
