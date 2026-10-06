"""
Subida de evidencias fotográficas del módulo SMU.

Equivalente Django de `capex_procesar_archivos()` / `saveFiles()` del PHP legado
(documentado en `estudio_captura_fotos_smu_2026-09-29.md`):

- valida el **contenido real** del archivo con Pillow (magic bytes), no la
  extensión ni el ``Content-Type`` que declara el navegador;
- tope de 5 MB y formatos JPG / PNG / WebP;
- nombre único con ``uuid4()`` (nunca el nombre original, como el ``uniqid()``
  del PHP);
- re-encripta **siempre** a WebP calidad 80 (el PHP hacía lo mismo con GD:
  ``saveFiles(..., $max_size_mb = 0)`` siempre pasaba por ``imagewebp``).

La ruta que se devuelve va **relativa a ``MEDIA_ROOT``**, igual que el PHP
guardaba rutas relativas a la raíz del proyecto. Se compone con
``MEDIA_URL`` para servir la foto desde el navegador.

Nota de implementación: toda lectura se hace sobre una **copia en memoria**
(``io.BytesIO``). El stream del upload se usa solo para ``read()`` y se rebobina
siempre, de modo que la validación se puede repetir (la llaman el serializer y
el servicio) sin que Pillow deje el archivo cerrado.
"""
import io
import os
import re
import uuid
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

# Espejo de `frontend/src/lib/fotos.ts` (FOTO_MAX_SIZE_MB / FOTO_TIPOS_PERMITIDOS)
FOTO_MAX_SIZE_MB = 5
FOTO_MAX_BYTES = FOTO_MAX_SIZE_MB * 1024 * 1024
# Formatos que PIL confirma leyendo los magic bytes (GIF/BMP/SVG quedan fuera)
FORMATOS_PIL_PERMITIDOS = {'JPEG', 'PNG', 'WEBP'}
# Content-Type declarado por el navegador (primera barrera, falsificable)
MIME_DECLARADOS_PERMITIDOS = {'image/jpeg', 'image/png', 'image/webp'}

# PHP: `$maxArchivos = 5` por campo (`capex_procesar_archivos`, línea 555).
TOPE_FOTOS_POR_CAMPO = 5

SUBDIR_MEDIA = Path('smu') / 'evidencias'
_EXTENSION_POR_FORMATO = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}


def _leer_upload(archivo):
    """Copia los bytes del upload y rebobina el stream original."""
    try:
        archivo.seek(0)
        contenido = archivo.read()
    except (OSError, ValueError):
        return b''
    finally:
        try:
            archivo.seek(0)
        except (OSError, ValueError):
            pass
    return contenido


def validar_archivo_foto(archivo):
    """Valida la foto y devuelve ``None`` si es válida o un mensaje de error.

    No confía en la extensión ni en ``content_type``: Pillow identifica el
    formato real leyendo los magic bytes (un SVG o un HTML renombrado a
    ``.jpg`` queda rechazado).
    """
    if archivo is None:
        return "Falta la foto."
    if not getattr(archivo, 'size', 0):
        return "El archivo de la foto está vacío."
    if archivo.size > FOTO_MAX_BYTES:
        return f"La foto supera el máximo de {FOTO_MAX_SIZE_MB} MB."

    content_type = (getattr(archivo, 'content_type', '') or '').lower()
    if content_type and content_type not in MIME_DECLARADOS_PERMITIDOS:
        return "Formato no permitido: use JPG, PNG o WebP."

    contenido = _leer_upload(archivo)
    if not contenido:
        return "El archivo de la foto está vacío."

    try:
        with Image.open(io.BytesIO(contenido)) as imagen:
            formato = (imagen.format or '').upper()
            imagen.verify()  # comprueba la integridad del codificador real
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return "El archivo no es una imagen válida (JPG, PNG o WebP)."

    if formato not in FORMATOS_PIL_PERMITIDOS:
        return f"Formato no permitido ({formato}): use JPG, PNG o WebP."
    return None


def _sanear_segmento(valor):
    """Segmento seguro de ruta: sin ``..``, ni barras, ni caracteres raros."""
    limpio = re.sub(r'[^A-Za-z0-9_-]+', '_', str(valor or '')).strip('_')
    return limpio.lower() or 'general'


def guardar_evidencia(archivo, seccion, campo_origen, actividad_id=None,
                      orden=None, descripcion=''):
    """Guarda la foto en ``MEDIA_ROOT`` y devuelve sus metadatos.

    Estructura de carpetas (espejo de ``archivos/{formulario}/`` del PHP)::

        media/smu/evidencias/{actividad_id | 'borrador'}/{seccion}/{uuid}.webp

    Si todavía no existe la actividad (la subida ocurre **al guardar** el
    formulario), la carpeta es ``borrador/``.
    """
    error = validar_archivo_foto(archivo)
    if error:
        raise ValueError(error)

    destino_relativo = SUBDIR_MEDIA / str(
        actividad_id if actividad_id is not None else 'borrador'
    ) / _sanear_segmento(seccion)
    destino = Path(settings.MEDIA_ROOT) / destino_relativo
    os.makedirs(destino, exist_ok=True)

    contenido = _leer_upload(archivo)
    imagen = Image.open(io.BytesIO(contenido))
    formato_original = (imagen.format or 'JPEG').upper()
    # Las fotos de celular traen EXIF de rotación: sin esto, al perder el EXIF
    # en la conversión a WebP las imágenes quedarían giradas.
    imagen = ImageOps.exif_transpose(imagen)
    # WebP admite RGB y RGBA; el resto de modos (paleta, escala de grises…)
    # se normaliza conservando la transparencia si la había.
    if imagen.mode not in ('RGB', 'RGBA'):
        con_alfa = 'A' in imagen.mode or 'transparency' in imagen.info
        imagen = imagen.convert('RGBA' if con_alfa else 'RGB')

    nombre_base = uuid.uuid4().hex
    try:
        nombre_archivo = f'{nombre_base}.webp'
        imagen.save(destino / nombre_archivo, 'WEBP', quality=80)
    except OSError:
        # Pillow sin soporte WebP: conserva el formato original, igual que el
        # PHP caía a `move_uploaded_file()` cuando GD fallaba.
        extension = _EXTENSION_POR_FORMATO.get(formato_original, '.jpg')
        nombre_archivo = f'{nombre_base}{extension}'
        imagen.convert('RGB').save(destino / nombre_archivo, formato_original)
    finally:
        imagen.close()

    ruta_relativa = (destino_relativo / nombre_archivo).as_posix()
    ruta_completa = Path(settings.MEDIA_ROOT) / ruta_relativa
    return {
        'ruta_archivo': ruta_relativa,
        'url': f'{settings.MEDIA_URL}{ruta_relativa}',
        'nombre': nombre_archivo,
        'bytes': os.path.getsize(ruta_completa),
    }
