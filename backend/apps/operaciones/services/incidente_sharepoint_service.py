import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.common.services import SharePointGraphClient

logger = logging.getLogger(__name__)


class IncidenteConfigError(ValueError):
    """Error de configuración de fuente de Incidentes en SharePoint."""


class IncidenteSharePointError(RuntimeError):
    """Error de comunicación o lectura con Microsoft Graph / SharePoint."""


class IncidenteSharePointService:
    """
    Servicio de consulta de incidentes desde archivos Excel en Microsoft SharePoint
    (hoja/tabla configurada por fuente), con caché compartida, bloqueo contra
    descargas simultáneas, cooldown de refresco y respaldo stale.
    """

    REQUIRED_COLUMNS = ("INC", "F_CREACION", "OT", "CLIENTE", "ESTADO")
    EXCEL_EPOCH = datetime(1899, 12, 30)

    @classmethod
    def _tz(cls) -> ZoneInfo:
        tz_name = getattr(settings, "TIME_ZONE", "America/Bogota") or "America/Bogota"
        return ZoneInfo(tz_name)

    @classmethod
    def get_fuentes_config(cls) -> Dict[str, Dict[str, Any]]:
        return getattr(settings, "SHAREPOINT_INCIDENTES_FUENTES", {}) or {}

    @classmethod
    def listar_fuentes(cls) -> List[Dict[str, Any]]:
        """Retorna el catálogo público de fuentes disponibles para el selector del frontend."""
        return [
            {
                "key": cfg["key"],
                "label": cfg["label"],
                "habilitado": bool(cfg.get("habilitado")),
            }
            for cfg in cls.get_fuentes_config().values()
        ]

    @classmethod
    def get_fuente_config(cls, fuente_key: Optional[str] = None) -> Dict[str, Any]:
        fuentes = cls.get_fuentes_config()
        if not fuentes:
            raise IncidenteConfigError("No hay fuentes de incidentes configuradas en el servidor.")

        key = (fuente_key or "").strip()
        if not key:
            for cfg in fuentes.values():
                if cfg.get("habilitado"):
                    return cfg
            raise IncidenteConfigError("No hay ninguna fuente de incidentes habilitada.")

        cfg = fuentes.get(key)
        if not cfg:
            raise IncidenteConfigError(f"La fuente '{key}' no existe en la configuración.")
        if not cfg.get("habilitado"):
            raise IncidenteConfigError(
                f"La fuente '{cfg['label']}' aún no tiene archivo configurado en SharePoint."
            )
        return cfg

    @staticmethod
    def _cache_keys(fuente_key: str) -> Dict[str, str]:
        return {
            "item": f"sp_inc:item:{fuente_key}",
            "index": f"sp_inc:index:{fuente_key}",
            "stale": f"sp_inc:stale:{fuente_key}",
            "lock": f"sp_inc:lock:{fuente_key}",
            "cooldown": f"sp_inc:refresh_cd:{fuente_key}",
        }

    @classmethod
    def _resolve_item_ids(
        cls,
        cfg: Dict[str, Any],
        force_resolve: bool = False,
    ) -> Tuple[str, str]:
        keys = cls._cache_keys(cfg["key"])
        if not force_resolve:
            cached_item = cache.get(keys["item"])
            if cached_item and cached_item.get("drive_id") and cached_item.get("item_id"):
                return cached_item["drive_id"], cached_item["item_id"]

        resolved: Optional[Dict[str, Any]] = None
        if cfg.get("file_url"):
            resolved = SharePointGraphClient.resolve_drive_item_by_url(cfg["file_url"], timeout=20)
        elif cfg.get("site_url") and cfg.get("file_name"):
            resolved = SharePointGraphClient.find_file_in_site(
                cfg["site_url"],
                cfg["file_name"],
                timeout=20,
            )

        if not resolved or not resolved.get("drive_id") or not resolved.get("item_id"):
            raise IncidenteSharePointError(
                f"No se pudo ubicar el archivo '{cfg.get('label')}' en SharePoint."
            )

        cache.set(
            keys["item"],
            {"drive_id": resolved["drive_id"], "item_id": resolved["item_id"]},
            timeout=3600,
        )
        return resolved["drive_id"], resolved["item_id"]

    @classmethod
    def _fetch_table_range(cls, cfg: Dict[str, Any]) -> Dict[str, Any]:
        table_name = quote(cfg.get("table_name") or "INFO_4", safe="")
        drive_id, item_id = cls._resolve_item_ids(cfg, force_resolve=False)
        endpoint = (
            f"/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}"
            "/range?$select=address,values,text"
        )

        t0 = time.perf_counter()
        try:
            response = SharePointGraphClient.request("GET", endpoint, timeout=30)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 404:
                logger.info(
                    "Graph devolvió 404 para %s; re-resolviendo item_id en SharePoint...",
                    cfg["key"],
                )
                cache.delete(cls._cache_keys(cfg["key"])["item"])
                drive_id, item_id = cls._resolve_item_ids(cfg, force_resolve=True)
                endpoint = (
                    f"/drives/{drive_id}/items/{item_id}/workbook/tables/{table_name}"
                    "/range?$select=address,values,text"
                )
                response = SharePointGraphClient.request("GET", endpoint, timeout=30)
            else:
                raise

        elapsed = time.perf_counter() - t0
        payload_bytes = len(response.content or b"")
        data = response.json()
        logger.info(
            "SharePoint Incidentes [%s] tabla '%s' consultada en %.2fs (%d bytes, %s)",
            cfg["key"],
            cfg.get("table_name"),
            elapsed,
            payload_bytes,
            data.get("address", ""),
        )
        return data

    @classmethod
    def _parse_f_creacion(cls, raw_value: Any, text_value: Any) -> Optional[str]:
        """
        Convierte la fecha de Excel (serial numérico o texto) a string ISO 8601
        con zona horaria del proyecto (America/Bogota). Retorna None si está vacía.
        """
        tz = cls._tz()

        if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
            dt_naive = cls.EXCEL_EPOCH + timedelta(days=float(raw_value))
            # Redondeo al segundo más cercano para evitar deriva binaria de punto flotante
            if dt_naive.microsecond >= 500_000:
                dt_naive = dt_naive.replace(microsecond=0) + timedelta(seconds=1)
            else:
                dt_naive = dt_naive.replace(microsecond=0)
            return dt_naive.replace(tzinfo=tz).isoformat()

        if isinstance(raw_value, datetime):
            dt = raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=tz)
            return dt.isoformat()

        candidate = str(text_value if text_value not in (None, "") else (raw_value or "")).strip()
        if not candidate:
            return None

        try:
            dt = datetime.fromisoformat(candidate)
            return (dt if dt.tzinfo else dt.replace(tzinfo=tz)).isoformat()
        except ValueError:
            pass

        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(candidate, fmt).replace(tzinfo=tz)
                return dt.isoformat()
            except ValueError:
                continue

        return None

    @staticmethod
    def _clean_cell_text(raw_value: Any, text_value: Any) -> str:
        if text_value not in (None, ""):
            return str(text_value).strip()
        if raw_value is None:
            return ""
        return str(raw_value).strip()

    @classmethod
    def _build_index(cls, range_payload: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
        values = range_payload.get("values") or []
        texts = range_payload.get("text") or []
        if not values:
            raise IncidenteSharePointError(
                f"La tabla '{cfg.get('table_name')}' en '{cfg['label']}' no devolvió datos."
            )

        headers_row = values[0]
        col_indices: Dict[str, int] = {}
        for idx, col_name in enumerate(headers_row):
            if col_name is None:
                continue
            key = str(col_name).strip().upper()
            if key in cls.REQUIRED_COLUMNS and key not in col_indices:
                col_indices[key] = idx

        missing = [c for c in cls.REQUIRED_COLUMNS if c not in col_indices]
        if missing:
            raise IncidenteSharePointError(
                f"Faltan las columnas {', '.join(missing)} en la tabla '{cfg.get('table_name')}'."
            )

        records: Dict[str, List[Dict[str, Any]]] = {}
        inc_idx = col_indices["INC"]
        fc_idx = col_indices["F_CREACION"]
        ot_idx = col_indices["OT"]
        cli_idx = col_indices["CLIENTE"]
        est_idx = col_indices["ESTADO"]

        total_rows = 0
        for row_num in range(1, len(values)):
            raw_row = values[row_num]
            text_row = texts[row_num] if row_num < len(texts) else []

            raw_inc = raw_row[inc_idx] if inc_idx < len(raw_row) else None
            text_inc = text_row[inc_idx] if inc_idx < len(text_row) else None
            inc_clean = cls._clean_cell_text(raw_inc, text_inc).upper()
            if not inc_clean:
                continue

            total_rows += 1
            record = {
                "inc": inc_clean,
                "f_creacion": cls._parse_f_creacion(
                    raw_row[fc_idx] if fc_idx < len(raw_row) else None,
                    text_row[fc_idx] if fc_idx < len(text_row) else None,
                ),
                "ot": cls._clean_cell_text(
                    raw_row[ot_idx] if ot_idx < len(raw_row) else None,
                    text_row[ot_idx] if ot_idx < len(text_row) else None,
                ),
                "cliente": cls._clean_cell_text(
                    raw_row[cli_idx] if cli_idx < len(raw_row) else None,
                    text_row[cli_idx] if cli_idx < len(text_row) else None,
                ),
                "estado": cls._clean_cell_text(
                    raw_row[est_idx] if est_idx < len(raw_row) else None,
                    text_row[est_idx] if est_idx < len(text_row) else None,
                ),
            }
            records.setdefault(inc_clean, []).append(record)

        # Orden explícito para duplicados: más reciente por f_creacion primero (None al final)
        for inc_key, items in records.items():
            if len(items) > 1:
                items.sort(
                    key=lambda item: (item["f_creacion"] is not None, item["f_creacion"] or ""),
                    reverse=True,
                )

        return {
            "records": records,
            "cached_at": timezone.now().isoformat(),
            "row_count": total_rows,
            "unique_count": len(records),
        }

    @classmethod
    def _get_or_load_index(
        cls,
        cfg: Dict[str, Any],
        force_refresh: bool = False,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        keys = cls._cache_keys(cfg["key"])
        cache_ttl = getattr(settings, "SHAREPOINT_INCIDENTES_CACHE_TTL_SECONDS", 300)
        stale_ttl = getattr(settings, "SHAREPOINT_INCIDENTES_STALE_TTL_SECONDS", 86400)
        cooldown_ttl = getattr(settings, "SHAREPOINT_INCIDENTES_REFRESH_COOLDOWN_SECONDS", 60)

        cached = cache.get(keys["index"])
        stale_cached = cache.get(keys["stale"])

        if force_refresh and cache.get(keys["cooldown"]):
            fallback = cached or stale_cached
            if fallback is not None:
                return fallback, {
                    "stale": cached is None,
                    "refreshed": False,
                    "cooldown_active": True,
                }

        if not force_refresh and cached is not None:
            return cached, {
                "stale": False,
                "refreshed": False,
                "cooldown_active": False,
            }

        lock_acquired = cache.add(keys["lock"], "1", timeout=30)
        if not lock_acquired:
            for _ in range(6):
                time.sleep(0.5)
                ready = cache.get(keys["index"])
                if ready is not None:
                    return ready, {
                        "stale": False,
                        "refreshed": False,
                        "cooldown_active": False,
                    }
            if stale_cached is not None:
                return stale_cached, {
                    "stale": True,
                    "refreshed": False,
                    "cooldown_active": False,
                }

        try:
            range_payload = cls._fetch_table_range(cfg)
            index_data = cls._build_index(range_payload, cfg)
            cache.set(keys["index"], index_data, timeout=cache_ttl)
            cache.set(keys["stale"], index_data, timeout=stale_ttl)
            cache.set(keys["cooldown"], "1", timeout=cooldown_ttl)
            return index_data, {
                "stale": False,
                "refreshed": True,
                "cooldown_active": False,
            }
        except Exception as exc:
            logger.error(
                "Error consultando SharePoint para fuente '%s': %s",
                cfg["key"],
                exc,
                exc_info=True,
            )
            stale_fallback = cache.get(keys["stale"])
            if stale_fallback is not None:
                return stale_fallback, {
                    "stale": True,
                    "refreshed": False,
                    "cooldown_active": False,
                }
            raise IncidenteSharePointError(
                f"No fue posible consultar '{cfg['label']}' en SharePoint: {exc}"
            ) from exc
        finally:
            if lock_acquired:
                cache.delete(keys["lock"])

    @staticmethod
    def _calcular_antiguedad_minutos(cached_at_iso: Optional[str]) -> int:
        if not cached_at_iso:
            return 0
        try:
            cached_dt = datetime.fromisoformat(cached_at_iso)
            if cached_dt.tzinfo is None:
                cached_dt = timezone.make_aware(cached_dt, timezone.get_default_timezone())
            delta = timezone.now() - cached_dt
            return max(0, int(delta.total_seconds() // 60))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def buscar_incidente(
        cls,
        inc: str,
        fuente: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Busca un INC normalizado en la fuente de SharePoint seleccionada.
        """
        cfg = cls.get_fuente_config(fuente)
        inc_norm = (inc or "").strip().upper()
        index_data, meta = cls._get_or_load_index(cfg, force_refresh=refresh)

        matches = index_data.get("records", {}).get(inc_norm, [])
        cached_at = index_data.get("cached_at")

        return {
            "encontrado": bool(matches),
            "fuente": {
                "key": cfg["key"],
                "label": cfg["label"],
            },
            "inc": inc_norm,
            "principal": matches[0] if matches else None,
            "coincidencias": matches,
            "total_coincidencias": len(matches),
            "stale": meta["stale"],
            "refreshed": meta["refreshed"],
            "cooldown_active": meta["cooldown_active"],
            "cached_at": cached_at,
            "antiguedad_minutos": cls._calcular_antiguedad_minutos(cached_at),
            "cooldown_segundos": getattr(
                settings, "SHAREPOINT_INCIDENTES_REFRESH_COOLDOWN_SECONDS", 60
            ),
        }
