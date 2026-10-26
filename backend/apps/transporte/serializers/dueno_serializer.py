"""
Serializers del módulo «Dueños de vehículos» (2026-10-26).

Tabla (resumen con conteos), ficha completa (vehículos + cuentas) y los
inputs de asignar vehículo y de las cuentas bancarias del dueño.
"""
from rest_framework import serializers

from ..models import DatosBancariosDueno, DuenoVehiculo, Vehiculo


class DatosBancariosDuenoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatosBancariosDueno
        fields = (
            "id",
            "cedula_titular",
            "nombre_titular",
            "banco",
            "tipo_cuenta",
            "numero_cuenta",
            "activo",
        )


class VehiculoDelDuenoSerializer(serializers.ModelSerializer):
    """Resumen del vehículo dentro de la ficha del dueño."""

    class Meta:
        model = Vehiculo
        fields = (
            "id",
            "placa",
            "tipo_vehiculo",
            "marca",
            "referencia",
            "modelo_anio",
            "activo",
        )


class DuenoResumenSerializer(serializers.ModelSerializer):
    """Fila de la tabla de dueños (conteos anotados por el service)."""

    total_vehiculos = serializers.IntegerField(read_only=True)
    total_cuentas = serializers.IntegerField(read_only=True)

    class Meta:
        model = DuenoVehiculo
        fields = (
            "id",
            "cedula",
            "nombre",
            "celular",
            "activo",
            "total_vehiculos",
            "total_cuentas",
        )


class DuenoSerializer(serializers.ModelSerializer):
    """Ficha del dueño: datos de contacto + vehículos + cuentas bancarias."""

    vehiculos = VehiculoDelDuenoSerializer(many=True, read_only=True)
    datos_bancarios = DatosBancariosDuenoSerializer(many=True, read_only=True)

    class Meta:
        model = DuenoVehiculo
        fields = (
            "id",
            "cedula",
            "nombre",
            "celular",
            "activo",
            "vehiculos",
            "datos_bancarios",
        )


class AsignarVehiculoSerializer(serializers.Serializer):
    """Input de `POST /duenos/{id}/vehiculos/`: placa o vehiculo_id."""

    vehiculo_id = serializers.IntegerField(required=False)
    placa = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs.get("vehiculo_id") and not attrs.get("placa"):
            raise serializers.ValidationError("Indique `vehiculo_id` o `placa`.")
        return attrs


class GuardarBancariosSerializer(serializers.Serializer):
    """Input de `PUT /duenos/{id}/bancarios/`: lista completa de cuentas.

    El service hace la persistencia (upsert por id / baja de las que no
    vienen); el serializer solo valida la forma.
    """

    cuentas = DatosBancariosDuenoSerializer(many=True)

    def validate_cuentas(self, cuentas):
        for i, cuenta in enumerate(cuentas):
            for campo in ("cedula_titular", "nombre_titular", "banco",
                          "tipo_cuenta", "numero_cuenta"):
                if not (cuenta.get(campo) or "").strip():
                    raise serializers.ValidationError(
                        f"Cuenta {i + 1}: `{campo}` es obligatorio."
                    )
        return cuentas
