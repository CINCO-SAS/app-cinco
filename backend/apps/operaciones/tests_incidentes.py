from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.operaciones.serializers.incidente_serializer import (
    IncidenteBuscarQuerySerializer,
)
from apps.operaciones.services.incidente_sharepoint_service import (
    IncidenteConfigError,
    IncidenteSharePointService,
)
from apps.operaciones.views.incidente_view import IncidenteViewSet


TEST_FUENTES = {
    "back_mtto_2026": {
        "key": "back_mtto_2026",
        "label": "BACK_MTTO_INFO_2026",
        "file_url": "https://disenocinco.sharepoint.com/file1",
        "site_url": "https://disenocinco.sharepoint.com/sites/DesignerTeam",
        "file_name": "BACK_MTTO_INFO_2026.xlsx",
        "sheet_name": "BACKLOG",
        "table_name": "INFO_4",
        "habilitado": True,
    },
    "archivo_2": {
        "key": "archivo_2",
        "label": "Segundo Archivo (Pendiente)",
        "file_url": "",
        "site_url": "",
        "file_name": "",
        "sheet_name": "BACKLOG",
        "table_name": "INFO_4",
        "habilitado": False,
    },
}


class IncidenteBuscarQuerySerializerTests(SimpleTestCase):
    def test_normaliza_inc_a_mayusculas(self):
        serializer = IncidenteBuscarQuerySerializer(data={"inc": "  inc000007572996  ", "refresh": "1"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["inc"], "INC000007572996")
        self.assertTrue(serializer.validated_data["refresh"])

    def test_rechaza_caracteres_invalidos_y_longitud_excesiva(self):
        bad_chars = IncidenteBuscarQuerySerializer(data={"inc": "INC 123;DROP"})
        self.assertFalse(bad_chars.is_valid())
        self.assertIn("inc", bad_chars.errors)

        too_long = IncidenteBuscarQuerySerializer(data={"inc": "A" * 41})
        self.assertFalse(too_long.is_valid())
        self.assertIn("inc", too_long.errors)


@override_settings(
    SHAREPOINT_INCIDENTES_FUENTES=TEST_FUENTES,
    SHAREPOINT_INCIDENTES_CACHE_TTL_SECONDS=300,
    SHAREPOINT_INCIDENTES_STALE_TTL_SECONDS=86400,
    SHAREPOINT_INCIDENTES_REFRESH_COOLDOWN_SECONDS=60,
)
class IncidenteSharePointServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_listar_fuentes_y_validar_fuente_deshabilitada(self):
        fuentes = IncidenteSharePointService.listar_fuentes()
        self.assertEqual(len(fuentes), 2)
        self.assertTrue(fuentes[0]["habilitado"])
        self.assertFalse(fuentes[1]["habilitado"])

        with self.assertRaises(IncidenteConfigError):
            IncidenteSharePointService.get_fuente_config("archivo_2")

        with self.assertRaises(IncidenteConfigError):
            IncidenteSharePointService.get_fuente_config("no_existe")

    def test_parse_f_creacion_serial_excel_y_none(self):
        iso = IncidenteSharePointService._parse_f_creacion(46350.5402777778, "24/11/2026 12:58")
        self.assertEqual(iso, "2026-11-24T12:58:00-05:00")

        self.assertIsNone(IncidenteSharePointService._parse_f_creacion(None, ""))

        iso_str = IncidenteSharePointService._parse_f_creacion("", "25/11/2026 08:48")
        self.assertEqual(iso_str, "2026-11-25T08:48:00-05:00")

    def test_duplicados_ordenados_por_f_creacion_descendente(self):
        payload = {
            "values": [
                ["EXTRA", "F_CREACION", "INC", "OT", "CLIENTE", "ESTADO"],
                ["X", None, "INC001", "OT-0", "CLI-0", "PENDIENTE"],
                ["X", 46350.5402777778, "INC001", "OT-1", "CLI-1", "PROGRAMADO"],
                ["X", 46351.3666666667, "INC001", "OT-2", "CLI-2", "CERRADO"],
                ["X", 46351.0, "", "OT-EMPTY", "CLI-EMPTY", "N/A"],
            ],
            "text": [
                ["EXTRA", "F_CREACION", "INC", "OT", "CLIENTE", "ESTADO"],
                ["X", "", "INC001", "OT-0", "CLI-0", "PENDIENTE"],
                ["X", "24/11/2026 12:58", "INC001", "OT-1", "CLI-1", "PROGRAMADO"],
                ["X", "25/11/2026 08:48", "INC001", "OT-2", "CLI-2", "CERRADO"],
                ["X", "25/11/2026 00:00", "", "OT-EMPTY", "CLI-EMPTY", "N/A"],
            ],
        }
        cfg = TEST_FUENTES["back_mtto_2026"]
        index = IncidenteSharePointService._build_index(payload, cfg)

        self.assertEqual(index["row_count"], 3)
        self.assertEqual(index["unique_count"], 1)
        matches = index["records"]["INC001"]
        self.assertEqual(len(matches), 3)
        self.assertEqual(matches[0]["ot"], "OT-2")
        self.assertEqual(matches[1]["ot"], "OT-1")
        self.assertEqual(matches[2]["ot"], "OT-0")
        self.assertIsNone(matches[2]["f_creacion"])

    @patch.object(IncidenteSharePointService, "_fetch_table_range")
    def test_cooldown_y_stale_fallback(self, mock_fetch):
        mock_fetch.return_value = {
            "values": [
                ["F_CREACION", "INC", "OT", "CLIENTE", "ESTADO"],
                [46350.5402777778, "INC007", "OT-77", "ACME", "PROGRAMADO"],
            ],
            "text": [
                ["F_CREACION", "INC", "OT", "CLIENTE", "ESTADO"],
                ["24/11/2026 12:58", "INC007", "OT-77", "ACME", "PROGRAMADO"],
            ],
        }

        res1 = IncidenteSharePointService.buscar_incidente("inc007", fuente="back_mtto_2026")
        self.assertTrue(res1["encontrado"])
        self.assertTrue(res1["refreshed"])
        self.assertEqual(res1["principal"]["ot"], "OT-77")
        self.assertEqual(mock_fetch.call_count, 1)

        # Refresh dentro de cooldown no vuelve a llamar a SharePoint
        res2 = IncidenteSharePointService.buscar_incidente("INC007", fuente="back_mtto_2026", refresh=True)
        self.assertTrue(res2["cooldown_active"])
        self.assertFalse(res2["refreshed"])
        self.assertEqual(mock_fetch.call_count, 1)

        # Expirar caché fresca y cooldown manteniendo stale, luego simular fallo de Graph
        keys = IncidenteSharePointService._cache_keys("back_mtto_2026")
        cache.delete(keys["index"])
        cache.delete(keys["cooldown"])
        mock_fetch.side_effect = RuntimeError("Graph timeout")

        res_stale = IncidenteSharePointService.buscar_incidente("INC007", fuente="back_mtto_2026")
        self.assertTrue(res_stale["encontrado"])
        self.assertTrue(res_stale["stale"])
        self.assertEqual(res_stale["principal"]["cliente"], "ACME")

    @patch("apps.operaciones.services.incidente_sharepoint_service.SharePointGraphClient.resolve_drive_item_by_url")
    @patch("apps.operaciones.services.incidente_sharepoint_service.SharePointGraphClient.request")
    def test_re_resuelve_item_id_si_graph_devuelve_404(self, mock_request, mock_resolve):
        keys = IncidenteSharePointService._cache_keys("back_mtto_2026")
        cache.set(keys["item"], {"drive_id": "d1", "item_id": "old-id"}, timeout=3600)

        r_404 = MagicMock(status_code=404)
        err_404 = requests.HTTPError("404 Not Found", response=r_404)
        r_ok = MagicMock(content=b"{}")
        r_ok.json.return_value = {"address": "BACKLOG!A1:E2", "values": [], "text": []}

        mock_request.side_effect = [err_404, r_ok]
        mock_resolve.return_value = {"drive_id": "d1", "item_id": "new-id"}

        IncidenteSharePointService._fetch_table_range(TEST_FUENTES["back_mtto_2026"])

        mock_resolve.assert_called_once()
        self.assertEqual(mock_request.call_count, 2)
        self.assertIn("/items/new-id/", mock_request.call_args_list[1].args[1])


@override_settings(SHAREPOINT_INCIDENTES_FUENTES=TEST_FUENTES)
class IncidenteViewSetTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(is_authenticated=True, id=1, username="tester")

    def tearDown(self):
        cache.clear()

    def test_listar_fuentes_endpoint(self):
        view = IncidenteViewSet.as_view({"get": "listar_fuentes"})
        req = self.factory.get("/operaciones/incidentes/fuentes/")
        force_authenticate(req, user=self.user)
        resp = view(req)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])
        self.assertEqual(len(resp.data["fuentes"]), 2)

    @patch.object(IncidenteSharePointService, "buscar_incidente")
    def test_buscar_endpoint_200_y_404(self, mock_buscar):
        view = IncidenteViewSet.as_view({"get": "buscar"})

        mock_buscar.return_value = {
            "encontrado": True,
            "fuente": {"key": "back_mtto_2026", "label": "BACK_MTTO_INFO_2026"},
            "inc": "INC000007572996",
            "principal": {
                "inc": "INC000007572996",
                "f_creacion": "2026-11-24T12:58:00-05:00",
                "ot": "OT-123",
                "cliente": "CLIENTE TEST",
                "estado": "PROGRAMADO",
            },
            "coincidencias": [],
            "total_coincidencias": 1,
            "stale": False,
            "refreshed": False,
            "cooldown_active": False,
            "cached_at": "2026-11-27T08:50:00-05:00",
            "antiguedad_minutos": 0,
            "cooldown_segundos": 60,
        }
        req_ok = self.factory.get("/operaciones/incidentes/buscar/", {"inc": "inc000007572996"})
        force_authenticate(req_ok, user=self.user)
        resp_ok = view(req_ok)
        self.assertEqual(resp_ok.status_code, 200)
        self.assertEqual(resp_ok.data["principal"]["ot"], "OT-123")

        mock_buscar.return_value = {
            **mock_buscar.return_value,
            "encontrado": False,
            "principal": None,
            "total_coincidencias": 0,
        }
        req_404 = self.factory.get("/operaciones/incidentes/buscar/", {"inc": "INC999"})
        force_authenticate(req_404, user=self.user)
        resp_404 = view(req_404)
        self.assertEqual(resp_404.status_code, 404)
        self.assertFalse(resp_404.data["success"])
