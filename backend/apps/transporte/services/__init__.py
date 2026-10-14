"""
Capa de servicios del módulo Transporte.

Contrato arquitectónico ADMCINCO (D-A3): ViewSet → Service → Serializer.
Ningún ViewSet ni Serializer contiene lógica de negocio.
"""
from .conductor_service import ConductorService

__all__ = ["ConductorService"]
