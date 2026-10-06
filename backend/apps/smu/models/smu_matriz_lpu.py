from django.db import models


class SmuMatrizLpu(models.Model):
    """
    Catálogo oficial maestro de materiales y mano de obra (LPU) para SMU.
    Garantiza unicidad en código SAP, tipos de datos decimales estrictos
    para valores monetarios y soporte para el control y vigencia de precios.
    """
    id = models.BigAutoField(primary_key=True)
    codigo_sap = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text='Código SAP oficial único del material / ítem'
    )
    codigo_liquidacion = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        db_index=True,
        help_text='Código auxiliar para procesos de liquidación'
    )
    texto_sap = models.CharField(
        max_length=255,
        help_text='Descripción o texto oficial del ítem según SAP'
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Detalle o alcance extendido del ítem'
    )
    unidad_medida = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text='Unidad de medida (ej: UN, M, GL, HORA)'
    )
    
    # Precisión decimal estricta para valores monetarios
    valor_unitario = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        help_text='Precio o valor unitario vigente'
    )

    # Clasificación del catálogo
    tipo_registro = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Clasificación LPU (ej: inventario_capex, mano_obra, preventivo, etc.)'
    )

    # Control e historial de vigencia de precios
    fecha_vigencia_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha inicial de validez del precio/tarifa'
    )
    fecha_vigencia_fin = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha final de validez del precio/tarifa'
    )
    activo = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Indica si el ítem está activo en el catálogo vigente'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'smu_matriz_lpu'
        ordering = ['codigo_sap']
        indexes = [
            models.Index(fields=['codigo_liquidacion'], name='idx_smu_lpu_cod_liq'),
            models.Index(fields=['tipo_registro'], name='idx_smu_lpu_tipo_reg'),
            models.Index(fields=['activo'], name='idx_smu_lpu_activo'),
        ]

    def __str__(self):
        return f"{self.codigo_sap} - {self.texto_sap}"
