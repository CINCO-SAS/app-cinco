from rest_framework import serializers
from apps.smu.models import SmuActividad


class SmuActividadListSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para el listado paginado de actividades SMU.

    Solo expone los campos que muestra la tabla de historial; el detalle
    completo (técnicos, materiales, evidencias…) se obtiene con el
    SmuActividadSerializer estándar cuando se necesite el exportable.
    """

    categoria_display = serializers.CharField(
        source="get_categoria_display", read_only=True
    )
    tipo_formulario_display = serializers.SerializerMethodField()
    estado_display = serializers.CharField(
        source="get_estado_display", read_only=True
    )

    class Meta:
        model = SmuActividad
        fields = [
            "id",
            "categoria",
            "categoria_display",
            "tipo_formulario",
            "tipo_formulario_display",
            # Tipo de planta/estación (vacio en los formularios de planta,
            # que no lo piden en su cabecera).
            "tipo_estacion",
            "nombre_estacion",
            "codigo_ot",
            "responsable_cedula",
            "responsable_nombre",
            "estado",
            "estado_display",
            "fecha_inicio",
            "created_at",
        ]
        read_only_fields = fields

    # Mapa legible de los 6 tipos de formulario
    _TIPO_LABELS = dict(SmuActividad.TIPO_FORMULARIO_CHOICES)

    def get_tipo_formulario_display(self, obj: SmuActividad) -> str:
        return self._TIPO_LABELS.get(obj.tipo_formulario, obj.tipo_formulario)
