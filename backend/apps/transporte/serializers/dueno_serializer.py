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

    celular = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={"blank": "El teléfono o celular es obligatorio."},
    )
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


class CuentaBancariaInputSerializer(serializers.Serializer):
    """Input de una cuenta bancaria del dueño.

    `id` es opcional: si viene, la cuenta se actualiza; si no, se crea.
    Hace falta un serializer aparte (y no el `ModelSerializer`) porque el
    `id` de un ModelSerializer es de solo lectura y se perdería en la
    validación, haciendo que cada guardado recrease las cuentas.
    """

    id = serializers.IntegerField(required=False)
    cedula_titular = serializers.CharField(max_length=20)
    nombre_titular = serializers.CharField(max_length=150)
    banco = serializers.CharField(max_length=80)
    tipo_cuenta = serializers.CharField(max_length=30)
    numero_cuenta = serializers.CharField(max_length=30)
    activo = serializers.BooleanField(required=False, default=True)


class GuardarBancariosSerializer(serializers.Serializer):
    """Input de `PUT /duenos/{id}/bancarios/`: lista completa de cuentas.

    El service hace la persistencia (upsert por id / baja de las que no
    vienen); el serializer solo valida la forma.
    """

    cuentas = CuentaBancariaInputSerializer(many=True)

    def validate_cuentas(self, cuentas):
        for i, cuenta in enumerate(cuentas):
            for campo in ("cedula_titular", "nombre_titular", "banco",
                          "tipo_cuenta", "numero_cuenta"):
                if not (cuenta.get(campo) or "").strip():
                    raise serializers.ValidationError(
                        f"Cuenta {i + 1}: `{campo}` es obligatorio."
                    )
        return cuentas
