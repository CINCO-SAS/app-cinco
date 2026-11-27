from unittest import TestCase
from unittest.mock import MagicMock, patch
import requests
from rest_framework import status
from rest_framework.exceptions import ValidationError
from apps.common.exceptions import custom_exception_handler
from apps.common.services import SharePointGraphClient


class CustomExceptionHandlerTests(TestCase):
    def test_maneja_excepcion_estandar_de_drf(self):
        exc = ValidationError({"campo": ["Este campo es obligatorio."]})
        context = {"view": None}
        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campo", response.data)

    def test_captura_excepcion_no_controlada_y_retorna_json_500(self):
        exc = ValueError("Error inesperado en lógica de negocio")
        context = {"view": None}
        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("detail", response.data)
        self.assertNotIn("<html", str(response.data))
        self.assertEqual(
            response.data["detail"],
            "Ocurrió un error interno en el servidor. Por favor, intenta nuevamente más tarde.",
        )


class SharePointGraphClientTests(TestCase):
    def setUp(self):
        SharePointGraphClient.reset_msal_client()

    def tearDown(self):
        SharePointGraphClient.reset_msal_client()

    def test_encode_sharing_url_format(self):
        token = SharePointGraphClient.encode_sharing_url("https://example.sharepoint.com/a")
        self.assertTrue(token.startswith("u!"))
        self.assertNotIn("=", token)

    @patch("apps.common.services.sharepoint_graph_client.time.sleep")
    @patch("apps.common.services.sharepoint_graph_client.requests.request")
    @patch.object(SharePointGraphClient, "get_access_token", return_value="tok")
    def test_request_retries_on_429_and_503(self, _mock_tok, mock_req, mock_sleep):
        r_429 = MagicMock(status_code=429, headers={"Retry-After": "1"})
        r_503 = MagicMock(status_code=503, headers={})
        r_ok = MagicMock(status_code=200, headers={})
        r_ok.raise_for_status.return_value = None
        mock_req.side_effect = [r_429, r_503, r_ok]

        resp = SharePointGraphClient.request("GET", "/sites/root", max_retries=3)

        self.assertIs(resp, r_ok)
        self.assertEqual(mock_req.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("apps.common.services.sharepoint_graph_client.time.sleep")
    @patch("apps.common.services.sharepoint_graph_client.requests.request")
    @patch.object(SharePointGraphClient, "get_access_token", return_value="tok")
    def test_request_raises_404_without_retrying(self, _mock_tok, mock_req, mock_sleep):
        r_404 = MagicMock(status_code=404, headers={})
        r_404.raise_for_status.side_effect = requests.HTTPError("404", response=r_404)
        mock_req.return_value = r_404

        with self.assertRaises(requests.HTTPError):
            SharePointGraphClient.request("GET", "/drives/d/items/missing", max_retries=3)

        mock_req.assert_called_once()
        mock_sleep.assert_not_called()

    @patch.object(SharePointGraphClient, "request")
    def test_resolve_drive_item_by_url_extracts_ids(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "item-123",
            "name": "BACK_MTTO_INFO_2026.xlsx",
            "size": 16397230,
            "lastModifiedDateTime": "2026-11-26T20:58:24Z",
            "webUrl": "https://disenocinco.sharepoint.com/...",
            "parentReference": {"driveId": "drive-456"},
        }
        mock_request.return_value = mock_resp

        item = SharePointGraphClient.resolve_drive_item_by_url("https://disenocinco.sharepoint.com/file")

        self.assertEqual(item["drive_id"], "drive-456")
        self.assertEqual(item["item_id"], "item-123")
        self.assertEqual(item["name"], "BACK_MTTO_INFO_2026.xlsx")
