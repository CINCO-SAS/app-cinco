from rest_framework import serializers
from apps.smu.models import SmuEstacion, SmuMatrizLpu


class SmuEstacionSerializer(serializers.ModelSerializer):
    """
    Serializer para la tabla maestra de estaciones / sitios SMU.
    Permite consulta, autocompletado y validación de atributos geográficos y técnicos en 1FN.
    """
    class Meta:
        model = SmuEstacion
        fields = [
            'id',
            'nombre_sitio',
            'regional',
            'departamento',
            'municipio',
            'zona',
            'direccion',
            'latitud',
            'longitud',
            'tipo_estacion',
            'tipo_sitio',
            'site_owner',
            'categoria_criticidad',
            'activo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SmuMatrizLpuSerializer(serializers.ModelSerializer):
    """
    Serializer para el catálogo oficial de materiales y mano de obra (LPU).
    Entrega códigos oficiales, descripción y tarifas decimales vigentes.
    """
    class Meta:
        model = SmuMatrizLpu
        fields = [
            'id',
            'codigo_sap',
            'codigo_liquidacion',
            'texto_sap',
            'descripcion',
            'unidad_medida',
            'valor_unitario',
            'tipo_registro',
            'fecha_vigencia_inicio',
            'fecha_vigencia_fin',
            'activo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
