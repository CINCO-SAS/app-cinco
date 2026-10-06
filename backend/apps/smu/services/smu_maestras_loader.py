import logging
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional
from django.db import transaction
from apps.smu.models import SmuEstacion, SmuMatrizLpu

logger = logging.getLogger(__name__)


def limpiar_texto(valor: Any) -> str:
    """Limpia y normaliza cadenas de texto para evitar duplicados por espacios."""
    if valor is None:
        return ""
    return str(valor).strip()


def limpiar_fecha(valor: Any) -> Optional[date]:
    """Convierte y valida fechas evitando cadenas vacías que fallen en DateField."""
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    if isinstance(valor, datetime):
        return valor.date()

    texto = str(valor).strip()
    if not texto:
        return None

    # Intentar formatos comunes YYYY-MM-DD o DD/MM/YYYY
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def convertir_decimal(
    valor: Any,
    default: Optional[Decimal] = Decimal('0.00'),
    decimales: Optional[int] = None
) -> Optional[Decimal]:
    """
    Convierte de forma segura y precisa cadenas numéricas a Decimal,
    soportando formato latino (1.250,50) y estándar (1,250.50).
    Permite preservar la precisión de coordenadas GPS cuando decimales=None.
    """
    if valor is None:
        return default
    if isinstance(valor, (Decimal, int, float)):
        try:
            dec = Decimal(str(valor))
            if decimales is not None:
                return dec.quantize(Decimal('1e-' + str(decimales)))
            return dec
        except (InvalidOperation, ValueError, TypeError):
            return default

    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if not texto:
        return default

    # Manejo robusto de separadores de miles y decimales
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            # Formato latino: 1.250,50 -> 1250.50
            texto = texto.replace(".", "").replace(",", ".")
        else:
            # Formato estándar: 1,250.50 -> 1250.50
            texto = texto.replace(",", "")
    elif "," in texto:
        # Solo comas: 1250,50 -> 1250.50
        texto = texto.replace(",", ".")

    try:
        dec = Decimal(texto)
        if decimales is not None:
            return dec.quantize(Decimal('1e-' + str(decimales)))
        return dec
    except (InvalidOperation, ValueError, TypeError):
        return default


class SmuMaestrasLoaderService:
    """
    Servicio para la validación, deduplicación, auditoría y carga
    de las tablas maestras de SMU (Estaciones y Matriz LPU).
    """

    @classmethod
    def procesar_estaciones(
        cls,
        registros: List[Dict[str, Any]],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Valida, normaliza en 1FN y deduplica la lista de sitios/estaciones.
        Si dry_run=True, solo audita y reporta inconsistencias sin escribir en BD.
        """
        sitios_vistos = set()
        estaciones_validas = []
        duplicados = []
        inconsistencias = []

        for idx, item in enumerate(registros, start=1):
            nombre_sitio = limpiar_texto(item.get('nombre_sitio') or item.get('nombre_estacion'))
            if not nombre_sitio:
                inconsistencias.append({
                    'fila': idx,
                    'error': 'Falta el nombre obligatorio del sitio/estación'
                })
                continue

            nombre_clave = nombre_sitio.upper()
            if nombre_clave in sitios_vistos:
                duplicados.append({
                    'fila': idx,
                    'nombre_sitio': nombre_sitio
                })
                continue

            sitios_vistos.add(nombre_clave)

            # Atributos atómicos 1FN (preservando hasta 7 decimales para GPS)
            datos_estacion = {
                'nombre_sitio': nombre_sitio,
                'regional': limpiar_texto(item.get('regional')) or None,
                'departamento': limpiar_texto(item.get('departamento')) or None,
                'municipio': limpiar_texto(item.get('municipio')) or None,
                'zona': limpiar_texto(item.get('zona')) or None,
                'direccion': limpiar_texto(item.get('direccion')) or None,
                'latitud': convertir_decimal(item.get('latitud'), default=None, decimales=7) if item.get('latitud') is not None else None,
                'longitud': convertir_decimal(item.get('longitud'), default=None, decimales=7) if item.get('longitud') is not None else None,
                'tipo_estacion': limpiar_texto(item.get('tipo_estacion')) or None,
                'tipo_sitio': limpiar_texto(item.get('tipo_sitio')) or None,
                'site_owner': limpiar_texto(item.get('site_owner')) or None,
                'categoria_criticidad': limpiar_texto(item.get('categoria_criticidad')) or None,
                'activo': bool(item.get('activo', True)),
            }
            estaciones_validas.append(datos_estacion)

        insertados = 0
        actualizados = 0

        if not dry_run and estaciones_validas:
            with transaction.atomic():
                for data in estaciones_validas:
                    _, created = SmuEstacion.objects.update_or_create(
                        nombre_sitio=data['nombre_sitio'],
                        defaults=data
                    )
                    if created:
                        insertados += 1
                    else:
                        actualizados += 1

        return {
            'total_recibidos': len(registros),
            'total_validos': len(estaciones_validas),
            'total_duplicados_omitidos': len(duplicados),
            'total_inconsistencias': len(inconsistencias),
            'duplicados': duplicados[:20],
            'inconsistencias': inconsistencias[:20],
            'dry_run': dry_run,
            'insertados': insertados,
            'actualizados': actualizados,
        }

    @classmethod
    def procesar_matriz_lpu(
        cls,
        registros: List[Dict[str, Any]],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Valida, normaliza y asegura precisión decimal estricta y unicidad SAP para ítems LPU.
        Si dry_run=True, no efectúa escrituras en BD.
        """
        sap_vistos = set()
        items_validos = []
        duplicados = []
        inconsistencias = []

        for idx, item in enumerate(registros, start=1):
            codigo_sap = limpiar_texto(item.get('codigo_sap'))
            texto_sap = limpiar_texto(item.get('texto_sap') or item.get('descripcion'))

            if not codigo_sap:
                inconsistencias.append({
                    'fila': idx,
                    'error': 'Falta el código SAP obligatorio'
                })
                continue

            if not texto_sap:
                inconsistencias.append({
                    'fila': idx,
                    'codigo_sap': codigo_sap,
                    'error': 'Falta la descripción o texto oficial SAP'
                })
                continue

            sap_clave = codigo_sap.upper()
            if sap_clave in sap_vistos:
                duplicados.append({
                    'fila': idx,
                    'codigo_sap': codigo_sap
                })
                continue

            sap_vistos.add(sap_clave)

            # Moneda con 2 decimales exactos
            valor_unitario = convertir_decimal(item.get('valor_unitario', '0.00'), decimales=2) or Decimal('0.00')

            datos_item = {
                'codigo_sap': codigo_sap,
                'codigo_liquidacion': limpiar_texto(item.get('codigo_liquidacion')) or None,
                'texto_sap': texto_sap,
                'descripcion': limpiar_texto(item.get('descripcion')) or None,
                'unidad_medida': limpiar_texto(item.get('unidad_medida')) or 'UN',
                'valor_unitario': valor_unitario,
                'tipo_registro': limpiar_texto(item.get('tipo_registro')) or None,
                'fecha_vigencia_inicio': limpiar_fecha(item.get('fecha_vigencia_inicio')),
                'fecha_vigencia_fin': limpiar_fecha(item.get('fecha_vigencia_fin')),
                'activo': bool(item.get('activo', True)),
            }
            items_validos.append(datos_item)

        insertados = 0
        actualizados = 0

        if not dry_run and items_validos:
            with transaction.atomic():
                for data in items_validos:
                    _, created = SmuMatrizLpu.objects.update_or_create(
                        codigo_sap=data['codigo_sap'],
                        defaults=data
                    )
                    if created:
                        insertados += 1
                    else:
                        actualizados += 1

        return {
            'total_recibidos': len(registros),
            'total_validos': len(items_validos),
            'total_duplicados_omitidos': len(duplicados),
            'total_inconsistencias': len(inconsistencias),
            'duplicados': duplicados[:20],
            'inconsistencias': inconsistencias[:20],
            'dry_run': dry_run,
            'insertados': insertados,
            'actualizados': actualizados,
        }
