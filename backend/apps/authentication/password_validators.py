import re

from django.core.exceptions import ValidationError


class ComplexityPasswordValidator:
    """
    Exige complejidad mínima en la contraseña: mayúscula, minúscula, número
    y carácter especial.

    Se registra en `settings.AUTH_PASSWORD_VALIDATORS`, por lo que solo se
    ejecuta donde Django valida contraseñas (cambio de contraseña). El módulo
    frontend (`configuraciones`) replica estas reglas en su checklist para
    que el usuario vea lo mismo que exige el backend.
    """

    SPECIAL_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9]")

    def validate(self, password, user=None):
        requirements = (
            (re.search(r"[A-Z]", password), "una letra mayúscula", "password_no_uppercase"),
            (re.search(r"[a-z]", password), "una letra minúscula", "password_no_lowercase"),
            (re.search(r"[0-9]", password), "un número", "password_no_number"),
            (
                self.SPECIAL_CHAR_PATTERN.search(password),
                "un carácter especial (por ejemplo: !@#$%&*)",
                "password_no_special",
            ),
        )

        errors = [
            ValidationError(
                f"La contraseña debe contener al menos {label}.",
                code=code,
            )
            for satisfied, label, code in requirements
            if not satisfied
        ]

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Tu contraseña debe tener al menos 8 caracteres e incluir "
            "una mayúscula, una minúscula, un número y un carácter especial."
        )
