"""
Tests del módulo Transporte.

Ejecución (aislada de otros módulos; SQLite en memoria, sin MySQL):
    python backend/manage.py test apps.transporte --settings=config.settings_test_transporte
"""
import io
import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import qrcode
from PIL import Image
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.empleados.models import Empleado
from apps.operaciones.models import Actividad, Agenda

from .etl import convertidores as cv
from .etl import normalizadores as nz
from .models import (
    AuditoriaLog,
    Conductor,
    ConsecutivoMensual,
    EstadoSalida,
    FechaLimiteCierre,
    JefeValidador,
    Novedad,
    PagoVehiculoMensual,
    ReporteFotoImagen,
    ReporteFotograficoVehiculo,
    Salida,
    SalidaHistorial,
    TipoNovedad,
    TipoPago,
    TipoVehiculo,
    ValidacionSalida,
    Vehiculo,
)
from .serializers.jefe_serializer import JefeValidadorSerializer
from .services import calendario
from .services import (
    ConductorService,
    FlotaService,
    LiquidacionService,
    ParametrosService,
    ReporteFotograficoService,
    SalidaService,
    ValidacionService,
)
from .services.flota_service import COLUMNAS_CSV_BANCARIOS
from .services.reporte_fotografico_service import MAX_BYTES_IMAGEN
from .services.periodos import restar_meses
from .services.vigencia import estado_vigencia


def _asegurar_tabla_empleados():
    """
    Empleado es managed=False (cinco_base_de_personal) y en tests el router
    está desactivado, así que la tabla no existe en la BD por defecto: se crea
    UNA vez desde este archivo (andamiaje solo de tests de transporte; no se
    toca el módulo empleados). Se invoca en setUpClass ANTES de
    super().setUpClass() para quedar fuera de las transacciones de TestCase.
    """
    if "cinco_base_de_personal" not in connection.introspection.table_names():
        with connection.schema_editor() as editor:
            editor.create_model(Empleado)


class EdadDerivadaTests(SimpleTestCase):
    """§5.4: la edad se deriva de fecha_nacimiento y NUNCA se persiste."""

    def test_edad_sin_fecha_es_none(self):
        self.assertIsNone(ConductorService.calcular_edad(None))

    def test_edad_antes_del_cumpleanos(self):
        self.assertEqual(
            ConductorService.calcular_edad(date(1990, 12, 31), hoy=date(2026, 1, 1)),
            35,
        )

    def test_edad_despues_del_cumpleanos(self):
        self.assertEqual(
            ConductorService.calcular_edad(date(1990, 1, 1), hoy=date(2026, 1, 1)),
            36,
        )


class SemaforoLicenciaTests(SimpleTestCase):
    """§5.3/§5.4: semáforo en servidor (>60 verde, 31–60 naranja, ≤30 rojo)."""

    hoy = date(2026, 10, 14)

    def test_sin_fecha(self):
        self.assertEqual(ConductorService.estado_licencia(None, self.hoy), "SIN_REGISTRO")

    def test_vigente(self):
        self.assertEqual(
            ConductorService.estado_licencia(date(2026, 12, 31), self.hoy), "VIGENTE"
        )

    def test_por_vencer(self):
        # 47 días restantes (31–60 → naranja).
        self.assertEqual(
            ConductorService.estado_licencia(date(2026, 11, 30), self.hoy), "POR_VENCER"
        )

    def test_vencida(self):
        self.assertEqual(
            ConductorService.estado_licencia(date(2026, 10, 1), self.hoy), "VENCIDA"
        )


class AlcanceFlotaTests(SimpleTestCase):
    """D-A13: exclusión dura de motos del catálogo de flota."""

    def test_tipos_vehiculo_no_incluyen_moto(self):
        self.assertNotIn("MOTO", TipoVehiculo.values)


class NovedadTotalTests(SimpleTestCase):
    """§5.1 calcular_pago: total = valor_dia ± novedad, en servidor."""

    def _salida_con_novedad(self, valor_dia, tipo, valor):
        salida = Salida(valor_dia=valor_dia)
        salida.novedad = Novedad(tipo=tipo, valor=valor)
        return salida

    def test_sin_novedad_devuelve_valor_dia(self):
        salida = Salida(valor_dia=100000)
        self.assertEqual(salida.total_a_pagar, 100000)

    def test_adicional_suma(self):
        salida = self._salida_con_novedad(100000, "ADICIONAL", 5000)
        self.assertEqual(salida.total_a_pagar, 105000)

    def test_descuento_rest(self):
        salida = self._salida_con_novedad(100000, "DESCUENTO", 5000)
        self.assertEqual(salida.total_a_pagar, 95000)


class ConductorCRUDTests(TestCase):
    """Reglas de escritura del catálogo (§5.4) contra BD en memoria."""

    def _datos(self, **extra):
        datos = {
            "cedula": "1234567890",
            "nombre_completo": "JUAN PRUEBA",
            "celular": "3001112233",
            "fecha_ingreso": date(2026, 1, 1),
            "fecha_nacimiento": date(1990, 5, 10),
            "tipo_vinculacion": "EXTERNO",
            "licencia_categoria": "C1",
            "licencia_vencimiento": date(2027, 6, 30),
        }
        datos.update(extra)
        return datos

    def test_crear_conductor_ok(self):
        conductor = ConductorService.crear(self._datos(), actor=None)
        self.assertTrue(Conductor.objects.filter(pk=conductor.pk).exists())
        self.assertTrue(conductor.activo)

    def test_cedula_duplicada_rechazada(self):
        ConductorService.crear(self._datos(), actor=None)
        with self.assertRaisesMessage(ValueError, "Ya existe un conductor"):
            ConductorService.crear(self._datos(nombre_completo="OTRO"), actor=None)

    def test_sin_fecha_ingreso_rechazada(self):
        with self.assertRaisesMessage(ValueError, "fecha de ingreso"):
            ConductorService.crear(self._datos(fecha_ingreso=None), actor=None)

    def test_nacimiento_posterior_a_ingreso_rechazado(self):
        with self.assertRaisesMessage(ValueError, "nacimiento"):
            ConductorService.crear(
                self._datos(fecha_nacimiento=date(2026, 6, 1)), actor=None
            )

    def test_inactivar_exige_fecha_egreso(self):
        conductor = ConductorService.crear(self._datos(), actor=None)
        with self.assertRaisesMessage(ValueError, "fecha de egreso"):
            ConductorService.inactivar(conductor.pk, None, actor=None)

    def test_inactivar_registra_baja_logica(self):
        conductor = ConductorService.crear(self._datos(), actor=None)
        resultado = ConductorService.inactivar(
            conductor.pk, date(2026, 10, 1), actor=None
        )
        self.assertFalse(resultado.activo)
        self.assertEqual(resultado.fecha_egreso, date(2026, 10, 1))
        # Nunca borrado físico (las salidas lo referencian con PROTECT).
        self.assertTrue(Conductor.objects.filter(pk=conductor.pk).exists())

    def test_listar_filtro_por_cedula(self):
        ConductorService.crear(self._datos(), actor=None)
        resultados = ConductorService.listar({"cedula": "1234567890"})
        self.assertEqual(resultados.count(), 1)

    def test_listar_filtro_activo_false(self):
        ConductorService.crear(self._datos(), actor=None)
        self.assertEqual(ConductorService.listar({"activo": "false"}).count(), 0)


class EtlNormalizadoresTests(SimpleTestCase):
    """Normalizadores: catálogo D-A6, booleanos SI/NO, fechas cero y
    zona horaria America/Bogota (D-A4). Puros, sin BD."""

    def test_normalizar_estado_minusculas_a_mayusculas(self):
        self.assertEqual(nz.normalizar_estado("reportado"), "REPORTADO")

    def test_normalizar_estado_fuera_de_catalogo_rechaza(self):
        with self.assertRaisesMessage(ValueError, "fuera de catálogo"):
            nz.normalizar_estado("FINALIZADO")

    def test_booleano_si_no(self):
        self.assertTrue(nz.booleano_si_no("SI"))
        self.assertFalse(nz.booleano_si_no("NO"))
        self.assertFalse(nz.booleano_si_no(""))

    def test_fecha_cero_devuelve_none(self):
        self.assertIsNone(nz.fecha_legacy("0000-00-00"))

    def test_datetime_legacy_aware_en_bogota(self):
        resultado = nz.datetime_legacy("2026-09-10 08:30:00")
        self.assertIsNotNone(resultado.tzinfo)
        self.assertEqual(str(resultado.tzinfo), "America/Bogota")
        # 08:30 en Bogotá (UTC-5) es 13:30 UTC.
        self.assertEqual(
            resultado.astimezone(dt_timezone.utc).hour, 13
        )


class EtlConvertidoresTests(SimpleTestCase):
    """Convertidores: desempaquetado del JSON `datos` (§7.2) sin BD."""

    def test_convertir_vehiculo_desempaqueta_bancarios_y_pagos(self):
        fila = {
            "placa": "abc123",
            "tipo": "camioneta",
            "tipo_contrato": "externo",
            "tipo_vinculacion": "externo",
            "marca": "CHEVROLET",
            "modelo": "2021",
            "valor_dia": "450000",
            "propietario": "TRANSPORTE NORTE SAS",
            "cedula": "900123456",
            "cedual_conductor": "1032456789",
            "estado": "ACTIVO",
            "datos": json.dumps({
                "bancarios": [{"cedula": "900123456", "nombre": "NORTE",
                               "banco": "DAVIVIENDA", "tipo_cuenta": "AHORROS",
                               "numero_cuenta": "123"}],
                "pago_mensual": [{"mes": 9, "yyyy": 2026}],
                "pronto_pago": [{"mes": 8, "yyyy": 2026}],
            }),
        }
        datos = cv.convertir_vehiculo(fila)
        self.assertEqual(datos["placa"], "ABC123")  # mayúsculas D-A6
        self.assertEqual(datos["tipo_vehiculo"], "CAMIONETA")
        self.assertEqual(len(datos["_bancarios"]), 1)
        self.assertEqual(len(datos["_pagos"]), 2)
        tipos = {p["tipo"] for p in datos["_pagos"]}
        self.assertEqual(tipos, {TipoPago.MENSUAL, TipoPago.PRONTO_PAGO})

    def test_convertir_conductor_fecha_cero_devuelve_none(self):
        fila = {
            "cedula": "123", "nombre_conductor": "X", "celular_conductor": "1",
            "licencia": "C1", "fecha_ingreso": "2021-01-01",
            "fecha_egreso": "0000-00-00", "estado": "ACTIVO",
        }
        datos = cv.convertir_conductor(fila)
        self.assertIsNone(datos["fecha_egreso"])

    def test_convertir_jefe_anida_carpetas(self):
        fila = {"datos": json.dumps([{
            "cedula_jefe": "1050987654", "estado": "ACTIVO",
            "areas": ["OPERACIONES"],
            "carpetas": {"OPERACIONES": ["TRANSPORTE"]},
        }])}
        jefes = cv.convertir_jefes_fila(fila)
        self.assertEqual(len(jefes), 1)
        self.assertEqual(
            jefes[0]["carpetas_por_area"], {"OPERACIONES": ["TRANSPORTE"]}
        )

    def test_convertir_fecha_limite_cero_rechaza(self):
        # La fila queda como "no convertible" (reporte) y NO descuadra la
        # conciliación: la rechaza el convertidor, no el service.
        with self.assertRaisesMessage(ValueError, "fecha cero"):
            cv.convertir_fecha_limite(
                {"mes": "8", "anio": "2026", "fecha_limite": "0000-00-00"}
            )

    def test_convertir_fecha_limite_ok(self):
        datos = cv.convertir_fecha_limite(
            {"mes": "9", "anio": "2026", "fecha_limite": "2026-10-05"}
        )
        self.assertEqual(datos["mes"], 9)
        self.assertEqual(datos["fecha_limite"], date(2026, 10, 5))


class EtlComandoTests(TestCase):
    """`manage.py migrate_transporte_legacy` contra fixtures locales."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        # Los jefes validadores y los técnicos de salidas referencian
        # empleados por cédula (resolución en dos pasos, D-A10): se crean
        # los que la muestra usa para que la corrida no pierda filas.
        for cedula in (
            "1050987654", "1098765432", "1011223344", "1099887766",
            "808765432",
        ):
            Empleado.objects.create(
                cedula=cedula,
                codigo_sap=f"SAP-{cedula}",
                nombre="EMPLEADO",
                apellido=f"ETL {cedula[-4:]}",
                password="",
            )

    def _ruta_muestra(self):
        return Path(__file__).resolve().parent / "etl" / "muestras"

    def _ejecutar(self, *args):
        salida = io.StringIO()
        call_command(
            "migrate_transporte_legacy",
            "--fuente", str(self._ruta_muestra()), *args,
            stdout=salida,
        )
        return salida.getvalue()

    def test_dry_run_no_escribe(self):
        salida = self._ejecutar("--dry-run")
        self.assertIn("DRY-RUN", salida)
        self.assertEqual(Conductor.objects.count(), 0)
        self.assertEqual(Vehiculo.objects.count(), 0)
        self.assertEqual(Salida.objects.count(), 0)

    def test_carga_completa(self):
        self._ejecutar()
        self.assertEqual(Conductor.objects.count(), 3)
        self.assertEqual(Vehiculo.objects.count(), 3)
        self.assertEqual(Salida.objects.count(), 3)
        self.assertEqual(JefeValidador.objects.count(), 4)
        # 3 leídas − 1 con fecha cero (fila no convertible) = 2.
        self.assertEqual(FechaLimiteCierre.objects.count(), 2)

    def test_carga_resuelve_fk_por_cedula_y_placa(self):
        self._ejecutar()
        vehiculo = Vehiculo.objects.get(placa="ABC123")
        # conductor_habitual resuelto por cédula (cédual_conductor).
        self.assertEqual(vehiculo.conductor_habitual.cedula, "1032456789")
        salida = Salida.objects.get(vehiculo__placa="ABC123")
        self.assertEqual(salida.conductor.cedula, "1032456789")

    def test_carga_normaliza_estado_minuscula(self):
        self._ejecutar()
        salida = Salida.objects.get(vehiculo__placa="ABC123")
        self.assertEqual(salida.estado, "APROBADO")

    def test_carga_convierte_booleanos_si_no(self):
        self._ejecutar()
        vehiculo = Vehiculo.objects.get(placa="ABC123")
        self.assertTrue(vehiculo.cajon)
        self.assertFalse(vehiculo.logos)

    def test_carga_fecha_cero_a_none(self):
        self._ejecutar()
        vehiculo = Vehiculo.objects.get(placa="DEF456")
        self.assertIsNone(vehiculo.fecha_egreso)

    def test_carga_persiste_pagos_y_bancarios(self):
        self._ejecutar()
        vehiculo = Vehiculo.objects.get(placa="ABC123")
        self.assertEqual(vehiculo.datos_bancarios.count(), 2)
        self.assertEqual(vehiculo.pagos.count(), 3)

    def test_carga_novedad_y_historial(self):
        self._ejecutar()
        salida = Salida.objects.get(vehiculo__placa="ABC123")
        self.assertEqual(salida.novedad.tipo, TipoNovedad.ADICIONAL)
        self.assertEqual(salida.historial.count(), 2)

    def test_carga_datetime_a_utc(self):
        self._ejecutar()
        historial = Salida.objects.get(
            vehiculo__placa="ABC123"
        ).historial.order_by("fecha_cambio").first()
        # 08:30 Bogotá → 13:30 UTC (D-A4).
        self.assertEqual(historial.fecha_cambio.hour, 13)

    def test_conciliacion_cero(self):
        salida = self._ejecutar()
        # El DoD de C3: conteo origen = destino en TODAS las entidades.
        self.assertEqual(salida.count("conciliación OK"), 5)
        self.assertNotIn("DISCREPANCIA", salida)

    def test_reporte_filas_no_convertibles(self):
        salida = self._ejecutar()
        # La fila 3 de cierres (fecha 0000-00-00) se reporta, no aborta.
        self.assertIn("errores=1", salida)
        self.assertIn("fecha cero", salida)


class CalendarioTests(SimpleTestCase):
    """Port de `frontend/src/utils/festivos/festivosColombia.ts`.

    Valores dorados = test TS (`festivosColombia.test.ts`); la semántica
    de sábado por defecto (hábil) replica el frontend y la CR-9 legacy
    la desactiva con `sabado_habil=False` en su punto de uso.
    """

    def test_calcula_18_festivos_por_anio(self):
        self.assertEqual(len(calendario.calcular_festivos_colombia(2026)), 18)

    def test_fijos_y_nombre(self):
        self.assertEqual(calendario.festivo_nombre("2026-01-01"), "Año Nuevo")
        self.assertEqual(
            calendario.festivo_nombre(date(2026, 7, 20)), "Día de la Independencia"
        )
        self.assertEqual(
            calendario.festivo_nombre("2026-08-07"), "Batalla de Boyacá"
        )
        self.assertEqual(calendario.festivo_nombre("2026-12-25"), "Navidad")

    def test_ley_emiliani_traslada_al_lunes(self):
        # 6 de enero 2026 cae martes → lunes 12 (dorado del test TS).
        self.assertEqual(
            calendario.festivo_nombre("2026-01-12"), "Día de los Reyes Magos"
        )
        self.assertFalse(calendario.es_festivo("2026-01-06"))

    def test_relativos_a_pascua(self):
        # Pascua 2026 = 5 de abril (dorados del test TS).
        self.assertEqual(calendario.festivo_nombre("2026-04-02"), "Jueves Santo")
        self.assertEqual(calendario.festivo_nombre("2026-04-03"), "Viernes Santo")
        self.assertTrue(calendario.es_festivo("2026-05-18"))   # Ascensión
        self.assertTrue(calendario.es_festivo("2026-06-08"))   # Corpus Christi
        self.assertTrue(calendario.es_festivo("2026-06-15"))   # Sagrado Corazón

    def test_dia_habil_domingo_y_festivo_no(self):
        self.assertFalse(calendario.es_dia_habil("2026-10-04"))  # domingo
        self.assertFalse(calendario.es_dia_habil("2026-10-12"))  # festivo
        self.assertTrue(calendario.es_dia_habil("2026-10-13"))   # martes

    def test_sabado_habil_como_el_frontend(self):
        # Paridad con el archivo TS: hábil por defecto, configurable.
        self.assertTrue(calendario.es_dia_habil("2026-10-10"))
        self.assertFalse(
            calendario.es_dia_habil("2026-10-10", sabado_habil=False)
        )

    def test_sumar_dias_habiles_dorados_ts(self):
        self.assertEqual(
            calendario.sumar_dias_habiles("2026-10-09", 1), date(2026, 10, 10)
        )
        # Salta domingo 11 + festivo 12 → lunes 13.
        self.assertEqual(
            calendario.sumar_dias_habiles("2026-10-10", 1), date(2026, 10, 13)
        )

    def test_restar_dias_habiles_paridad_legacy(self):
        # CR-9 legacy (base_salida_transporte.php 77–96): sábados NO cuentan.
        # Desde martes 13: viernes 9 (1), jueves 8 (2) → 8 de octubre.
        self.assertEqual(
            calendario.restar_dias_habiles(
                "2026-10-13", 2, sabado_habil=False
            ),
            date(2026, 10, 8),
        )
        # Con sábado hábil la ventana es más corta: viernes 9.
        self.assertEqual(
            calendario.restar_dias_habiles("2026-10-13", 2),
            date(2026, 10, 9),
        )


class SemaforoCompartidoTests(SimpleTestCase):
    """La misma regla (§5.3/§5.4) gobierna SOAT, CDA y licencia."""

    hoy = date(2026, 10, 14)

    def test_misma_regla_para_soat_y_licencia(self):
        por_vencer = date(2026, 11, 30)  # 47 días
        self.assertEqual(estado_vigencia(por_vencer, self.hoy), "POR_VENCER")

    def test_sin_fecha(self):
        self.assertEqual(estado_vigencia(None, self.hoy), "SIN_REGISTRO")

    def test_vencida_incluye_vencidas(self):
        self.assertEqual(estado_vigencia(date(2020, 1, 1), self.hoy), "VENCIDA")


class FlotaCRUDTests(TestCase):
    """§5.3: ABM con placa única y semáforo en servidor."""

    def _datos(self, **extra):
        datos = {
            "placa": "ABC123",
            "tipo_vehiculo": "CAMIONETA",
            "marca": "MAZDA",
            "referencia": "CX5",
            "modelo_anio": 2022,
            "tipo_contrato": "PROPIO",
            "nombre_propietario": "CINCO SAS",
            "cedula_propietario": "900111222",
            "valor_dia_base": 85000,
            "fecha_soat": date(2027, 1, 1),   # 79 días → VIGENTE
            "fecha_cda": date(2026, 11, 15),  # 32 días → POR_VENCER
        }
        datos.update(extra)
        return datos

    def test_crear_vehiculo_ok(self):
        vehiculo = FlotaService.crear(self._datos(), actor=None)
        self.assertEqual(vehiculo.placa, "ABC123")
        self.assertTrue(vehiculo.activo)

    def test_placa_se_normaliza_a_mayusculas(self):
        vehiculo = FlotaService.crear(self._datos(placa=" abc123 "), actor=None)
        self.assertEqual(vehiculo.placa, "ABC123")

    def test_placa_duplicada_rechazada(self):
        FlotaService.crear(self._datos(), actor=None)
        with self.assertRaisesMessage(ValueError, "Ya existe un vehículo"):
            FlotaService.crear(self._datos(marca="OTRA"), actor=None)

    def test_placa_obligatoria(self):
        with self.assertRaisesMessage(ValueError, "placa es obligatoria"):
            FlotaService.crear(self._datos(placa="  "), actor=None)

    def test_motos_fuera_de_alcance(self):
        """D-A13: el catálogo no admite motos."""
        with self.assertRaisesMessage(ValueError, "no es un valor válido"):
            FlotaService.crear(self._datos(tipo_vehiculo="MOTO"), actor=None)

    def test_inactivar_es_logico(self):
        vehiculo = FlotaService.crear(self._datos(), actor=None)
        FlotaService.inactivar(vehiculo.pk, actor=None)
        self.assertTrue(Vehiculo.objects.filter(pk=vehiculo.pk, activo=False).exists())

    def test_semario_soat_calculado_en_servidor(self):
        vehiculo = FlotaService.crear(self._datos(), actor=None)
        ficha = FlotaService.ficha_documental(vehiculo.pk, hoy=date(2026, 10, 14))
        self.assertEqual(ficha["semaforo"]["soat"], "VIGENTE")      # 79 días
        self.assertEqual(ficha["semaforo"]["cda"], "POR_VENCER")     # 32 días

    def test_semario_vencido(self):
        vehiculo = FlotaService.crear(
            self._datos(fecha_soat=date(2026, 10, 1)), actor=None
        )
        ficha = FlotaService.ficha_documental(vehiculo.pk, hoy=date(2026, 10, 14))
        self.assertEqual(ficha["semaforo"]["soat"], "VENCIDA")


class DocumentoVehiculoTests(TestCase):
    """§5.3: documentos validados por tipo/tamaño, upsert por tipo."""

    # Los archivos de test van a un temporal, nunca al árbol del repo.
    MEDIA_ROOT_OVERRIDE = override_settings(
        MEDIA_ROOT=tempfile.mkdtemp(prefix="transporte_test_media_")
    )

    def setUp(self):
        self.MEDIA_ROOT_OVERRIDE.enable()
        self.addCleanup(self.MEDIA_ROOT_OVERRIDE.disable)

    def _vehiculo(self):
        return FlotaService.crear(
            {
                "placa": "XYZ789",
                "tipo_vehiculo": "FURGON",
                "marca": "RENAULT",
                "modelo_anio": 2021,
                "tipo_contrato": "EXTERNO",
                "nombre_propietario": "TERCERO",
                "cedula_propietario": "800999888",
                "fecha_ingreso": date(2026, 1, 1),
            },
            actor=None,
        )

    def _archivo(self, nombre="soat.jpg", contenido=b"img", tipo="image/jpeg"):
        return SimpleUploadedFile(nombre, contenido, content_type=tipo)

    def test_subir_documento_ok(self):
        vehiculo = self._vehiculo()
        doc = FlotaService.subir_documento(
            vehiculo.pk, "SOAT", self._archivo(), date(2027, 1, 1), actor=None
        )
        self.assertEqual(doc.tipo, "SOAT")
        self.assertTrue(vehiculo.documentos.exists())

    def test_tipo_archivo_no_permitido(self):
        vehiculo = self._vehiculo()
        with self.assertRaisesMessage(ValueError, "no permitido"):
            FlotaService.subir_documento(
                vehiculo.pk,
                "SOAT",
                self._archivo(nombre="virus.exe", tipo="application/octet-stream"),
                None,
                actor=None,
            )

    def test_archivo_demasiado_grande(self):
        vehiculo = self._vehiculo()
        grande = SimpleUploadedFile(
            "gigante.jpg", b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg"
        )
        with self.assertRaisesMessage(ValueError, "tamaño máximo"):
            FlotaService.subir_documento(
                vehiculo.pk, "SOAT", grande, None, actor=None
            )

    def test_upsert_reemplaza_documento_existente(self):
        vehiculo = self._vehiculo()
        FlotaService.subir_documento(
            vehiculo.pk, "SOAT", self._archivo("a.jpg"), date(2027, 1, 1), actor=None
        )
        FlotaService.subir_documento(
            vehiculo.pk, "SOAT", self._archivo("b.jpg"), date(2028, 1, 1), actor=None
        )
        self.assertEqual(vehiculo.documentos.filter(tipo="SOAT").count(), 1)
        doc = vehiculo.documentos.get(tipo="SOAT")
        self.assertEqual(doc.fecha_vencimiento, date(2028, 1, 1))


class ImportBancariosCsvTests(TestCase):
    """CR-13 / §5.3: separador autodetectado, limpieza regex y upsert por placa."""

    def _vehiculo(self, placa="ABC123"):
        return FlotaService.crear(
            {
                "placa": placa,
                "tipo_vehiculo": "CAMIONETA",
                "marca": "MAZDA",
                "modelo_anio": 2022,
                "tipo_contrato": "PROPIO",
                "nombre_propietario": "CINCO SAS",
                "cedula_propietario": "900111222",
                "fecha_ingreso": date(2026, 1, 1),
            },
            actor=None,
        )

    def _csv(self, contenido, nombre="bancos.csv"):
        return SimpleUploadedFile(
            nombre, contenido.encode("utf-8"), content_type="text/csv"
        )

    def test_orden_columnas_del_legacy(self):
        """Fija el contrato CSV → modelo de CR-13 (base_transportadores.php 605–610)."""
        self.assertEqual(
            COLUMNAS_CSV_BANCARIOS,
            (
                "placa",
                "cedula_titular",
                "nombre_titular",
                "tipo_cuenta",
                "banco",
                "numero_cuenta",
            ),
        )

    def test_separador_punto_y_coma(self):
        self._vehiculo()
        contenido = "placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\nABC123;12345;JUAN;AHORRO;LOJA;001"
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        self.assertEqual(resultado["insertados"], 1)
        self.assertEqual(resultado["actualizados"], 0)
        self.assertEqual(resultado["errores"], [])

    def test_separador_coma(self):
        self._vehiculo()
        contenido = "placa,cedula_banco,nombre,tipo_cuenta,banco,cuenta\nABC123,12345,JUAN,AHORRO,LOJA,001"
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        self.assertEqual(resultado["insertados"], 1)

    def test_limpieza_alfanumerica_y_mayusculas(self):
        """Réplica de limpiarTexto(): sin símbolos ni acentos, en mayúsculas."""
        self.assertEqual(
            FlotaService.limpiar_texto("Banco López! 33-4"), "BANCO LPEZ 334"
        )

    def test_upsert_actualiza_cuenta_existente(self):
        vehiculo = self._vehiculo()
        fila = "ABC123;111;PEDRO;AHORRO;LOJA;001"
        contenido = f"placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\n{fila}"
        FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        contenido2 = f"placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\nABC123;222;PEDRO;CORRIENTE;PRODUBANCO;999"
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido2))

        self.assertEqual(resultado["insertados"], 0)
        self.assertEqual(resultado["actualizados"], 1)
        self.assertEqual(vehiculo.datos_bancarios.filter(activo=True).count(), 1)
        dato = vehiculo.datos_bancarios.get(activo=True)
        self.assertEqual(dato.numero_cuenta, "999")
        self.assertEqual(dato.cedula_titular, "222")

    def test_placa_inexistente_reporta_causa(self):
        contenido = "placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\nNOEX99;1;A;B;C;D"
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        self.assertEqual(resultado["insertados"], 0)
        self.assertEqual(len(resultado["errores"]), 1)
        self.assertIn("NOEX99", resultado["errores"][0]["causa"])
        self.assertEqual(resultado["errores"][0]["fila"], 2)

    def test_placa_de_vehiculo_inactivo_rechazada(self):
        vehiculo = self._vehiculo(placa="INE999")
        FlotaService.inactivar(vehiculo.pk, actor=None)
        contenido = "placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\nINE999;1;A;B;C;D"
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        self.assertEqual(resultado["errores"][0]["fila"], 2)

    def test_campos_vacios_reportados(self):
        self._vehiculo()
        contenido = "placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\nABC123;;JUAN;AHORRO;LOJA;001"
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        self.assertIn("cedula_titular", resultado["errores"][0]["causa"])

    def test_archivo_vacio_rechazado(self):
        with self.assertRaisesMessage(ValueError, "vacío"):
            FlotaService.importar_datos_bancarios_csv(self._csv("cabecera\n"))

    def test_archivo_ausente_rechazado(self):
        with self.assertRaisesMessage(ValueError, "obligatorio"):
            FlotaService.importar_datos_bancarios_csv(None)

    def test_varias_filas_mezcladas(self):
        self._vehiculo("ABC123")
        self._vehiculo("DEF456")
        contenido = (
            "placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\n"
            "ABC123;1;JUAN;AHORRO;LOJA;001\n"
            "NOEX99;1;A;B;C;D\n"
            "DEF456;;MARIA;AHORRO;LOJA;002\n"
            "DEF456;2;MARIA;AHORRO;PRODUBANCO;777\n"
        )
        resultado = FlotaService.importar_datos_bancarios_csv(self._csv(contenido))
        self.assertEqual(resultado["filas"], 4)
        self.assertEqual(resultado["insertados"], 2)  # ABC123 y DEF456 (fila 4)
        self.assertEqual(resultado["actualizados"], 0)
        self.assertEqual(len(resultado["errores"]), 2)  # NOEX99 y fila 3 de DEF456


class QrTests(TestCase):
    """D-A8: el QR se regenera bajo demanda y jamás se persiste."""

    MEDIA_ROOT_OVERRIDE = override_settings(
        MEDIA_ROOT=tempfile.mkdtemp(prefix="transporte_test_qr_")
    )

    def setUp(self):
        self.MEDIA_ROOT_OVERRIDE.enable()
        self.addCleanup(self.MEDIA_ROOT_OVERRIDE.disable)

    def _vehiculo(self, placa="QRS123"):
        return FlotaService.crear(
            {
                "placa": placa,
                "tipo_vehiculo": "CAMIONETA",
                "marca": "MAZDA",
                "modelo_anio": 2022,
                "tipo_contrato": "PROPIO",
                "nombre_propietario": "CINCO SAS",
                "cedula_propietario": "900111222",
                "fecha_ingreso": date(2026, 1, 1),
            },
            actor=None,
        )

    def test_genera_png_valido(self):
        vehiculo = self._vehiculo()
        png = FlotaService.generar_qr(vehiculo.pk)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_es_determinista(self):
        """Regenerable: mismo vehículo → mismos bytes en cada petición."""
        vehiculo = self._vehiculo()
        self.assertEqual(
            FlotaService.generar_qr(vehiculo.pk),
            FlotaService.generar_qr(vehiculo.pk),
        )

    def test_payload_es_la_placa(self):
        vehiculo = self._vehiculo()
        capturados = []
        original = qrcode.QRCode.add_data

        def espia(self, data):
            capturados.append(data)
            return original(self, data)

        with mock.patch.object(qrcode.QRCode, "add_data", espia):
            FlotaService.generar_qr(vehiculo.pk)

        self.assertEqual(capturados, [vehiculo.placa])

    def test_no_persiste_archivos(self):
        vehiculo = self._vehiculo()
        FlotaService.generar_qr(vehiculo.pk)
        self.assertEqual(os.listdir(settings.MEDIA_ROOT), [])

    def test_vehiculo_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe un vehículo"):
            FlotaService.generar_qr(999999)


class CierreTests(TestCase):
    """§5.8 / matriz B2-D2: cierres con unicidad natural (mes, anio)."""

    def _datos(self, **extra):
        datos = {"mes": 9, "anio": 2026, "fecha_limite": date(2026, 10, 5)}
        datos.update(extra)
        return datos

    def test_crear_ok(self):
        cierre = ParametrosService.crear_cierre(self._datos(), actor=None)
        self.assertEqual((cierre.mes, cierre.anio), (9, 2026))

    def test_crear_duplicado_rechazado(self):
        ParametrosService.crear_cierre(self._datos(), actor=None)
        with self.assertRaisesMessage(ValueError, "Ya existe una fecha límite"):
            ParametrosService.crear_cierre(
                self._datos(fecha_limite=date(2026, 10, 7)), actor=None
            )

    def test_mes_fuera_de_rango(self):
        with self.assertRaisesMessage(ValueError, "mes debe estar entre 1 y 12"):
            ParametrosService.crear_cierre(self._datos(mes=13), actor=None)

    def test_mes_no_entero(self):
        with self.assertRaisesMessage(ValueError, "número entero"):
            ParametrosService.crear_cierre(self._datos(mes="sep"), actor=None)

    def test_anio_fuera_de_rango(self):
        with self.assertRaisesMessage(ValueError, "año debe estar entre"):
            ParametrosService.crear_cierre(self._datos(anio=1999), actor=None)

    def test_fecha_limite_obligatoria(self):
        with self.assertRaisesMessage(ValueError, "obligatoria"):
            ParametrosService.crear_cierre(
                self._datos(fecha_limite=None), actor=None
            )

    def test_listar_ordenado_por_fecha_desc(self):
        """Réplica de get_all_fecha: ORDER BY fecha_limite DESC."""
        ParametrosService.crear_cierre(self._datos(), actor=None)
        ParametrosService.crear_cierre(
            self._datos(mes=10, fecha_limite=date(2026, 11, 5)), actor=None
        )
        cierres = ParametrosService.listar_cierres()
        self.assertEqual([c.mes for c in cierres], [10, 9])

    def test_filtros_mes_anio(self):
        ParametrosService.crear_cierre(self._datos(), actor=None)
        ParametrosService.crear_cierre(
            self._datos(mes=10, fecha_limite=date(2026, 11, 5)), actor=None
        )
        cierres = ParametrosService.listar_cierres({"mes": "9", "anio": "2026"})
        self.assertEqual(len(cierres), 1)
        self.assertEqual(cierres[0].mes, 9)

    def test_filtro_mes_invalido(self):
        with self.assertRaisesMessage(ValueError, "número entero"):
            ParametrosService.listar_cierres({"mes": "x"})

    def test_obtener_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe una fecha límite"):
            ParametrosService.obtener_cierre(999999)

    def test_actualizar_parche_conserva_periodo(self):
        cierre = ParametrosService.crear_cierre(self._datos(), actor=None)
        actualizado = ParametrosService.actualizar_cierre(
            cierre.pk, {"fecha_limite": date(2026, 10, 10)}, actor=None
        )
        self.assertEqual(actualizado.fecha_limite, date(2026, 10, 10))
        self.assertEqual(actualizado.mes, 9)  # no tocado por el parche

    def test_actualizar_conflicto_de_periodo(self):
        a = ParametrosService.crear_cierre(self._datos(), actor=None)
        b = ParametrosService.crear_cierre(
            self._datos(mes=10, fecha_limite=date(2026, 11, 5)), actor=None
        )
        self.assertNotEqual(a.pk, b.pk)
        with self.assertRaisesMessage(ValueError, "Ya existe una fecha límite"):
            ParametrosService.actualizar_cierre(b.pk, {"mes": 9}, actor=None)

    def test_eliminar(self):
        cierre = ParametrosService.crear_cierre(self._datos(), actor=None)
        ParametrosService.eliminar_cierre(cierre.pk)
        self.assertFalse(
            FechaLimiteCierre.objects.filter(pk=cierre.pk).exists()
        )

    def test_eliminar_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe una fecha límite"):
            ParametrosService.eliminar_cierre(999999)


class JefeValidadorTests(TestCase):
    """§5.8 / D1: jefes validadores (mapeo del JSON data_jefes legacy)."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()  # DDL antes de las transacciones
        super().setUpClass()

    def _empleado(self, cedula="1000756621"):
        return Empleado.objects.create(
            cedula=cedula,
            codigo_sap=f"SAP-{cedula}",
            nombre="ANA",
            apellido="PEREZ",
            password="",
        )

    def _datos(self, empleado, **extra):
        datos = {
            "empleado": empleado,
            "areas": ["TRANSPORTE"],
            "carpetas_por_area": {"TRANSPORTE": ["LOGISTICA"]},
        }
        datos.update(extra)
        return datos

    # ------------------------------ alta ------------------------------ #
    def test_crear_jefe_ok(self):
        empleado = self._empleado()
        jefe = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        self.assertEqual(jefe.empleado_id, empleado.pk)
        self.assertTrue(jefe.activo)

    def test_crear_acepta_pk_ademas_de_instancia(self):
        empleado = self._empleado()
        jefe = ParametrosService.crear_jefe(self._datos(empleado.pk), actor=None)
        self.assertEqual(jefe.empleado_id, empleado.pk)

    def test_empleado_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe empleado"):
            ParametrosService.crear_jefe(self._datos(999999), actor=None)

    def test_empleado_ausente(self):
        with self.assertRaisesMessage(ValueError, "empleado es obligatorio"):
            ParametrosService.crear_jefe(self._datos(None), actor=None)

    def test_sin_areas_rechazado(self):
        empleado = self._empleado()
        with self.assertRaisesMessage(ValueError, "al menos un área"):
            ParametrosService.crear_jefe(
                self._datos(empleado, areas=[]), actor=None
            )

    def test_area_en_blanco(self):
        empleado = self._empleado()
        with self.assertRaisesMessage(ValueError, "texto no vacío"):
            ParametrosService.crear_jefe(
                self._datos(empleado, areas=["   "]), actor=None
            )

    def test_carpetas_de_area_no_registrada(self):
        """La subclava de carpetas debe apuntar a áreas de la lista."""
        empleado = self._empleado()
        with self.assertRaisesMessage(ValueError, "no está en areas"):
            ParametrosService.crear_jefe(
                self._datos(empleado, carpetas_por_area={"OTRA": ["X"]}),
                actor=None,
            )

    def test_carpetas_no_lista(self):
        empleado = self._empleado()
        with self.assertRaisesMessage(ValueError, "lista de textos"):
            ParametrosService.crear_jefe(
                self._datos(empleado, carpetas_por_area={"TRANSPORTE": "LOG"}),
                actor=None,
            )

    def test_jefe_duplicado_activo(self):
        empleado = self._empleado()
        ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        with self.assertRaisesMessage(ValueError, "Ya existe un jefe validador"):
            ParametrosService.crear_jefe(self._datos(empleado), actor=None)

    def test_actualizar_jefe_areas(self):
        """Snapshot: campos no enviados (empleado, activo) se conservan."""
        empleado = self._empleado()
        jefe = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        actualizado = ParametrosService.actualizar_jefe(
            jefe.pk,
            {
                "areas": ["TRANSPORTE", "ADMINISTRACION"],
                "carpetas_por_area": {"TRANSPORTE": []},
            },
            actor=None,
        )
        self.assertEqual(actualizado.areas, ["TRANSPORTE", "ADMINISTRACION"])
        self.assertEqual(actualizado.empleado_id, empleado.pk)
        self.assertTrue(actualizado.activo)

    # --------------------------- baja/listado -------------------------- #
    def test_inactivar_libera_al_empleado(self):
        empleado = self._empleado()
        jefe = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        ParametrosService.inactivar_jefe(jefe.pk, actor=None)
        self.assertTrue(
            JefeValidador.objects.filter(pk=jefe.pk, activo=False).exists()
        )
        # Con el primero inactivo, el empleado puede tener otro jefe activo.
        nuevo = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        self.assertTrue(nuevo.activo)

    def test_listar_filtro_activo(self):
        empleado = self._empleado()
        jefe = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        ParametrosService.inactivar_jefe(jefe.pk, actor=None)
        self.assertEqual(len(ParametrosService.listar_jefes({"activo": "true"})), 0)
        self.assertEqual(len(ParametrosService.listar_jefes({"activo": "false"})), 1)

    def test_listar_adjunta_empleados_sin_join(self):
        """1 query de jefes + 1 in_bulk: cero N+1 y cero JOIN cross-database."""
        empleado = self._empleado()
        ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        with self.assertNumQueries(2):
            jefes = ParametrosService.listar_jefes()
            self.assertEqual(jefes[0].empleado.cedula, "1000756621")

    def test_serializer_expone_cedula_y_nombre(self):
        empleado = self._empleado()
        jefe = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        datos = JefeValidadorSerializer(ParametrosService.obtener_jefe(jefe.pk)).data
        self.assertEqual(datos["empleado_cedula"], "1000756621")
        self.assertEqual(datos["empleado_nombre"], "ANA PEREZ")

    # ------------------- isUserLeaderOfSalida (782) ------------------- #
    def test_es_jefe_validador_ok(self):
        self._empleado("1055837370")
        ParametrosService.crear_jefe(
            self._datos(Empleado.objects.get(cedula="1055837370")), actor=None
        )
        self.assertTrue(
            ParametrosService.es_jefe_validador(
                "1055837370", "TRANSPORTE", "LOGISTICA"
            )
        )

    def test_es_jefe_validador_carpeta_fuera_de_lista(self):
        empleado = self._empleado("1055837370")
        ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        self.assertFalse(
            ParametrosService.es_jefe_validador(
                "1055837370", "TRANSPORTE", "ADMINISTRACION"
            )
        )

    def test_es_jefe_validador_carpetas_vacias_cubre_todas(self):
        empleado = self._empleado("1055837370")
        ParametrosService.crear_jefe(
            self._datos(empleado, carpetas_por_area={}), actor=None
        )
        self.assertTrue(
            ParametrosService.es_jefe_validador(
                "1055837370", "TRANSPORTE", "CUALQUIERA"
            )
        )

    def test_es_jefe_validador_area_fuera(self):
        empleado = self._empleado("1055837370")
        ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        self.assertFalse(
            ParametrosService.es_jefe_validador(
                "1055837370", "CONTABILIDAD", "LOGISTICA"
            )
        )

    def test_es_jefe_validador_inactivo(self):
        empleado = self._empleado("1055837370")
        jefe = ParametrosService.crear_jefe(self._datos(empleado), actor=None)
        ParametrosService.inactivar_jefe(jefe.pk, actor=None)
        self.assertFalse(
            ParametrosService.es_jefe_validador(
                "1055837370", "TRANSPORTE", "LOGISTICA"
            )
        )

    def test_es_jefe_validador_cedula_sin_jefatura(self):
        self._empleado("800999888")  # existe en personal pero no es jefe
        self.assertFalse(
            ParametrosService.es_jefe_validador("800999888", "TRANSPORTE", "X")
        )

    def test_es_jefe_validador_cedula_desconocida(self):
        self.assertFalse(
            ParametrosService.es_jefe_validador("111222333", "TRANSPORTE", "X")
        )

    def test_es_jefe_validador_acepta_cedula_numerica(self):
        """La sesión legacy envía cédula; se normaliza a str para el lookup."""
        empleado = self._empleado("1000756621")
        ParametrosService.crear_jefe(
            self._datos(empleado, carpetas_por_area={}), actor=None
        )
        self.assertTrue(
            ParametrosService.es_jefe_validador(1000756621, "TRANSPORTE", "X")
        )

    def test_es_jefe_validador_sin_cedula_o_area(self):
        self.assertFalse(ParametrosService.es_jefe_validador("", "TRANSPORTE"))
        self.assertFalse(ParametrosService.es_jefe_validador("1000756621", ""))


class LiquidacionTests(TestCase):
    """§5.2 / CR-10: sábanas, consecutivos atómicos y gate de cierre."""

    def _vehiculo(self, placa="ABC123"):
        return FlotaService.crear(
            {
                "placa": placa,
                "tipo_vehiculo": "CAMIONETA",
                "marca": "MAZDA",
                "referencia": "CX5",
                "modelo_anio": 2022,
                "tipo_contrato": "PROPIO",
                "nombre_propietario": "CINCO SAS",
                "cedula_propietario": "900111222",
                "valor_dia_base": 85000,
                "fecha_soat": date(2027, 1, 1),
                "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )

    def _salida(self, vehiculo, fecha, estado, valor="85000"):
        return Salida.objects.create(
            vehiculo=vehiculo,
            fecha_salida=fecha,
            valor_dia=Decimal(valor),
            estado=estado,
        )

    def _inscribir(self, vehiculo, mes, anio, tipo=TipoPago.MENSUAL):
        return PagoVehiculoMensual.objects.create(
            vehiculo=vehiculo, mes=mes, anio=anio, tipo=tipo
        )

    # --------------------------- sábanas (CR-10) -------------------------- #
    def test_pago_mensual_suma_tres_estados(self):
        vehiculo = self._vehiculo()
        self._inscribir(vehiculo, 9, 2026)
        self._salida(vehiculo, date(2026, 9, 5), EstadoSalida.APROBADO)
        self._salida(vehiculo, date(2026, 9, 6), EstadoSalida.REPORTADO)
        self._salida(vehiculo, date(2026, 9, 7), EstadoSalida.VALIDADO)
        self._salida(vehiculo, date(2026, 9, 8), EstadoSalida.RECHAZADO)
        self._salida(vehiculo, date(2026, 9, 9), EstadoSalida.ELIMINADO)

        sabana = LiquidacionService.sabana_pago_mensual(9, 2026)
        self.assertEqual(sabana["filas"][0]["dias"], 3)
        self.assertFalse(sabana["retroactivo"])
        self.assertEqual(sabana["mes_aplicado"], 9)
        self.assertEqual(sabana["totales"]["dias"], 3)

    def test_pronto_pago_solo_aprobado(self):
        """CR-10: misma flota y mes, pero pronto pago cuenta solo APROBADO."""
        vehiculo = self._vehiculo()
        self._inscribir(vehiculo, 9, 2026, tipo=TipoPago.PRONTO_PAGO)
        self._salida(vehiculo, date(2026, 9, 5), EstadoSalida.APROBADO)
        self._salida(vehiculo, date(2026, 9, 6), EstadoSalida.REPORTADO)
        self._salida(vehiculo, date(2026, 9, 7), EstadoSalida.VALIDADO)

        sabana = LiquidacionService.sabana_pronto_pago(9, 2026)
        self.assertEqual(sabana["filas"][0]["dias"], 1)

    def test_total_suma_novedades(self):
        """§5.1: total = Σ (valor_dia ± novedad)."""
        vehiculo = self._vehiculo()
        self._inscribir(vehiculo, 9, 2026)
        salida_a = self._salida(vehiculo, date(2026, 9, 5), EstadoSalida.APROBADO)
        salida_b = self._salida(vehiculo, date(2026, 9, 6), EstadoSalida.APROBADO)
        Novedad.objects.create(
            salida=salida_a,
            tipo=TipoNovedad.ADICIONAL,
            valor=Decimal("5000"),
            descripcion="extra",
        )
        Novedad.objects.create(
            salida=salida_b,
            tipo=TipoNovedad.DESCUENTO,
            valor=Decimal("3000"),
            descripcion="descuento",
        )

        sabana = LiquidacionService.sabana_pago_mensual(9, 2026)
        self.assertEqual(sabana["filas"][0]["total"], Decimal("172000.00"))
        self.assertEqual(sabana["totales"]["total"], Decimal("172000.00"))

    def test_sin_inscritos_error(self):
        with self.assertRaisesMessage(
            ValueError, "No se encontraron registros para el mes y año 01/2025."
        ):
            LiquidacionService.sabana_pago_mensual(1, 2025)

    def test_retroceso_desde_mes_actual(self):
        """CR-10: pedido del mes en curso sin inscritos → hasta 6 meses atrás."""
        hoy = date.today()
        mes, anio = hoy.month, hoy.year
        mes_prev, anio_prev = restar_meses(mes, anio, 1)

        vehiculo = self._vehiculo()
        self._inscribir(vehiculo, mes_prev, anio_prev)
        self._salida(vehiculo, date(anio_prev, mes_prev, 5), EstadoSalida.APROBADO)

        sabana = LiquidacionService.sabana_pago_mensual(mes, anio)
        self.assertTrue(sabana["retroactivo"])
        self.assertEqual((mes, anio), (sabana["mes"], sabana["anio"]))
        self.assertEqual(
            (mes_prev, anio_prev),
            (sabana["mes_aplicado"], sabana["anio_aplicado"]),
        )
        self.assertEqual(sabana["filas"][0]["dias"], 1)

    def test_retroceso_agotado_error(self):
        hoy = date.today()
        with self.assertRaisesMessage(ValueError, "No se encontraron registros"):
            LiquidacionService.sabana_pago_mensual(hoy.month, hoy.year)

    def test_filtros_de_sabana(self):
        v1 = self._vehiculo("ABC123")
        v2 = self._vehiculo("DEF456")
        self._inscribir(v1, 9, 2026)
        self._inscribir(v2, 9, 2026)

        sabana = LiquidacionService.sabana_pago_mensual(
            9, 2026, filtros={"placa": "abc"}
        )
        self.assertEqual(len(sabana["filas"]), 1)
        self.assertEqual(sabana["filas"][0]["placa"], "ABC123")

    # ------------------------- consecutivos (D3) -------------------------- #
    def test_consecutivo_arranca_en_1000(self):
        vehiculo = self._vehiculo()
        numero, creado = LiquidacionService.proximo_consecutivo(
            vehiculo.pk, 9, 2026
        )
        self.assertEqual(numero.consecutivo, 1000)
        self.assertTrue(creado)

    def test_consecutivo_sigue_el_maximo_global(self):
        """El legacy tomaba MAX de TODA la tabla (no por vehículo)."""
        a = self._vehiculo("ABC123")
        b = self._vehiculo("DEF456")
        primero, _ = LiquidacionService.proximo_consecutivo(a.pk, 9, 2026)
        segundo, creado = LiquidacionService.proximo_consecutivo(b.pk, 9, 2026)
        self.assertEqual(primero.consecutivo, 1000)
        self.assertEqual(segundo.consecutivo, 1001)
        self.assertTrue(creado)

    def test_consecutivo_idempotente(self):
        vehiculo = self._vehiculo()
        primero, creado_1 = LiquidacionService.proximo_consecutivo(
            vehiculo.pk, 9, 2026
        )
        segundo, creado_2 = LiquidacionService.proximo_consecutivo(
            vehiculo.pk, 9, 2026
        )
        self.assertEqual(primero.pk, segundo.pk)
        self.assertEqual(primero.consecutivo, segundo.consecutivo)
        self.assertTrue(creado_1)
        self.assertFalse(creado_2)

    def test_consecutivo_vehiculo_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe un vehículo"):
            LiquidacionService.proximo_consecutivo(999999, 9, 2026)

    # ------------------------ pagos (D4 / upsert) ------------------------- #
    def test_guardar_pago_upsert(self):
        vehiculo = self._vehiculo()
        LiquidacionService.guardar_pago(
            {"vehiculo": vehiculo.pk, "mes": 9, "anio": 2026, "tipo": "MENSUAL"},
            actor=None,
        )
        pago = LiquidacionService.guardar_pago(
            {
                "vehiculo": vehiculo.pk,
                "mes": 9,
                "anio": 2026,
                "tipo": "MENSUAL",
                "pagado": True,
                "fecha_pago": date(2026, 10, 10),
            },
            actor=None,
        )
        inscritos = PagoVehiculoMensual.objects.filter(
            vehiculo=vehiculo, mes=9, anio=2026, tipo=TipoPago.MENSUAL
        )
        self.assertEqual(inscritos.count(), 1)
        self.assertTrue(pago.pagado)
        self.assertEqual(pago.fecha_pago, date(2026, 10, 10))

    def test_guardar_pago_snapshot_automatico(self):
        """Al marcar pagado sin total, se calcula con la fórmula de la sábana."""
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2026, 9, 5), EstadoSalida.APROBADO)
        self._salida(vehiculo, date(2026, 9, 6), EstadoSalida.REPORTADO)

        pago = LiquidacionService.guardar_pago(
            {
                "vehiculo": vehiculo.pk,
                "mes": 9,
                "anio": 2026,
                "tipo": "MENSUAL",
                "pagado": True,
            },
            actor=None,
        )
        self.assertEqual(pago.total_liquidado, Decimal("170000.00"))

    def test_guardar_pago_tipo_invalido(self):
        vehiculo = self._vehiculo()
        with self.assertRaisesMessage(ValueError, "no es un valor válido"):
            LiquidacionService.guardar_pago(
                {
                    "vehiculo": vehiculo.pk,
                    "mes": 9,
                    "anio": 2026,
                    "tipo": "OTRO",
                },
                actor=None,
            )

    def test_guardar_pago_periodo_invalido(self):
        vehiculo = self._vehiculo()
        with self.assertRaisesMessage(ValueError, "mes debe estar entre 1 y 12"):
            LiquidacionService.guardar_pago(
                {
                    "vehiculo": vehiculo.pk,
                    "mes": 13,
                    "anio": 2026,
                    "tipo": "MENSUAL",
                },
                actor=None,
            )

    def test_listar_pagos_filtros(self):
        vehiculo = self._vehiculo()
        self._inscribir(vehiculo, 9, 2026, tipo=TipoPago.MENSUAL)
        self._inscribir(vehiculo, 9, 2026, tipo=TipoPago.PRONTO_PAGO)

        mensual = LiquidacionService.listar_pagos({"tipo": "MENSUAL"})
        self.assertEqual(mensual.count(), 1)
        self.assertEqual(mensual[0].tipo, TipoPago.MENSUAL)

        with self.assertRaisesMessage(ValueError, "no es un valor válido"):
            LiquidacionService.listar_pagos({"tipo": "OTRO"})
        with self.assertRaisesMessage(ValueError, "número entero"):
            LiquidacionService.listar_pagos({"mes": "x"})

    # ----------------------- gate de fecha límite ------------------------- #
    def test_periodo_abierto_sin_cierre_o_con_cierre_futuro(self):
        self.assertTrue(LiquidacionService.puede_editar_periodo(9, 2026))
        FechaLimiteCierre.objects.create(
            mes=9, anio=2026, fecha_limite=date(2099, 1, 1)
        )
        self.assertTrue(LiquidacionService.puede_editar_periodo(9, 2026))

    def test_periodo_cerrado_tras_fecha_limite(self):
        FechaLimiteCierre.objects.create(
            mes=9, anio=2026, fecha_limite=date(2020, 1, 1)
        )
        self.assertFalse(LiquidacionService.puede_editar_periodo(9, 2026))
        self.assertTrue(
            LiquidacionService.puede_editar_periodo(
                9, 2026, tiene_permiso_editar=True
            )
        )


class SalidaServiceTests(TestCase):
    """B2 · §5.1: núcleo transaccional de salidas.

    Cubre CR-9 (ventana −2 días hábiles con sábados NO hábiles, bypass
    por rol), CR-1/CR-2 anticolisión contra salidas vivas, exigencia de
    personal/disponible, snapshots, máquina de estados D-A11 con
    historial por fila + AuditoriaLog, consulta B1 y escaneo S1.
    """

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()  # DDL antes de las transacciones
        super().setUpClass()

    def setUp(self):
        self.hoy = timezone.localdate()
        # Personal que sale: legacy exige área Y carpeta en personal.
        self.personal = Empleado.objects.create(
            cedula="1234567890",
            codigo_sap="SAP-1234567890",
            nombre="MARIA",
            apellido="GOMEZ",
            area="OPERACIONES",
            carpeta="LOGISTICA",
            sede="MEDELLIN",
            password="",
        )
        # Personal sin área/carpeta (bloqueo legacy 461–477).
        self.sin_area = Empleado.objects.create(
            cedula="1098765432",
            codigo_sap="SAP-1098765432",
            nombre="PEDRO",
            apellido="SIN-DATOS",
            password="",
        )
        # Cédula dual: está en personal (sale) Y en conductores (externo).
        self.dual = Empleado.objects.create(
            cedula="777888999",
            codigo_sap="SAP-777888999",
            nombre="LUIS",
            apellido="EXTERNO",
            area="OPERACIONES",
            carpeta="LOGISTICA",
            sede="MEDELLIN",
            password="",
        )
        self.vehiculo = FlotaService.crear(
            self._vehiculo_datos("KIA001"), actor=None
        )
        self.vehiculo2 = FlotaService.crear(
            self._vehiculo_datos("KIA002"), actor=None
        )
        self.conductor = Conductor.objects.create(
            cedula="777888999",
            nombre_completo="LUIS EXTERNO",
            celular="3001112233",
            fecha_ingreso=date(2026, 1, 1),
        )
        # Jefe validador del área/carpeta de las salidas de prueba.
        self.jefe_empleado = Empleado.objects.create(
            cedula="555666777",
            codigo_sap="SAP-555666777",
            nombre="ANA",
            apellido="JEFE",
            password="",
        )
        ParametrosService.crear_jefe(
            {
                "empleado": self.jefe_empleado,
                "areas": ["OPERACIONES"],
                "carpetas_por_area": {"OPERACIONES": ["LOGISTICA"]},
            },
            actor=None,
        )
        self.jefe = User.objects.create_user(
            username="555666777", password="x"
        )
        self.operador = User.objects.create_user(
            username="1234567890", password="x"
        )
        self.admin = User.objects.create_user(
            username="9999999999", password="x", is_staff=True
        )

    # ------------------------------ fixtures ----------------------------- #
    @staticmethod
    def _vehiculo_datos(placa, **extra):
        datos = {
            "placa": placa,
            "tipo_vehiculo": "CAMIONETA",
            "marca": "KIA",
            "referencia": "SPORTAGE",
            "modelo_anio": 2023,
            "tipo_contrato": "PROPIO",
            "nombre_propietario": "CINCO SAS",
            "cedula_propietario": "900111222",
            "valor_dia_base": 85000,
        }
        datos.update(extra)
        return datos

    def _datos(self, **extra):
        datos = {
            "fecha_salida": self.hoy,
            "vehiculo": self.vehiculo,
            "movil_sale": "1234567890",
            "cc_asignada": "1234567890",
            "observacion": "Reporte de kiosco",
        }
        datos.update(extra)
        return datos

    def _salida(self, estado=EstadoSalida.REPORTADO, fecha=None, **extra):
        """Salida directa (sin validación de servicio) para probar la
        máquina; incluye la semilla de historial que todo registro real
        tiene (registrar_salida/ETL)."""
        datos = {
            "vehiculo": self.vehiculo,
            "fecha_salida": fecha or self.hoy,
            "area": "OPERACIONES",
            "carpeta": "LOGISTICA",
            "sede": "MEDELLIN",
            "valor_dia": Decimal("85000"),
            "estado": estado,
        }
        datos.update(extra)
        salida = Salida.objects.create(**datos)
        SalidaHistorial.objects.create(
            salida=salida,
            estado=salida.estado,
            motivo="",
            fecha_cambio=timezone.now(),
        )
        return salida

    # ------------------------------- CR-9 -------------------------------- #
    def test_ventana_reportar_limites(self):
        limite = calendario.restar_dias_habiles(
            self.hoy, 2, sabado_habil=False
        )
        self.assertTrue(SalidaService.ventana_validacion(self.hoy, None))
        self.assertTrue(
            SalidaService.ventana_validacion(limite, None, "reportar")
        )
        # Un día antes del límite queda fuera (sabado/domingo no "corren"
        # la ventana: el límite es fijo en días hábiles).
        self.assertFalse(
            SalidaService.ventana_validacion(
                limite - timedelta(days=1), None, "reportar"
            )
        )
        self.assertFalse(
            SalidaService.ventana_validacion(
                self.hoy + timedelta(days=1), None, "reportar"
            )
        )

    def test_ventana_reportar_bypass_admin(self):
        vieja = self.hoy - timedelta(days=15)
        self.assertFalse(
            SalidaService.ventana_validacion(vieja, self.operador)
        )
        self.assertTrue(
            SalidaService.ventana_validacion(vieja, self.admin, "reportar")
        )

    def test_ventana_novedad_eliminar_jefe_del_area_bypass(self):
        vieja = self.hoy - timedelta(days=15)
        comun = {
            "accion": "eliminar",
            "area": "OPERACIONES",
            "carpeta": "LOGISTICA",
        }
        # Jefe del área: bypass; del mismo modo admin/programación.
        self.assertTrue(
            SalidaService.ventana_validacion(vieja, self.jefe, **comun)
        )
        self.assertTrue(
            SalidaService.ventana_validacion(vieja, self.admin, **comun)
        )
        # Operador de otra carpeta/área: ventana estricta (CR-9).
        self.assertFalse(
            SalidaService.ventana_validacion(vieja, self.operador, **comun)
        )
        otros = dict(comun, area="FINANZAS")
        self.assertFalse(
            SalidaService.ventana_validacion(vieja, self.jefe, **otros)
        )
        # Dentro de ventana cualquiera gestionado pasa.
        self.assertTrue(
            SalidaService.ventana_validacion(
                self.hoy, self.operador, **comun
            )
        )

    # ------------------------------ registro ----------------------------- #
    def test_registrar_ok_snapshots_historial_auditoria(self):
        salida = SalidaService.registrar_salida(
            self._datos(), usuario=self.operador
        )
        self.assertEqual(salida.estado, EstadoSalida.REPORTADO)
        self.assertFalse(salida.es_disponible)
        self.assertIsNone(salida.conductor)
        self.assertEqual(salida.tecnico_asignado_id, self.personal.pk)
        # Snapshots desde personal (no de la tarifa vigente).
        self.assertEqual(salida.area, "OPERACIONES")
        self.assertEqual(salida.carpeta, "LOGISTICA")
        self.assertEqual(salida.sede, "MEDELLIN")
        self.assertEqual(salida.valor_dia, Decimal("85000"))
        self.assertEqual(salida.creado_por_id, self.personal.pk)
        # Semilla de historial (fila, no JSON) + log de auditoría.
        historial = list(salida.historial.all())
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0].estado, EstadoSalida.REPORTADO)
        log = AuditoriaLog.objects.get(
            tabla="transporte_salida",
            accion="CREADO",
            registro_id=salida.pk,
        )
        self.assertEqual(log.datos_despues, {"estado": "REPORTADO"})
        self.assertEqual(log.creado_por_id, self.personal.pk)

    def test_registrar_disponible_requiere_area_manual(self):
        with self.assertRaisesMessage(ValueError, "Debe seleccionar un área"):
            SalidaService.registrar_salida(
                self._datos(movil_sale="disponible"), usuario=self.operador
            )
        salida = SalidaService.registrar_salida(
            self._datos(
                movil_sale="disponible", area="OPERACIONES",
                carpeta="SOPORTE", cc_asignada="",
            ),
            usuario=self.operador,
        )
        self.assertTrue(salida.es_disponible)
        self.assertIsNone(salida.conductor)
        self.assertEqual(salida.area, "OPERACIONES")
        self.assertEqual(salida.carpeta, "SOPORTE")

    def test_registrar_personal_sin_area_carpeta_bloquea(self):
        # 461–477: sin área o carpeta en personal ⇒ excepción bloqueante.
        with self.assertRaisesMessage(
            ValueError, "no tiene asignada un área o carpeta asignada"
        ):
            SalidaService.registrar_salida(
                self._datos(movil_sale="1098765432"), usuario=self.operador
            )

    def test_registrar_cedula_inexistente_en_personal_bloquea(self):
        with self.assertRaisesMessage(
            ValueError, "no tiene asignada un área o carpeta asignada"
        ):
            SalidaService.registrar_salida(
                self._datos(movil_sale="0000000000"), usuario=self.operador
            )

    def test_registrar_fuera_de_ventana_y_fecha_futura(self):
        vieja = self.hoy - timedelta(days=15)
        with self.assertRaisesMessage(
            ValueError, "No es posible registrar la salida en esta fecha"
        ):
            SalidaService.registrar_salida(
                self._datos(fecha_salida=vieja), usuario=self.operador
            )
        with self.assertRaisesMessage(
            ValueError, "No es posible registrar la salida en esta fecha"
        ):
            SalidaService.registrar_salida(
                self._datos(fecha_salida=self.hoy + timedelta(days=1)),
                usuario=self.operador,
            )

    def test_registrar_en_limite_exacto_de_2_dias_habiles(self):
        limite = calendario.restar_dias_habiles(
            self.hoy, 2, sabado_habil=False
        )
        # En el límite: pasa sin bypass.
        salida = SalidaService.registrar_salida(
            self._datos(fecha_salida=limite), usuario=None
        )
        self.assertEqual(salida.fecha_salida, limite)
        # Un día antes del límite: fuera (aunque sea el mismo "hábil").
        with self.assertRaisesMessage(
            ValueError, "No es posible registrar la salida en esta fecha"
        ):
            SalidaService.registrar_salida(
                self._datos(fecha_salida=limite - timedelta(days=1)),
                usuario=None,
            )

    def test_registrar_bypass_de_ventana_por_admin(self):
        vieja = self.hoy - timedelta(days=15)
        salida = SalidaService.registrar_salida(
            self._datos(fecha_salida=vieja), usuario=self.admin
        )
        self.assertEqual(salida.fecha_salida, vieja)

    def test_cr1_duplicado_vehiculo_dia(self):
        SalidaService.registrar_salida(self._datos(), usuario=self.operador)
        with self.assertRaisesMessage(
            ValueError,
            "Ya existe un registro de salida para este vehículo",
        ):
            SalidaService.registrar_salida(
                self._datos(movil_sale="disponible", area="OPERACIONES"),
                usuario=self.operador,
            )

    def test_cr2_duplicado_movil_dia_conductor(self):
        s1 = SalidaService.registrar_salida(
            self._datos(vehiculo=self.vehiculo, movil_sale="777888999"),
            usuario=self.operador,
        )
        # D-A10: cédula dual ⇒ FK conductor (habilita CR-2).
        self.assertEqual(s1.conductor_id, self.conductor.pk)
        with self.assertRaisesMessage(
            ValueError,
            "Ya existe un registro de salida para esta móvil",
        ):
            SalidaService.registrar_salida(
                self._datos(vehiculo=self.vehiculo2, movil_sale="777888999"),
                usuario=self.operador,
            )

    def test_cr1_liberada_por_eliminar_logico(self):
        salida = SalidaService.registrar_salida(
            self._datos(), usuario=self.operador
        )
        SalidaService.eliminar(salida.pk, usuario=self.operador)
        # El borrado lógico libera el vehículo para otro despacho el
        # mismo día (CR-1 solo mira salidas vivas).
        nueva = SalidaService.registrar_salida(
            self._datos(), usuario=self.operador
        )
        self.assertNotEqual(nueva.pk, salida.pk)
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.ELIMINADO)

    def test_registrar_valor_dia_snapshot_override(self):
        salida = SalidaService.registrar_salida(
            self._datos(valor_dia=Decimal("99000")), usuario=self.operador
        )
        self.assertEqual(salida.valor_dia, Decimal("99000"))

    def test_obtener_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe la salida"):
            SalidaService.obtener(999999)

    # ------------------------ máquina de estados ------------------------- #
    def test_reportado_a_aprobado_con_jefe(self):
        salida = self._salida()
        SalidaService.aprobar(salida.pk, usuario=self.jefe)
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.APROBADO)
        self.assertEqual(salida.modificado_por_id, self.jefe_empleado.pk)
        estados = {h.estado for h in salida.historial.all()}
        self.assertEqual(
            estados, {EstadoSalida.REPORTADO, EstadoSalida.APROBADO}
        )
        log = AuditoriaLog.objects.get(
            accion="CAMBIO_ESTADO", registro_id=salida.pk
        )
        self.assertEqual(log.datos_antes, {"estado": "REPORTADO"})
        self.assertEqual(log.datos_despues["estado"], "APROBADO")

    def test_aprobado_a_validado_d_a11(self):
        salida = self._salida(estado=EstadoSalida.APROBADO)
        SalidaService.validar(salida.pk, usuario=self.jefe)
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)

    def test_reportado_a_validado_no_permitido(self):
        salida = self._salida()
        with self.assertRaisesMessage(ValueError, "Transición no permitida"):
            SalidaService.validar(salida.pk, usuario=self.jefe)

    def test_rechazar_exige_motivo_y_queda_terminal(self):
        salida = self._salida()
        with self.assertRaisesMessage(ValueError, "motivo de rechazo"):
            SalidaService.rechazar(salida.pk, "  ", usuario=self.jefe)
        SalidaService.rechazar(
            salida.pk, "Datos incorrectos", usuario=self.jefe
        )
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.RECHAZADO)
        fila = salida.historial.filter(
            estado=EstadoSalida.RECHAZADO
        ).first()
        self.assertEqual(fila.motivo, "Datos incorrectos")
        self.assertEqual(fila.creado_por_id, self.jefe_empleado.pk)
        # Terminal: no se re-aprueba desde RECHAZADO.
        with self.assertRaisesMessage(ValueError, "Transición no permitida"):
            SalidaService.aprobar(salida.pk, usuario=self.jefe)

    def test_transicion_sin_permiso_de_gestion(self):
        salida = self._salida()
        with self.assertRaisesMessage(
            ValueError, "No tiene permiso para gestionar"
        ):
            SalidaService.aprobar(salida.pk, usuario=self.operador)

    def test_aprobar_masivo_todas_o_ninguna(self):
        a = self._salida()
        b = self._salida(vehiculo=self.vehiculo2)
        SalidaService.aprobar_masivo([a.pk, b.pk], usuario=self.jefe)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.estado, EstadoSalida.APROBADO)
        self.assertEqual(b.estado, EstadoSalida.APROBADO)
        # Atómico: si una no está en REPORTADO, ninguna cambia.
        c = self._salida(estado=EstadoSalida.APROBADO)
        d = self._salida(vehiculo=self.vehiculo2)
        with self.assertRaisesMessage(ValueError, "Transición no permitida"):
            SalidaService.aprobar_masivo([c.pk, d.pk], usuario=self.jefe)
        d.refresh_from_db()
        self.assertEqual(d.estado, EstadoSalida.REPORTADO)

    def test_eliminar_ventana_estricta_y_bypass(self):
        vieja = self._salida(fecha=self.hoy - timedelta(days=15))
        with self.assertRaisesMessage(
            ValueError,
            "Solo se permite eliminar registros de hasta máximo 2 días atrás",
        ):
            SalidaService.eliminar(vieja.pk, usuario=self.operador)
        # Admin bypass y jefe del área también; operador dentro de la
        # ventana puede (CR-9).
        SalidaService.eliminar(vieja.pk, usuario=self.admin)
        vieja.refresh_from_db()
        self.assertEqual(vieja.estado, EstadoSalida.ELIMINADO)
        hoy = self._salida(vehiculo=self.vehiculo2)
        SalidaService.eliminar(hoy.pk, usuario=self.operador)
        hoy.refresh_from_db()
        self.assertEqual(hoy.estado, EstadoSalida.ELIMINADO)

    # ------------------------------ consulta ----------------------------- #
    def test_listar_por_rango_de_fechas(self):
        self._salida(fecha=self.hoy - timedelta(days=3))
        self._salida(vehiculo=self.vehiculo2, fecha=self.hoy)
        dentro = SalidaService.listar(
            {
                "desde": str(self.hoy - timedelta(days=2)),
                "hasta": str(self.hoy),
            }
        )
        self.assertEqual(dentro.count(), 1)
        self.assertEqual(dentro[0].fecha_salida, self.hoy)

    def test_listar_excluye_eliminadas_por_defecto(self):
        viva = self._salida()
        self._salida(vehiculo=self.vehiculo2, estado=EstadoSalida.ELIMINADO)
        base = SalidaService.listar({})
        self.assertEqual(list(base), [viva])
        solo_eliminadas = SalidaService.listar({"estado": "ELIMINADO"})
        self.assertEqual(solo_eliminadas.count(), 1)
        self.assertEqual(
            solo_eliminadas[0].estado, EstadoSalida.ELIMINADO
        )

    def test_listar_search_por_placa(self):
        self._salida()
        otro = self._salida(vehiculo=self.vehiculo2)
        encontradas = SalidaService.listar({"search": "kia002"})
        self.assertEqual(list(encontradas), [otro])

    # ------------------------------- kiosco ------------------------------ #
    def test_escanear_resuelve_qr_a_vehiculo_y_salida_del_dia(self):
        SalidaService.registrar_salida(self._datos(), usuario=self.operador)
        datos = FlotaService.escanear(" kia001 ")  # QR: placa, sin sanear
        self.assertEqual(datos["vehiculo"].placa, "KIA001")
        self.assertIsNotNone(datos["salida"])
        self.assertEqual(datos["salida"].estado, EstadoSalida.REPORTADO)

    def test_escanear_sin_salida_del_dia(self):
        datos = FlotaService.escanear("KIA002")
        self.assertEqual(datos["vehiculo"].placa, "KIA002")
        self.assertIsNone(datos["salida"])

    def test_escanear_qr_invalido(self):
        with self.assertRaisesMessage(ValueError, "está vacío"):
            FlotaService.escanear("   ")
        with self.assertRaisesMessage(ValueError, "no encontrado"):
            FlotaService.escanear("ZZZ999")
class NovedadSalidaTests(TestCase):
    """B6/B7 · §5.1: novedades con UNA por salida, ventana CR-9 y
    máquina de estados (solo REPORTADO/APROBADO es gestionable)."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        self.hoy = timezone.localdate()
        self.personal = Empleado.objects.create(
            cedula="111222333", codigo_sap="SAP-111222333",
            nombre="MARIA", apellido="GOMEZ",
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            password="",
        )
        self.operador = User.objects.create_user(
            username="111222333", password="x"
        )
        self.jefe_empleado = Empleado.objects.create(
            cedula="555666001", codigo_sap="SAP-555666001",
            nombre="ANA", apellido="JEFE", password="",
        )
        ParametrosService.crear_jefe(
            {
                "empleado": self.jefe_empleado,
                "areas": ["OPERACIONES"],
                "carpetas_por_area": {"OPERACIONES": []},
            },
            actor=None,
        )
        self.jefe = User.objects.create_user(
            username="555666001", password="x"
        )
        self.vehiculo = FlotaService.crear(
            SalidaServiceTests._vehiculo_datos("NOV001"), actor=None
        )

    def _salida(self, estado=EstadoSalida.REPORTADO, fecha=None,
                vehiculo=None):
        salida = Salida.objects.create(
            vehiculo=vehiculo or self.vehiculo,
            fecha_salida=fecha or self.hoy,
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            valor_dia=Decimal("85000"), estado=estado,
        )
        SalidaHistorial.objects.create(
            salida=salida, estado=estado, motivo="",
            fecha_cambio=timezone.now(),
        )
        return salida

    def test_adicional_suma_al_total(self):
        salida = self._salida()
        SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.ADICIONAL, Decimal("15000"),
            "Recargo nocturno", usuario=self.operador,
        )
        salida.refresh_from_db()
        self.assertEqual(
            SalidaService.calcular_pago(salida), Decimal("100000")
        )

    def test_descuento_rest_al_total(self):
        salida = self._salida()
        SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.DESCUENTO, Decimal("5000"),
            "Retardo", usuario=self.operador,
        )
        salida.refresh_from_db()
        self.assertEqual(
            SalidaService.calcular_pago(salida), Decimal("80000")
        )

    def test_una_por_salida_sobrescribe(self):
        salida = self._salida()
        primera = SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.ADICIONAL, Decimal("10000"),
            "Primera", usuario=self.operador,
        )
        segunda = SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.DESCUENTO, Decimal("20000"),
            "Segunda", usuario=self.operador,
        )
        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(Novedad.objects.filter(salida=salida).count(), 1)
        salida.refresh_from_db()
        self.assertEqual(
            SalidaService.calcular_pago(salida), Decimal("65000")
        )

    def test_novedad_dentro_de_ventana_la_puede_cualquiera(self):
        # CR-9: dentro de [hoy−2, hoy] la ventana estricta deja pasar a
        # cualquier usuario sin necesidad de bypass.
        salida = self._salida()
        ajeno = User.objects.create_user(
            username="999888777", password="x"
        )
        novedad = SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.ADICIONAL, Decimal("1000"),
            "Dentro de ventana", usuario=ajeno,
        )
        self.assertIsNotNone(novedad.pk)

    def test_novedad_fuera_de_ventana_exige_bypass(self):
        # Fuera de ventana un ajeno NUNCA pasa; el jefe del área sí.
        vieja = self.hoy - timedelta(days=15)
        salida = self._salida(fecha=vieja)
        ajeno = User.objects.create_user(
            username="999888777", password="x"
        )
        with self.assertRaisesMessage(ValueError, "2 días atrás"):
            SalidaService.registrar_novedad(
                salida.pk, TipoNovedad.ADICIONAL, Decimal("1000"),
                "Intento fuera de ventana", usuario=ajeno,
            )
        # El jefe del área sí tiene bypass de ventana y puede gestionar.
        novedad = SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.ADICIONAL, Decimal("1000"),
            "Bypass del jefe", usuario=self.jefe,
        )
        self.assertIsNotNone(novedad.pk)

    def test_eliminar_novedad_borra_y_audita(self):
        salida = self._salida()
        SalidaService.registrar_novedad(
            salida.pk, TipoNovedad.ADICIONAL, Decimal("10000"),
            "Borrar", usuario=self.operador,
        )
        SalidaService.eliminar_novedad(salida.pk, usuario=self.operador)
        self.assertEqual(Novedad.objects.filter(salida=salida).count(), 0)
        salida.refresh_from_db()
        self.assertEqual(
            SalidaService.calcular_pago(salida), Decimal("85000")
        )

    def test_eliminar_novedad_sin_novedad_da_error(self):
        salida = self._salida()
        with self.assertRaisesMessage(ValueError, "no tiene novedades"):
            SalidaService.eliminar_novedad(salida.pk, usuario=self.operador)

    def test_serializer_B10_mixto_con_y_sin_novedad(self):
        # B10/B15 en el camino crítico del listado: una salida SIN
        # novedad (RelatedObjectDoesNotExist capturado) y otra CON
        # novedad, serializadas juntas sin romper.
        from .serializers.salida_serializer import SalidaSerializer
        con = self._salida()
        SalidaService.registrar_novedad(
            con.pk, TipoNovedad.ADICIONAL, Decimal("15000"),
            "Recargo", usuario=self.operador,
        )
        sin = self._salida(vehiculo=FlotaService.crear(
            SalidaServiceTests._vehiculo_datos("NOV002"), actor=None
        ))
        qs = Salida.objects.select_related(
            "vehiculo", "novedad"
        ).filter(pk__in=[con.pk, sin.pk])
        ctx = {"request": type("R", (), {"user": None})()}
        datos = {d["id"]: d for d in SalidaSerializer(
            qs, many=True, context=ctx
        ).data}
        self.assertEqual(str(datos[con.pk]["valor_novedad"]), "15000.00")
        self.assertEqual(str(datos[con.pk]["total_a_pagar"]), "100000.00")
        # Decimal(0) sin contexto serializa como "0"; el decimal del
        # modelo (0.00) como "0.00". Aceptamos ambos, es cosmético.
        self.assertIn(str(datos[sin.pk]["valor_novedad"]), ("0", "0.00"))
        self.assertEqual(str(datos[sin.pk]["total_a_pagar"]), "85000.00")


class ValidacionServiceTests(TestCase):
    """B4/F4 · cierre mensual por área: UNA fila por (área, mes, año) y
    autorización jefe-del-área (A1) o programación (§5.9)."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        self.jefe_empleado = Empleado.objects.create(
            cedula="555000111", codigo_sap="SAP-555000111",
            nombre="ANA", apellido="JEFE", password="",
        )
        ParametrosService.crear_jefe(
            {
                "empleado": self.jefe_empleado,
                "areas": ["OPERACIONES"],
                "carpetas_por_area": {"OPERACIONES": []},
            },
            actor=None,
        )
        self.jefe = User.objects.create_user(
            username="555000111", password="x"
        )
        self.admin = User.objects.create_user(
            username="999000111", password="x", is_staff=True
        )
        self.ajeno = User.objects.create_user(
            username="999000222", password="x"
        )

    def _datos(self, **extra):
        datos = {
            "area": "OPERACIONES",
            "mes": 9,
            "anio": 2026,
            "datos": {"notas": "cierre de prueba"},
        }
        datos.update(extra)
        return datos

    def test_cierre_por_jefe_del_area(self):
        cierre = ValidacionService.cerrar_area(
            self._datos(), usuario=self.jefe
        )
        self.assertEqual(cierre.area, "OPERACIONES")
        self.assertEqual(cierre.mes, 9)
        self.assertEqual(cierre.anio, 2026)
        self.assertEqual(cierre.datos["notas"], "cierre de prueba")

    def test_cierre_por_admin(self):
        cierre = ValidacionService.cerrar_area(
            self._datos(), usuario=self.admin
        )
        self.assertIsNotNone(cierre.pk)

    def test_cierre_sin_rol_es_rechazado(self):
        with self.assertRaisesMessage(ValueError, "No tiene permisos"):
            ValidacionService.cerrar_area(
                self._datos(), usuario=self.ajeno
            )

    def test_unicidad_area_periodo(self):
        ValidacionService.cerrar_area(self._datos(), usuario=self.admin)
        with self.assertRaisesMessage(ValueError, "Ya existe un cierre"):
            ValidacionService.cerrar_area(self._datos(), usuario=self.admin)
        self.assertEqual(
            ValidacionSalida.objects.filter(area="OPERACIONES").count(), 1
        )

    def test_listar_filtra_por_mes_anio_area(self):
        ValidacionService.cerrar_area(self._datos(), usuario=self.admin)
        ValidacionService.cerrar_area(
            self._datos(area="FINANZAS"), usuario=self.admin
        )
        solo_oper = ValidacionService.listar({"area": "operaciones"})
        self.assertEqual(solo_oper.count(), 1)
        por_mes = ValidacionService.listar({"mes": "9", "anio": "2026"})
        self.assertEqual(por_mes.count(), 2)
        vacio = ValidacionService.listar({"mes": "1"})
        self.assertEqual(vacio.count(), 0)

    def test_listar_mes_invalido_da_error(self):
        with self.assertRaisesMessage(ValueError, "mes"):
            ValidacionService.listar({"mes": "13"})


class PerfilGestionTests(TestCase):
    """B15 · permisos por fila sin N+1: programación o jefatura por
    área/carpeta (A1)."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        self.jefe_empleado = Empleado.objects.create(
            cedula="444333222", codigo_sap="SAP-444333222",
            nombre="LUIS", apellido="JEFE", password="",
        )
        ParametrosService.crear_jefe(
            {
                "empleado": self.jefe_empleado,
                "areas": ["OPERACIONES"],
                "carpetas_por_area": {"OPERACIONES": ["LOGISTICA"]},
            },
            actor=None,
        )
        self.jefe = User.objects.create_user(
            username="444333222", password="x"
        )
        self.admin = User.objects.create_user(
            username="999444333", password="x", is_staff=True
        )

    def test_admin_gestiona_todo(self):
        perfil = SalidaService.perfil_gestion(self.admin)
        self.assertTrue(perfil.puede_gestionar("CUALQUIERA"))

    def test_jefe_gestiona_su_area_carpeta(self):
        perfil = SalidaService.perfil_gestion(self.jefe)
        self.assertTrue(
            perfil.puede_gestionar("OPERACIONES", "LOGISTICA")
        )

    def test_jefe_no_gestiona_otra_area_ni_carpeta(self):
        perfil = SalidaService.perfil_gestion(self.jefe)
        self.assertFalse(perfil.puede_gestionar("OPERACIONES", "OTRA"))
        self.assertFalse(perfil.puede_gestionar("FINANZAS", "LOGISTICA"))

    def test_sin_rol_no_gestiona(self):
        ajeno = User.objects.create_user(username="000111222", password="x")
        perfil = SalidaService.perfil_gestion(ajeno)
        self.assertFalse(perfil.puede_gestionar("OPERACIONES", "LOGISTICA"))


class HistorialSalidaTests(TestCase):
    """B4 · §7.2: historial como FILAS de SalidaHistorial, más reciente
    primero; error si la salida no existe."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        self.hoy = timezone.localdate()
        self.vehiculo = FlotaService.crear(
            SalidaServiceTests._vehiculo_datos("HIS001"), actor=None
        )
        self.salida = Salida.objects.create(
            vehiculo=self.vehiculo,
            fecha_salida=self.hoy,
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            valor_dia=Decimal("85000"), estado=EstadoSalida.REPORTADO,
        )

    def test_historial_mas_reciente_primero(self):
        base = timezone.now()
        SalidaHistorial.objects.create(
            salida=self.salida, estado=EstadoSalida.REPORTADO,
            motivo="", fecha_cambio=base,
        )
        SalidaHistorial.objects.create(
            salida=self.salida, estado=EstadoSalida.APROBADO,
            motivo="", fecha_cambio=base + timedelta(hours=1),
        )
        filas = list(SalidaService.historial(self.salida.pk))
        self.assertEqual(
            [f.estado for f in filas],
            [EstadoSalida.APROBADO, EstadoSalida.REPORTADO],
        )

    def test_historial_salida_inexistente(self):
        with self.assertRaisesMessage(ValueError, "No existe la salida"):
            SalidaService.historial(999999)


class ReporteFotograficoReglasTests(SimpleTestCase):
    """Reglas puras del reporte fotográfico (sin BD): normalización y exenciones."""

    def test_normalizar_clave(self):
        self.assertEqual(
            ReporteFotograficoService.normalizar_clave("Operacion & Mant. (02)"),
            "OPERACIONMANT02",
        )

    def test_normalizar_clave_elimina_acentos(self):
        # Paridad legacy: el PHP no es multibyte, los acentos se descartan.
        self.assertEqual(
            ReporteFotograficoService.normalizar_clave("Operación"), "OPERACIN"
        )

    def test_normalizar_ot_im_solo_digitos(self):
        # IM exige normalizar a la base numérica de la OT.
        self.assertEqual(
            ReporteFotograficoService.normalizar_ot_actividad(
                "1234_ABC", area="IM", carpeta="APOYO"
            ),
            "1234",
        )

    def test_normalizar_ot_area_no_requerida(self):
        self.assertEqual(
            ReporteFotograficoService.normalizar_ot_actividad(
                "OT-99", area="OM", carpeta="CORRECTIVO"
            ),
            "OT-99",
        )

    def test_omite_oy_m_correctivo(self):
        self.assertTrue(
            ReporteFotograficoService.omite_validacion_ot(
                "OM", "CORRECTIVO MECANICO", "TECNICO"
            )
        )

    def test_omite_oy_m_no_aplica_preventivo(self):
        self.assertFalse(
            ReporteFotograficoService.omite_validacion_ot(
                "OM", "PREVENTIVO", "TECNICO"
            )
        )

    def test_omite_pymes_en(self):
        self.assertTrue(
            ReporteFotograficoService.omite_validacion_ot("EN", "PYMES", "AUXILIAR")
        )

    def test_omite_iym_apoyo_externo(self):
        self.assertTrue(
            ReporteFotograficoService.omite_validacion_ot(
                "IM", "APOYO NORTE", "APOYO EXTERNO"
            )
        )

    def test_no_omite_transporte(self):
        self.assertFalse(
            ReporteFotograficoService.omite_validacion_ot(
                "TRANSPORTE", "LOGISTICA", "TECNICO"
            )
        )

    def test_valida_ot_en_wfm_im(self):
        self.assertTrue(ReporteFotograficoService.valida_ot_en_wfm("IM"))
        self.assertFalse(ReporteFotograficoService.valida_ot_en_wfm("OM"))


class ReporteFotograficoTests(TestCase):
    """B3: reporte fotográfico diario (ventana, agenda, imágenes, save)."""

    # Relojes fijos en America/Bogota: dentro [10:00,16:00] y fuera.
    RELOJ_OK = datetime(2026, 10, 15, 11, 0, tzinfo=ZoneInfo("America/Bogota"))
    RELOJ_TARDE = datetime(2026, 10, 15, 17, 30, tzinfo=ZoneInfo("America/Bogota"))
    RELOJ_TEMPRANO = datetime(2026, 10, 15, 8, 0, tzinfo=ZoneInfo("America/Bogota"))

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()  # DDL antes de las transacciones
        super().setUpClass()

    def setUp(self):
        media = override_settings(
            MEDIA_ROOT=tempfile.mkdtemp(prefix="transporte_test_reporte_")
        )
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user(username="1000001", password="x")
        self.empleado = Empleado.objects.create(
            cedula="1000001", codigo_sap="SAP-1", nombre="TEC", apellido="UNO",
            password="", area="TRANSPORTE", carpeta="LOGISTICA", estado="ACTIVO",
        )
        self.vehiculo = Vehiculo.objects.create(**self._vehiculo_datos("ABC123"))

    # ------------------------------ helpers ------------------------------ #
    @staticmethod
    def _vehiculo_datos(placa, **extra):
        datos = {
            "placa": placa, "tipo_vehiculo": "CAMIONETA", "marca": "KIA",
            "referencia": "SPORTAGE", "modelo_anio": 2023, "tipo_contrato": "PROPIO",
            "nombre_propietario": "CINCO SAS", "cedula_propietario": "900111222",
            "valor_dia_base": 85000,
        }
        datos.update(extra)
        return datos

    @staticmethod
    def _imagen(nombre="foto.jpg", tamano=(2000, 1500)):
        buf = io.BytesIO()
        Image.new("RGB", tamano, color=(180, 40, 40)).save(buf, format="JPEG")
        buf.seek(0)
        return SimpleUploadedFile(nombre, buf.read(), content_type="image/jpeg")

    @staticmethod
    def _con_reloj(reloj):
        return mock.patch.object(
            ReporteFotograficoService, "ahora_local", return_value=reloj
        )

    def _agendar(self, cedula, fecha):
        user, _ = User.objects.get_or_create(username=cedula)
        actividad = Actividad.objects.create(responsable=user, ot="OT-77")
        return Agenda.objects.create(
            actividad=actividad, responsable=user,
            fecha_inicio=fecha, fecha_fin=fecha, sede="MEDELLIN",
        )

    def _guardar(self, **extra):
        kwargs = dict(
            vehiculo=self.vehiculo, responsable=self.empleado,
            imagenes=[self._imagen()],
        )
        kwargs.update(extra)
        return ReporteFotograficoService.guardar(**kwargs)

    # ------------------------------ ventana ------------------------------ #
    def test_en_ventana_dentro(self):
        self.assertTrue(ReporteFotograficoService.en_ventana(self.RELOJ_OK))

    def test_en_ventana_fuera_tarde(self):
        self.assertFalse(ReporteFotograficoService.en_ventana(self.RELOJ_TARDE))

    def test_en_ventana_fuera_temprano(self):
        self.assertFalse(ReporteFotograficoService.en_ventana(self.RELOJ_TEMPRANO))

    def test_en_ventana_limites_inclusivos(self):
        inicio = datetime(2026, 10, 15, 10, 0, tzinfo=ZoneInfo("America/Bogota"))
        fin = datetime(2026, 10, 15, 16, 0, tzinfo=ZoneInfo("America/Bogota"))
        self.assertTrue(ReporteFotograficoService.en_ventana(inicio))
        self.assertTrue(ReporteFotograficoService.en_ventana(fin))

    # ------------------------------ save ------------------------------ #
    def test_guardar_ok(self):
        self._agendar("1000001", self.RELOJ_OK.date())
        with self._con_reloj(self.RELOJ_OK):
            reporte = self._guardar()
        self.assertEqual(reporte.fecha, self.RELOJ_OK.date())
        self.assertEqual(reporte.hora, self.RELOJ_OK.time())
        self.assertEqual(reporte.imagenes.count(), 1)
        self.assertEqual(reporte.responsable_id, self.empleado.pk)

    def test_guardar_cinco_imagenes(self):
        self._agendar("1000001", self.RELOJ_OK.date())
        with self._con_reloj(self.RELOJ_OK):
            reporte = self._guardar(
                imagenes=[self._imagen(f"f{i}.jpg") for i in range(5)]
            )
        self.assertEqual(reporte.imagenes.count(), 5)

    def test_guardar_rechaza_fuera_ventana(self):
        self._agendar("1000001", self.RELOJ_TARDE.date())
        with self._con_reloj(self.RELOJ_TARDE):
            with self.assertRaisesRegex(ValueError, "10:00"):
                self._guardar()

    def test_guardar_rechaza_sin_agenda(self):
        # TRANSPORTE/LOGISTICA no es área exenta y no hay agenda.
        with self._con_reloj(self.RELOJ_OK):
            with self.assertRaisesRegex(ValueError, "agenda programada"):
                self._guardar()

    def test_guardar_permite_area_exenta_sin_agenda(self):
        # O&M + CORRECTIVO exenta (transporteOmiteValidacionOt) → sin agenda.
        self.empleado.area = "OM"
        self.empleado.carpeta = "CORRECTIVO"
        self.empleado.save()
        with self._con_reloj(self.RELOJ_OK):
            reporte = self._guardar()
        self.assertTrue(reporte.validacion_ot["agenda_exenta"])

    def test_guardar_rechaza_duplicado_tecnico(self):
        self._agendar("1000001", self.RELOJ_OK.date())
        with self._con_reloj(self.RELOJ_OK):
            self._guardar()
            with self.assertRaisesRegex(ValueError, "Ya existe un reporte"):
                self._guardar()

    def test_guardar_rechaza_mas_de_cinco(self):
        self._agendar("1000001", self.RELOJ_OK.date())
        with self._con_reloj(self.RELOJ_OK):
            with self.assertRaisesRegex(ValueError, "m.s de 5"):
                self._guardar(imagenes=[self._imagen(f"f{i}.jpg") for i in range(6)])

    def test_guardar_rechaza_cero_imagenes(self):
        with self._con_reloj(self.RELOJ_OK):
            with self.assertRaisesRegex(ValueError, "al menos una imagen"):
                self._guardar(imagenes=[])

    def test_guardar_rechaza_fecha_pasada(self):
        self._agendar("1000001", self.RELOJ_OK.date())
        ayer = self.RELOJ_OK.date() - timedelta(days=1)
        with self._con_reloj(self.RELOJ_OK):
            with self.assertRaisesRegex(ValueError, "excepci"):
                self._guardar(fecha=ayer)

    # ------------------------------ agenda (lectura) ------------------------------ #
    def test_agenda_del_dia_encuentra_agenda(self):
        self._agendar("1000001", self.RELOJ_OK.date())
        agendas = ReporteFotograficoService._agendas_del_dia(
            self.empleado, self.RELOJ_OK.date()
        )
        self.assertEqual(len(agendas), 1)

    def test_agenda_del_dia_ignora_borrada(self):
        agenda = self._agendar("1000001", self.RELOJ_OK.date())
        agenda.is_deleted = True
        agenda.save()
        agendas = ReporteFotograficoService._agendas_del_dia(
            self.empleado, self.RELOJ_OK.date()
        )
        self.assertEqual(len(agendas), 0)

    def test_validar_agenda_responsable_sin_identidad(self):
        resultado = ReporteFotograficoService.validar_agenda_responsable(
            None, self.RELOJ_OK.date()
        )
        self.assertFalse(resultado["tiene_agenda"])
        self.assertEqual(resultado["origen"], "sin_identidad")

    # ------------------------------ imágenes ------------------------------ #
    def test_comprimir_re_escala_ancho(self):
        comprimida = ReporteFotograficoService.comprimir_imagen(
            self._imagen(tamano=(3000, 2000))
        )
        img = Image.open(io.BytesIO(comprimida.read()))
        self.assertLessEqual(img.width, 1280)

    def test_comprimir_rechaza_no_imagen(self):
        malo = SimpleUploadedFile("nota.txt", b"no soy imagen", content_type="text/plain")
        with self.assertRaisesRegex(ValueError, "no es una imagen"):
            ReporteFotograficoService.comprimir_imagen(malo)


class ReporteFotograficoApiTests(TestCase):
    """Endpoints B3 (multipart): identidad derivada del usuario autenticado."""

    RELOJ_OK = ReporteFotograficoTests.RELOJ_OK

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        media = override_settings(
            MEDIA_ROOT=tempfile.mkdtemp(prefix="transporte_test_reporte_api_")
        )
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user(username="1000002", password="x")
        # Área exenta para no requerir agenda en el camino feliz del API.
        self.empleado = Empleado.objects.create(
            cedula="1000002", codigo_sap="SAP-2", nombre="API", apellido="TEST",
            password="", area="OM", carpeta="CORRECTIVO", estado="ACTIVO",
        )
        self.vehiculo = Vehiculo.objects.create(
            **ReporteFotograficoTests._vehiculo_datos("API123")
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_create_identidad_desde_usuario(self):
        # El cliente NO envía cédula; el backend la deriva de request.user.
        with ReporteFotograficoTests._con_reloj(self.RELOJ_OK):
            resp = self.api.post(
                "/transporte/reportes-fotograficos/",
                {"placa": "API123", "imagenes": [ReporteFotograficoTests._imagen()]},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["responsable_cedula"], "1000002")

    def test_create_placa_inexistente(self):
        with ReporteFotograficoTests._con_reloj(self.RELOJ_OK):
            resp = self.api.post(
                "/transporte/reportes-fotograficos/",
                {"placa": "ZZZ999", "imagenes": [ReporteFotograficoTests._imagen()]},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 400)

    def test_validar_agenda(self):
        with ReporteFotograficoTests._con_reloj(self.RELOJ_OK):
            resp = self.api.post(
                "/transporte/reportes-fotograficos/validar-agenda/", {}, format="json"
            )
        self.assertEqual(resp.status_code, 200)
        # OM + CORRECTIVO → exenta, no exige agenda.
        self.assertTrue(resp.json()["tiene_agenda"])
        self.assertEqual(resp.json()["origen"], "area_exenta")

    def test_vehiculo_placa(self):
        resp = self.api.get("/transporte/reportes-fotograficos/vehiculo-placa/?placa=API123")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["vehiculo"]["placa"], "API123")


class KioscoS3S4Tests(TestCase):
    """S3 pre-chequeo (fecha/vehículo/móvil) y S4 consulta por placa."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()  # DDL antes de las transacciones
        super().setUpClass()

    def setUp(self):
        self.user = User.objects.create_user(username="1000999", password="x")
        self.vehiculo = Vehiculo.objects.create(
            **ReporteFotograficoTests._vehiculo_datos("KIO123")
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _salida(self, vehiculo, fecha, estado=EstadoSalida.REPORTADO):
        return Salida.objects.create(
            vehiculo=vehiculo,
            fecha_salida=fecha,
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            valor_dia=Decimal("85000"), estado=estado,
        )

    def _validar(self, fecha, vehiculo=None, movil_sale=""):
        return self.api.post(
            "/transporte/kiosco/validar/",
            {
                "fecha": fecha.isoformat(),
                "vehiculo": (vehiculo or self.vehiculo).pk,
                "movil_sale": movil_sale,
            },
            format="json",
        )

    # ------------------------------ S3 ------------------------------ #
    def test_s3_fecha_ok_sin_salida(self):
        resp = self._validar(timezone.localdate())
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["validable"])
        self.assertFalse(data["duplicado_vehiculo"])
        self.assertFalse(data["duplicado_movil"])
        self.assertTrue(data["puede_registrar"])
        self.assertIsNone(data["mensaje"])
        self.assertIsNone(data["registro"])

    def test_s3_fuera_ventana_no_validable(self):
        resp = self._validar(timezone.localdate() - timedelta(days=30))
        data = resp.json()
        self.assertFalse(data["validable"])
        self.assertFalse(data["puede_registrar"])
        self.assertIn("No es posible registrar la salida", data["mensaje"])

    def test_s3_cr1_vehiculo_duplicado(self):
        hoy = timezone.localdate()
        self._salida(self.vehiculo, hoy, EstadoSalida.REPORTADO)
        data = self._validar(hoy).json()
        self.assertTrue(data["duplicado_vehiculo"])
        self.assertFalse(data["puede_registrar"])
        self.assertIn("Ya existe un registro de salida", data["mensaje"])
        self.assertIsNotNone(data["salida"])

    def test_s3_registro_aprobado_informativo(self):
        hoy = timezone.localdate()
        self._salida(self.vehiculo, hoy, EstadoSalida.APROBADO)
        data = self._validar(hoy).json()
        self.assertIsNotNone(data["registro"])
        self.assertEqual(data["registro"]["estado"], EstadoSalida.APROBADO)

    def test_s3_eliminado_no_bloquea(self):
        hoy = timezone.localdate()
        self._salida(self.vehiculo, hoy, EstadoSalida.ELIMINADO)
        data = self._validar(hoy).json()
        self.assertFalse(data["duplicado_vehiculo"])
        self.assertTrue(data["puede_registrar"])

    def test_s3_cr2_movil_duplicado(self):
        hoy = timezone.localdate()
        conductor = Conductor.objects.create(
            cedula="777888999", nombre_completo="CON DUCTOR",
            celular="300", fecha_ingreso=date(2026, 1, 1),
        )
        # Otra vehículo deja al conductor ocupado hoy (aisla CR-2 de CR-1).
        otra = Vehiculo.objects.create(
            **ReporteFotograficoTests._vehiculo_datos("OTR456")
        )
        Salida.objects.create(
            vehiculo=otra, fecha_salida=hoy, conductor=conductor,
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            valor_dia=Decimal("85000"), estado=EstadoSalida.REPORTADO,
        )
        data = self._validar(hoy, movil_sale="777888999").json()
        self.assertTrue(data["duplicado_movil"])
        self.assertFalse(data["puede_registrar"])
        self.assertIn("Ya existe un registro de salida para esta móvil", data["mensaje"])

    def test_s3_disponible_no_aplica_cr2(self):
        hoy = timezone.localdate()
        data = self._validar(hoy, movil_sale="disponible").json()
        self.assertFalse(data["duplicado_movil"])
        self.assertTrue(data["puede_registrar"])

    # ------------------------------ S4 ------------------------------ #
    def test_s4_placa_ok_sin_salida(self):
        resp = self.api.get("/transporte/kiosco/vehiculo/KIO123/")
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["vehiculo"]["placa"], "KIO123")
        self.assertIsNone(data["salida"])

    def test_s4_placa_con_salida_del_dia(self):
        self._salida(self.vehiculo, timezone.localdate())
        data = self.api.get("/transporte/kiosco/vehiculo/KIO123/").json()
        self.assertIsNotNone(data["salida"])
        self.assertEqual(data["salida"]["vehiculo"], self.vehiculo.pk)

    def test_s4_placa_inexistente(self):
        resp = self.api.get("/transporte/kiosco/vehiculo/ZZZ999/")
        self.assertEqual(resp.status_code, 400)

    def test_s4_eliminada_no_se_considera(self):
        self._salida(self.vehiculo, timezone.localdate(), EstadoSalida.ELIMINADO)
        data = self.api.get("/transporte/kiosco/vehiculo/KIO123/").json()
        self.assertIsNone(data["salida"])
