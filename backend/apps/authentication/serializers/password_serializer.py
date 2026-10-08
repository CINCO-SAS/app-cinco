from rest_framework import serializers


class ChangePasswordRequestSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        required=True, write_only=True, max_length=128
    )
    new_password = serializers.CharField(
        required=True, write_only=True, min_length=8, max_length=128
    )
    confirm_new_password = serializers.CharField(
        required=True, write_only=True, max_length=128
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({
                "confirm_new_password": "Las contraseñas nuevas no coinciden."
            })
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({
                "new_password": "La nueva contraseña debe ser diferente a la contraseña actual."
            })
        return attrs
