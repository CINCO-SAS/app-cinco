import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rest_framework import status
from rest_framework.exceptions import ValidationError
from apps.common.exceptions import custom_exception_handler
from apps.common import festivos


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


class FestivosAlgoritmoYCatalogoTests(TestCase):
    """`apps.common.festivos` = 18 estatutarios (algoritmo) ∪ catálogo JSON.

    El catálogo es la fuente editable: agregar una fecha al JSON la vuelve
    festivo sin tocar Python ni migraciones.
    """

    def test_algoritmo_sigue_dando_18_estatutarios(self):
        # El contrato de `calcular_festivos_colombia` NO cambia: 18, sin extras.
        self.assertEqual(len(festivos.calcular_festivos_colombia(2026)), 18)
        self.assertNotIn(date(2026, 7, 13),
                         [f for f, _ in festivos.calcular_festivos_colombia(2026)])

    def test_catalogo_cubierto_es_superconjunto_del_algoritmo(self):
        # El JSON confirma el algoritmo: los 18 estatutarios están en el JSON.
        for anio in (2022, 2023, 2024, 2025, 2026, 2027):
            en_json = {fecha for fecha, _ in festivos.festivos_del_anio(anio)}
            en_algoritmo = {fecha for fecha, _ in
                            festivos.calcular_festivos_colombia(anio)}
            self.assertTrue(en_algoritmo <= en_json,
                            f"año {anio}: el JSON no cubre todos los estatutarios")

    def test_feriado_decretado_del_json_es_festivo(self):
        # Extra del catálogo que el algoritmo no calcula (2026-07-13).
        self.assertTrue(festivos.es_festivo("2026-07-13"))
        self.assertEqual(
            festivos.festivo_nombre("2026-07-13"), "Día de la Virgen de Chiquinquirá"
        )
        self.assertFalse(festivos.es_dia_habil("2026-07-13"))  # lunes, pero festivo

    def test_nombre_del_algoritmo_gana_sobre_el_del_json(self):
        # El JSON dice "Batalla de Boyaca" / "Día de Navidad"; el algoritmo
        # tiene los nombres dorados ya testeados y manda ese.
        self.assertEqual(festivos.festivo_nombre("2026-08-07"), "Batalla de Boyacá")
        self.assertEqual(festivos.festivo_nombre("2026-12-25"), "Navidad")

    def test_festivos_del_anio_es_union_ordenada(self):
        self.assertEqual(len(festivos.festivos_del_anio(2026)), 19)   # 18 + extra
        self.assertEqual(len(festivos.festivos_del_anio(2024)), 18)   # sin extras
        fechas = [f for f, _ in festivos.festivos_del_anio(2026)]
        self.assertEqual(fechas, sorted(fechas))

    def test_anio_fuera_del_rango_del_json_lo_resuelve_el_algoritmo(self):
        # El JSON cubre 2022–2030; 2035 (y cualquier otro) va 100% algoritmo.
        self.assertTrue(festivos.es_festivo("2035-01-01"))
        self.assertEqual(len(festivos.festivos_del_anio(2035)), 18)
        self.assertTrue(festivos.es_dia_habil("2035-01-02"))


class AgregarFestivoViaJsonTests(TestCase):
    """Agregar un festivo = editar el JSON + `recargar_catalogo()` (sin código)."""

    def setUp(self):
        self.addCleanup(festivos.recargar_catalogo)  # siempre restaura el real

    def _catalogo_temp(self, entradas):
        directorio = TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        ruta = Path(directorio.name) / "festivos_colombia.json"
        ruta.write_text(json.dumps(entradas), encoding="utf-8")
        return ruta

    def test_agrega_festivo_nuevo_lo_vuelve_no_habil(self):
        ruta = self._catalogo_temp({
            "2026": {"07": [{"fecha": "2026-07-27", "motivo": "Festivo decretado nuevo"}]},
        })
        festivos.recargar_catalogo(ruta)

        self.assertTrue(festivos.es_festivo("2026-07-27"))
        self.assertEqual(festivos.festivo_nombre("2026-07-27"), "Festivo decretado nuevo")
        self.assertFalse(festivos.es_dia_habil("2026-07-27"))  # lunes, ahora festivo

        # Al restaurar el catálogo real, la fecha deja de ser festivo.
        festivos.recargar_catalogo()
        self.assertFalse(festivos.es_festivo("2026-07-27"))

    def test_reemplazar_catalogo_no_quita_los_estatutarios(self):
        # Un JSON (casi) vacío no apaga la Ley Emiliani: sigue mandando el algoritmo.
        festivos.recargar_catalogo(self._catalogo_temp({}))

        self.assertFalse(festivos.es_festivo("2026-07-13"))       # extra: fuera
        self.assertTrue(festivos.es_festivo("2026-10-12"))        # estatutario: dentro
        self.assertEqual(festivos.festivo_nombre("2026-07-20"), "Día de la Independencia")
        self.assertEqual(len(festivos.calcular_festivos_colombia(2026)), 18)

    def test_json_inexistente_o_malformado_no_rompe(self):
        self.assertEqual(festivos.recargar_catalogo("/no/existe/festivos.json"), {})
        self.assertFalse(festivos.es_festivo("2026-07-13"))
        self.assertTrue(festivos.es_festivo("2026-10-12"))  # el algoritmo sigue vivo

        ruta = self._catalogo_temp({})
        ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(festivos.recargar_catalogo(ruta), {})
        self.assertTrue(festivos.es_festivo("2026-12-25"))

    def test_import_de_transporte_apunta_al_modulo_compartido(self):
        # El shim de transporte re-exporta exactamente esta misma lógica.
        from apps.transporte.services import calendario as calendario_transporte

        self.assertIs(calendario_transporte.es_festivo, festivos.es_festivo)
        self.assertTrue(calendario_transporte.es_festivo("2026-07-13"))
