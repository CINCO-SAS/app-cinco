from unittest import TestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError
from apps.common.exceptions import custom_exception_handler


class CustomExceptionHandlerTests(TestCase):
    def test_maneja_excepcion_estandar_de_drf(self):
        exc = ValidationError({"campo": ["Este campo es obligatorio."]})
        context = {"view": None}
        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campo", response.data)

    def test_captura_excepcion_no_controlada_y_retorna_json_500(self):
        exc = ValueError("Error inesperado en lógica de negocio")
        context = {"view": None}
        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("detail", response.data)
        self.assertNotIn("<html", str(response.data))
        self.assertEqual(
            response.data["detail"],
            "Ocurrió un error interno en el servidor. Por favor, intenta nuevamente más tarde.",
        )
