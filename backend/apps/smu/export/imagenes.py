"""Inserción de fotografías dentro de celdas del Excel (media -> xlsx).

Las fotos se guardan en ``MEDIA_ROOT`` como WebP (ver ``guardar_evidencia``),
formato que Excel no admite dentro de un .xlsx, así que se re-codifican a JPEG
con Pillow antes de incrustarlas.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

from django.conf import settings
from openpyxl.drawing.image import Image as XlImage

logger = logging.getLogger(__name__)

# Caja máxima (en píxeles) que ocupa una foto dentro de un bloque de la plantilla.
ANCHO_MAX_PX = 260
ALTO_MAX_PX = 140


def ruta_absoluta(ruta_relativa: str | None):
    """`archivos/...` -> ``Path`` absoluto dentro de ``MEDIA_ROOT`` (o ``None``)."""
    if not ruta_relativa:
        return None
    limpia = ruta_relativa.replace("\\", "/").lstrip("/")
    # Nada de rutas absolutas ni saltos de directorio desde el cliente.
    if ".." in limpia.split("/"):
        return None
    return Path(settings.MEDIA_ROOT) / limpia


def insertar_foto_en_celda(
    ws,
    ruta_relativa: str | None,
    celda_destino: str,
    ancho_max: int = ANCHO_MAX_PX,
    alto_max: int = ALTO_MAX_PX,
) -> bool:
    """
    Incrusta la foto de ``MEDIA_ROOT`` en ``celda_destino`` (ancla de una
    celda fusionada). Devuelve ``False`` si el archivo no existe o no se pudo
    procesar: el exporte nunca debe fallar por una imagen faltante.
    """
    try:
        from PIL import Image as PilImage
    except ImportError:  # pragma: no cover - dependencia declarada en requirements
        logger.warning("Pillow no disponible: no se incrustan fotos en el Excel.")
        return False

    if not ruta_relativa:
        return False

    ruta = ruta_absoluta(ruta_relativa)
    if ruta is None or not ruta.is_file():
        logger.warning("Foto de evidencia no encontrada en disco: %s", ruta)
        return False

    try:
        with PilImage.open(ruta) as im:
            # Excel no soporta WebP: pasamos a RGB + JPEG.
            imagen = im.convert("RGB")
            ancho, alto = imagen.size
            escala = min(ancho_max / ancho, alto_max / alto, 1.0)
            if escala < 1.0:
                imagen = imagen.resize(
                    (max(1, int(ancho * escala)), max(1, int(alto * escala))),
                    PilImage.LANCZOS,
                )
            buffer = io.BytesIO()
            imagen.save(buffer, format="JPEG", quality=85, optimize=True)
            buffer.seek(0)

        img = XlImage(buffer)
        img.width, img.height = imagen.size
        ws.add_image(img, celda_destino)
        return True
    except Exception as exc:  # noqa: BLE001 - una foto rota no puede tumbar el exporte
        logger.warning("No se pudo incrustar la foto %s: %s", ruta, exc)
        return False
