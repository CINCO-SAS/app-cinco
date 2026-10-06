import logging
from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Manejador global de excepciones para Django REST Framework.
    
    Asegura que cualquier excepción no controlada (incluyendo errores 500)
    devuelva siempre una respuesta en formato JSON estructurado y limpio,
    evitando que se exponga HTML de depuración técnica o datos sensibles al frontend.
    """
    response = exception_handler(exc, context)

    if response is not None:
        return response

    # Registrar el error completo en el log del servidor
    view_name = context.get('view').__class__.__name__ if context.get('view') else 'Desconocida'
    logger.exception("Error interno no controlado en API REST (Vista: %s): %s", view_name, exc)

    data = {
        "detail": "Ocurrió un error interno en el servidor. Por favor, intenta nuevamente más tarde.",
    }

    if settings.DEBUG:
        data["error"] = str(exc)
        data["exception_type"] = exc.__class__.__name__

    return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
