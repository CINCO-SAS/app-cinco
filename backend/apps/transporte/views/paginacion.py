"""
Paginación del módulo transporte.

El proyecto NO define `DEFAULT_PAGINATION_CLASS` global, así que los
ViewSet que paginan deben declararla **explícitamente**: sin ella
`self.paginator` es `None` y `get_paginated_response` revienta con
`AssertionError` → HTTP 500. Esto afectaba (latente, sin tests HTTP) a
`SalidaViewSet.list`/`export` (B1/B4) y ahora también a
`InformeViewSet.mensual` (F5-3).
"""
from rest_framework.pagination import PageNumberPagination


class PaginacionTransporte(PageNumberPagination):
    """
    Página numerada con tamaño amplio por defecto (informes y sábanas
    manejan muchas filas); el cliente puede ajustar con `?page_size=`.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000
