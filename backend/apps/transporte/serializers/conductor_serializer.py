"""
Serializers del módulo Transporte.

Contrato ADMCINCO (D-A3): validan forma y exponen datos; la regla de
negocio vive en services/.
"""
from rest_framework import serializers

from ..models import Conductor
from ..services import ConductorService


class ConductorSerializer(serializers.ModelSerializer):
    """Contrato de lectura/escritura del catálogo de conductores."""

    # Derivados de solo lectura (nunca se persisten, §5.4).
    edad = serializers.SerializerMethodField()
    estado_licencia = serializers.SerializerMethodField()

    class Meta:
        model = Conductor
        fields = [
            "id",
            "cedula",
            "nombre_completo",
            "celular",
            "direccion",
            "barrio",
            "licencia_categoria",
            "licencia_vencimiento",
            "tipo_vinculacion",
            "fecha_ingreso",
            "fecha_egreso",
            "fecha_nacimiento",
            "activo",
            "edad",
            "estado_licencia",
        ]
        read_only_fields = ["id", "fecha_egreso"]

    def get_edad(self, obj):
        return ConductorService.calcular_edad(obj.fecha_nacimiento)

    def get_estado_licencia(self, obj):
        return ConductorService.estado_licencia(obj.licencia_vencimiento)

    def validate_cedula(self, value):
        if not value.strip():
            raise serializers.ValidationError("La cédula no puede estar vacía.")
        return value.strip()

    def validate_tipo_vinculacion(self, value):
        return value.upper()


class ConductorListSerializer(serializers.ModelSerializer):
    """
    Vista compacta para listados (sin campos derivados pesados).

    Incluye `estado_licencia` (barato: una resta de fechas) porque la tabla
    pinta el semáforo de licencia y la regla §5.3 vive EN EL SERVIDOR — mismo
    criterio que `VehiculoListSerializer` con SOAT/CDA. El `edad` completo
    solo en el detalle.
    """

    estado_licencia = serializers.SerializerMethodField()

    class Meta:
        model = Conductor
        fields = [
            "id",
            "cedula",
            "nombre_completo",
            "celular",
            "tipo_vinculacion",
            "licencia_categoria",
            "licencia_vencimiento",
            "estado_licencia",
            "activo",
        ]

    def get_estado_licencia(self, obj):
        return ConductorService.estado_licencia(obj.licencia_vencimiento)
