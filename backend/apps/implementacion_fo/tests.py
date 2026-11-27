from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.implementacion_fo.services.sharepoint_mapping_service import (
    SharePointMappingService,
)


class SharePointMappingServiceTests(TestCase):
    def setUp(self):
        SharePointMappingService.reset_msal_client()
        SharePointMappingService._list_columns_cache.clear()

    def tearDown(self):
        SharePointMappingService.reset_msal_client()
        SharePointMappingService._list_columns_cache.clear()

    @patch("apps.common.services.sharepoint_graph_client.msal.ConfidentialClientApplication")
    def test_get_access_token_reuses_msal_client_and_silent_cache(self, mock_msal_cls):
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = {"access_token": "cached-token"}
        mock_msal_cls.return_value = mock_app

        with patch("django.conf.settings.SHAREPOINT_TENANT_ID", "tenant-1"), \
             patch("django.conf.settings.SHAREPOINT_CLIENT_ID", "client-1"), \
             patch("django.conf.settings.SHAREPOINT_CLIENT_SECRET", "secret-1"):
            token1 = SharePointMappingService.get_access_token()
            token2 = SharePointMappingService.get_access_token()

        self.assertEqual(token1, "cached-token")
        self.assertEqual(token2, "cached-token")
        mock_msal_cls.assert_called_once()
        mock_app.acquire_token_for_client.assert_not_called()

    @patch("apps.common.services.sharepoint_graph_client.msal.ConfidentialClientApplication")
    def test_get_access_token_falls_back_to_client_credentials(self, mock_msal_cls):
        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {"access_token": "fresh-token"}
        mock_msal_cls.return_value = mock_app

        with patch("django.conf.settings.SHAREPOINT_TENANT_ID", "tenant-1"), \
             patch("django.conf.settings.SHAREPOINT_CLIENT_ID", "client-1"), \
             patch("django.conf.settings.SHAREPOINT_CLIENT_SECRET", "secret-1"):
            token = SharePointMappingService.get_access_token()

        self.assertEqual(token, "fresh-token")
        mock_app.acquire_token_for_client.assert_called_once_with(
            scopes=["https://graph.microsoft.com/.default"]
        )

    def test_get_msal_client_requires_credentials(self):
        with patch("django.conf.settings.SHAREPOINT_TENANT_ID", ""), \
             patch("django.conf.settings.SHAREPOINT_CLIENT_ID", ""), \
             patch("django.conf.settings.SHAREPOINT_CLIENT_SECRET", ""):
            with self.assertRaises(ValueError):
                SharePointMappingService.get_msal_client()

    @patch("apps.common.services.sharepoint_graph_client.requests.get")
    @patch.object(SharePointMappingService, "get_access_token", return_value="tok")
    def test_resolve_site_info_extracts_site_path(self, _mock_tok, mock_get):
        resp = MagicMock()
        resp.json.return_value = {"id": "site-123", "displayName": "GRUPO EXTERNO"}
        mock_get.return_value = resp

        info = SharePointMappingService.resolve_site_info(
            "https://empresa.sharepoint.com/sites/MiSitio/Documentos Compartidos/Carpeta"
        )

        self.assertEqual(info["site_id"], "site-123")
        self.assertEqual(info["site_name"], "GRUPO EXTERNO")
        self.assertEqual(info["site_relative_path"], "/sites/MiSitio")
        called_url = mock_get.call_args.args[0]
        self.assertEqual(
            called_url,
            "https://graph.microsoft.com/v1.0/sites/empresa.sharepoint.com:/sites/MiSitio",
        )

    @patch("apps.implementacion_fo.services.sharepoint_mapping_service.requests.get")
    @patch.object(SharePointMappingService, "get_access_token", return_value="tok")
    def test_list_excel_files_filters_temp_files(self, _mock_tok, mock_get):
        resp = MagicMock()
        resp.json.return_value = {
            "value": [
                {"id": "1", "name": "Mapping_Belen.xlsx", "webUrl": "https://x/1"},
                {"id": "2", "name": "~$Mapping_Belen.xlsx", "webUrl": "https://x/2"},
                {"id": "3", "name": "Notas.txt", "webUrl": "https://x/3"},
            ]
        }
        mock_get.return_value = resp

        files = SharePointMappingService.list_excel_files("drive-1")

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["id"], "1")
        self.assertEqual(files[0]["barrio_sugerido"], "BELEN")

    @patch("apps.implementacion_fo.services.sharepoint_mapping_service.time.sleep")
    @patch("apps.implementacion_fo.services.sharepoint_mapping_service.requests.post")
    @patch.object(SharePointMappingService, "get_access_token", return_value="tok")
    def test_append_rows_to_excel_retries_on_lock_423(self, _mock_tok, mock_post, mock_sleep):
        locked_resp = MagicMock(status_code=423)
        ok_resp = MagicMock(status_code=201)
        ok_resp.json.return_value = {"index": 0}
        mock_post.side_effect = [locked_resp, ok_resp]

        res = SharePointMappingService.append_rows_to_excel(
            drive_id="d1",
            item_id="i1",
            table_name="Tabla1",
            rows_values=[["A", "B"]],
        )

        self.assertEqual(res, {"index": 0})
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once()

    def test_format_predio_for_list_maps_columns_and_types(self):
        predio = SimpleNamespace(
            id=10,
            lote_amp="102A",
            nombre_conjunto="TORRE CENTRAL",
            nombre_calle="CL 10",
            placa_unidad="20-30",
            num_casas=0,
            num_apartamentos=12,
            num_locales=2,
            num_pisos=4,
            barrio="BELEN",
            interior="1",
            distribucion="VERTICAL",
            latitud="6.250000",
            longitud="-75.560000",
            calle_alterna_2="",
            placa_alterna_2="",
            calle_alterna_3="",
            placa_alterna_3="",
        )
        col_map = {
            "AMP": ("Title", False),
            "NOMBRE CONJUNTO": ("field_1", False),
            "APTOS": ("field_2", True),
            "CORDX": ("field_3", True),
        }

        payload = SharePointMappingService.format_predio_for_list(predio, col_map)

        self.assertEqual(payload["Title"], "102A")
        self.assertEqual(payload["field_1"], "TORRE CENTRAL")
        self.assertEqual(payload["field_2"], 12.0)
        self.assertAlmostEqual(payload["field_3"], 6.25)

    @patch.object(SharePointMappingService, "append_item_to_list", return_value={"id": "sp-99"})
    @patch.object(SharePointMappingService, "get_list_columns", return_value={"AMP": ("Title", False)})
    @patch("apps.implementacion_fo.services.sharepoint_mapping_service.SharePointMappingConfig.objects")
    def test_sync_predio_to_sharepoint_list_marks_synced(self, mock_cfg_qs, _mock_cols, _mock_append):
        mock_cfg_qs.filter.return_value.first.return_value = SimpleNamespace(
            tipo_destino="LISTA",
            sp_list_id="list-1",
        )
        predio = MagicMock(
            id=5,
            barrio="belen",
            lote_amp="AMP1",
            nombre_conjunto="",
            nombre_calle="CL 1",
            placa_unidad="2-3",
            num_casas=1,
            num_apartamentos=0,
            num_locales=0,
            num_pisos=1,
            interior="",
            distribucion="",
            latitud=None,
            longitud=None,
            calle_alterna_2="",
            placa_alterna_2="",
            calle_alterna_3="",
            placa_alterna_3="",
        )

        res = SharePointMappingService.sync_predio_to_sharepoint(predio)

        self.assertTrue(res["success"])
        self.assertEqual(res["sp_item_id"], "sp-99")
        self.assertTrue(predio.sp_synced)
        self.assertEqual(predio.sp_sync_error, "")
        predio.save.assert_called_once()
