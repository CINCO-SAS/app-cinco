"""
Serializers de Flota (vehículos y documentos).

Contrato ADMCINCO (D-A3): validan forma; la regla vive en FlotaService.
"""
from rest_framework import serializers

from ..models import DocumentoVehiculo, Vehiculo
from ..services.vigencia import estado_vigencia


class VehiculoSerializer(serializers.ModelSerializer):
    """Contrato de lectura/escritura del catálogo de flota."""

    estado_soat = serializers.SerializerMethodField()
    estado_cda = serializers.SerializerMethodField()
    conductor_habitual_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Vehiculo
        fields = [
            "id",
            "placa",
            "tipo_vehiculo",
            "marca",
            "referencia",
            "modelo_anio",
            "color",
            "municipio_matricula",
            "numero_vin",
            "numero_motor",
            "tipo_combustible",
            "kilometraje",
            "cajon",
            "logos",
            "sistema_activo",
            "sistema_pasivo",
            "siniestros_viales",
            "tipo_contrato",
            "ciudad_operacion",
            "conductor_habitual",
            "conductor_habitual_detalle",
            "nombre_propietario",
            "cedula_propietario",
            "celular_propietario",
            "fecha_ingreso",
            "fecha_egreso",
            "fecha_soat",
            "fecha_cda",
            "valor_dia_base",
            "codigo_qr",
            "activo",
            "estado_soat",
            "estado_cda",
        ]
        read_only_fields = ["id", "codigo_qr"]

    def get_estado_soat(self, obj):
        return estado_vigencia(obj.fecha_soat)

    def get_estado_cda(self, obj):
        return estado_vigencia(obj.fecha_cda)

    def get_conductor_habitual_detalle(self, obj):
        conductor = obj.conductor_habitual
        if not conductor:
            return None
        return {
            "id": conductor.pk,
            "cedula": conductor.cedula,
            "nombre_completo": conductor.nombre_completo,
        }

    def validate_placa(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("La placa es obligatoria.")
        return value.strip().upper()

    def validate_modelo_anio(self, value):
        anio_min, anio_max = 1950, 2100
        if not anio_min <= value <= anio_max:
            raise serializers.ValidationError(
                f"El año del modelo debe estar entre {anio_min} y {anio_max}."
            )
        return value

    def validate(self, attrs):
        """Coherencia de fechas del vehículo (nombre de dominio, no de campo)."""
        ingreso = attrs.get("fecha_ingreso")
        egreso = attrs.get("fecha_egreso")
        if not self.partial:
            egreso = egreso or (self.instance.fecha_egreso if self.instance else None)
            ingreso = ingreso or (self.instance.fecha_ingreso if self.instance else None)
        if egreso and ingreso and egreso < ingreso:
            raise serializers.ValidationError(
                {"fecha_egreso": "No puede ser anterior a la fecha de ingreso."}
            )
        return attrs


class VehiculoListSerializer(serializers.ModelSerializer):
    """Vista compacta para listados (sin campos pesados)."""

    estado_soat = serializers.SerializerMethodField()
    estado_cda = serializers.SerializerMethodField()

    class Meta:
        model = Vehiculo
        fields = [
            "id",
            "placa",
            "marca",
            "referencia",
            "modelo_anio",
            "tipo_vehiculo",
            "tipo_contrato",
            "ciudad_operacion",
            "fecha_soat",
            "fecha_cda",
            "estado_soat",
            "estado_cda",
            "valor_dia_base",
            "codigo_qr",
            "activo",
        ]

    def get_estado_soat(self, obj):
        return estado_vigencia(obj.fecha_soat)

    def get_estado_cda(self, obj):
        return estado_vigencia(obj.fecha_cda)


class VehiculoCatalogoOperativoSerializer(serializers.ModelSerializer):
    """
    E1: catálogo operativo que reemplaza ``get_vehiculos_transp``.

    El semáforo SOAT/CDA se calcula aquí (en servidor) en vez de la
    aritmética de fechas del JS legacy, y el icono por tipo se resuelve
    con ``tipo_vehiculo`` (nombre real, no el ``tipo`` del PHP).
    """

    estado_soat = serializers.SerializerMethodField()
    estado_cda = serializers.SerializerMethodField()
    conductor_habitual_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Vehiculo
        fields = [
            "id",
            "placa",
            "tipo_vehiculo",
            "marca",
            "referencia",
            "modelo_anio",
            "municipio_matricula",
            "tipo_contrato",
            "ciudad_operacion",
            "fecha_soat",
            "fecha_cda",
            "estado_soat",
            "estado_cda",
            "valor_dia_base",
            "conductor_habitual",
            "conductor_habitual_detalle",
        ]

    def get_estado_soat(self, obj):
        return estado_vigencia(obj.fecha_soat)

    def get_estado_cda(self, obj):
        return estado_vigencia(obj.fecha_cda)

    def get_conductor_habitual_detalle(self, obj):
        conductor = obj.conductor_habitual
        if not conductor:
            return None
        return {
            "id": conductor.pk,
            "cedula": conductor.cedula,
            "nombre_completo": conductor.nombre_completo,
        }


class DocumentoVehiculoSerializer(serializers.ModelSerializer):
    """Alta/edición de documentos; el service valida tipo y tamaño."""

    class Meta:
        model = DocumentoVehiculo
        fields = ["id", "vehiculo", "tipo", "archivo", "fecha_vencimiento"]
