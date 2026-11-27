import base64
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import msal
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SharePointGraphClient:
    """
    Cliente base compartido para autenticación MSAL y consumo de Microsoft Graph API.

    Centraliza:
    - Instancia singleton de MSAL con caché en memoria de tokens.
    - Peticiones HTTP con timeout explícito y reintentos ante 429 / 5xx / errores de red.
    - Resolución de sitios, bibliotecas (drives) y archivos por URL compartida o nombre.
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    _msal_app: Optional[msal.ConfidentialClientApplication] = None

    @classmethod
    def reset_msal_client(cls) -> None:
        """Reinicia la instancia cacheada de MSAL (útil en pruebas o rotación de credenciales)."""
        SharePointGraphClient._msal_app = None
        cls._msal_app = None

    @classmethod
    def get_msal_client(cls) -> msal.ConfidentialClientApplication:
        """Obtiene o inicializa el cliente MSAL singleton con caché interna de tokens."""
        if SharePointGraphClient._msal_app is None:
            tenant_id = getattr(settings, "SHAREPOINT_TENANT_ID", "") or ""
            client_id = getattr(settings, "SHAREPOINT_CLIENT_ID", "") or ""
            client_secret = getattr(settings, "SHAREPOINT_CLIENT_SECRET", "") or ""

            if not (tenant_id and client_id and client_secret):
                raise ValueError(
                    "Faltan credenciales de Microsoft Graph en settings / .env: "
                    "SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET"
                )

            authority = f"https://login.microsoftonline.com/{tenant_id}"
            SharePointGraphClient._msal_app = msal.ConfidentialClientApplication(
                client_id=client_id,
                client_credential=client_secret,
                authority=authority,
            )
        return SharePointGraphClient._msal_app

    @classmethod
    def get_access_token(cls) -> str:
        """
        Adquiere un token de acceso para Microsoft Graph API.
        MSAL busca automáticamente en su caché en memoria y renueva cuando expira.
        """
        app = cls.get_msal_client()
        scopes = ["https://graph.microsoft.com/.default"]
        result = app.acquire_token_silent(scopes=scopes, account=None)

        if not result:
            logger.info("Adquiriendo nuevo token de Microsoft Graph con credenciales de cliente...")
            result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" in result:
            return result["access_token"]

        error_desc = result.get(
            "error_description",
            result.get("error", "Error desconocido al obtener token"),
        )
        logger.error("Error al autenticar con Microsoft Graph: %s", error_desc)
        raise RuntimeError(f"Error al autenticar con Microsoft Graph: {error_desc}")

    @classmethod
    def _headers(cls) -> Dict[str, str]:
        token = cls.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @classmethod
    def _build_url(cls, endpoint_or_url: str) -> str:
        if endpoint_or_url.startswith("http://") or endpoint_or_url.startswith("https://"):
            return endpoint_or_url
        path = endpoint_or_url if endpoint_or_url.startswith("/") else f"/{endpoint_or_url}"
        return f"{cls.GRAPH_BASE_URL}{path}"

    @classmethod
    def request(
        cls,
        method: str,
        endpoint_or_url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: int = 20,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        retry_statuses: Tuple[int, ...] = (500, 502, 503, 504),
    ) -> requests.Response:
        """
        Ejecuta una petición HTTP hacia Microsoft Graph con timeout y reintentos
        para HTTP 429 (respetando Retry-After), códigos transitorios y fallos de red.
        Los errores 4xx no transitorios (como 400/401/403/404) se propagan de inmediato.
        """
        url = cls._build_url(endpoint_or_url)
        delay = backoff_seconds
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=cls._headers(),
                    params=params,
                    json=json,
                    timeout=timeout,
                )

                if response.status_code == 429:
                    retry_after_raw = response.headers.get("Retry-After", "2")
                    try:
                        retry_after = max(1, min(int(retry_after_raw), 30))
                    except (TypeError, ValueError):
                        retry_after = 2
                    if attempt < max_retries:
                        logger.warning(
                            "Graph API rate limit (HTTP 429) en %s; reintento %d/%d en %ss",
                            url,
                            attempt,
                            max_retries,
                            retry_after,
                        )
                        time.sleep(retry_after)
                        continue
                    response.raise_for_status()

                if response.status_code in retry_statuses and attempt < max_retries:
                    logger.warning(
                        "Graph API devolvió HTTP %s en %s; reintento %d/%d en %.1fs",
                        response.status_code,
                        url,
                        attempt,
                        max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError:
                raise
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt >= max_retries:
                    raise
                logger.warning(
                    "Error de red en Graph API (%s) intento %d/%d: %s",
                    url,
                    attempt,
                    max_retries,
                    exc,
                )
                time.sleep(delay)
                delay *= 2

        if last_exc:
            raise last_exc
        raise RuntimeError(f"Error inesperado consultando Microsoft Graph: {url}")

    @staticmethod
    def encode_sharing_url(url: str) -> str:
        """Codifica una URL compartida de SharePoint al formato u!<base64url> de Graph /shares."""
        encoded = base64.urlsafe_b64encode(url.strip().encode("utf-8")).decode("utf-8").rstrip("=")
        return f"u!{encoded}"

    @classmethod
    def resolve_site_info(cls, site_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Dada una URL de SharePoint (incluso si incluye carpetas o parámetros de vista),
        resuelve el ID único del sitio (Site ID) y la ruta relativa.
        """
        url = site_url or getattr(settings, "SHAREPOINT_SITE_URL", "")
        if not url:
            raise ValueError("No se configuró SHAREPOINT_SITE_URL en las variables de entorno.")

        parsed = urlparse(url)
        hostname = parsed.netloc

        path_segments = [seg for seg in parsed.path.strip("/").split("/") if seg]
        if len(path_segments) >= 2 and path_segments[0].lower() in ("sites", "teams"):
            site_relative_path = f"/{path_segments[0]}/{path_segments[1]}"
        else:
            site_relative_path = parsed.path.rstrip("/")

        endpoint = f"{cls.GRAPH_BASE_URL}/sites/{hostname}:{site_relative_path}"
        response = requests.get(endpoint, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        data = response.json()
        return {
            "site_id": data["id"],
            "site_name": data.get("displayName") or data.get("name"),
            "hostname": hostname,
            "site_relative_path": site_relative_path,
        }

    @classmethod
    def resolve_site_id(cls, site_url: Optional[str] = None) -> str:
        """Retorna únicamente el Site ID."""
        info = cls.resolve_site_info(site_url)
        return info["site_id"]

    @classmethod
    def list_drives(cls, site_id: str) -> List[Dict[str, Any]]:
        """Lista las bibliotecas de documentos (Drives) dentro de un sitio."""
        endpoint = f"{cls.GRAPH_BASE_URL}/sites/{site_id}/drives"
        response = requests.get(endpoint, headers=cls._headers(), timeout=15)
        response.raise_for_status()
        return response.json().get("value", [])

    @classmethod
    def resolve_drive_item_by_url(cls, file_url: str, timeout: int = 20) -> Dict[str, Any]:
        """
        Resuelve un archivo de SharePoint a partir de su URL directa/compartida
        usando el endpoint /shares/{shareId}/driveItem de Microsoft Graph.
        """
        if not file_url or not file_url.strip():
            raise ValueError("La URL del archivo en SharePoint es obligatoria.")

        share_token = cls.encode_sharing_url(file_url)
        response = cls.request(
            "GET",
            f"/shares/{share_token}/driveItem",
            timeout=timeout,
        )
        data = response.json()
        parent_ref = data.get("parentReference") or {}
        drive_id = parent_ref.get("driveId")
        item_id = data.get("id")

        if not (drive_id and item_id):
            raise RuntimeError("Microsoft Graph no devolvió driveId e itemId para la URL proporcionada.")

        return {
            "drive_id": drive_id,
            "item_id": item_id,
            "name": data.get("name", ""),
            "size": data.get("size"),
            "last_modified": data.get("lastModifiedDateTime"),
            "web_url": data.get("webUrl"),
        }

    @classmethod
    def find_file_in_site(
        cls,
        site_url: str,
        file_name: str,
        timeout: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        Busca un archivo por nombre exacto (case-insensitive) en las bibliotecas (drives)
        de un sitio SharePoint.
        """
        if not (site_url and file_name):
            return None

        target_name = file_name.strip().lower()
        site_id = cls.resolve_site_id(site_url)
        drives = cls.list_drives(site_id)
        search_term = file_name.rsplit(".", 1)[0].strip()

        for drive in drives:
            drive_id = drive.get("id")
            if not drive_id:
                continue
            try:
                resp = cls.request(
                    "GET",
                    f"/drives/{drive_id}/root/search(q='{search_term}')",
                    timeout=timeout,
                )
                items = resp.json().get("value", [])
            except Exception:
                resp = cls.request(
                    "GET",
                    f"/drives/{drive_id}/root/children",
                    timeout=timeout,
                )
                items = resp.json().get("value", [])

            for item in items:
                if (item.get("name") or "").strip().lower() == target_name:
                    return {
                        "drive_id": drive_id,
                        "item_id": item.get("id"),
                        "name": item.get("name", ""),
                        "size": item.get("size"),
                        "last_modified": item.get("lastModifiedDateTime"),
                        "web_url": item.get("webUrl"),
                    }

        return None
