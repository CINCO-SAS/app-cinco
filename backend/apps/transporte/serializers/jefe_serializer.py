"""
Serializer de jefes validadores (§5.8 / matriz D1).

Mapeo del JSON legacy programacion_parametros (data_jefes):
    cedula_jefe → empleado (FK, validado con queryset — sin JOIN)
    areas       → areas
    carpetas    → carpetas_por_area
    estado      → activo (ACTIVO ⇔ activo=True)

Contrato ADMCINCO (D-A3): valida forma (tipos); reglas de negocio
(subconjunto de carpetas, unicidad activa, existencia) en ParametrosService.
"""
from rest_framework import serializers

from apps.empleados.models import Empleado

from ..models import JefeValidador


class JefeValidadorSerializer(serializers.ModelSerializer):
    empleado = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all()
    )
    empleado_cedula = serializers.SerializerMethodField()
    empleado_nombre = serializers.SerializerMethodField()

    class Meta:
        model = JefeValidador
        fields = [
            "id",
            "empleado",
            "empleado_cedula",
            "empleado_nombre",
            "areas",
            "carpetas_por_area",
            "activo",
            "creado_en",
            "modificado_en",
        ]
        read_only_fields = ["id", "creado_en", "modificado_en"]

    def get_empleado_cedula(self, obj):
        # getattr con default tolera empleado_id huérfano (posible en ETL, C3).
        empleado = getattr(obj, "empleado", None)
        return empleado.cedula if empleado else None

    def get_empleado_nombre(self, obj):
        empleado = getattr(obj, "empleado", None)
        if empleado is None:
            return None
        return f"{empleado.nombre} {empleado.apellido}".strip()

    def validate_areas(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError(
                "Debe indicar al menos un área (lista no vacía)."
            )
        if any(not isinstance(area, str) or not area.strip() for area in value):
            raise serializers.ValidationError(
                "Cada área debe ser un texto no vacío."
            )
        return value

    def validate_carpetas_por_area(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Debe ser un objeto {área: [carpetas]}."
            )
        if any(not isinstance(v, list) for v in value.values()):
            raise serializers.ValidationError(
                "Cada área debe tener una lista de carpetas."
            )
        return value
