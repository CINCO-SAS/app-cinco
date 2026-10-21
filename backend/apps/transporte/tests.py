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
from openpyxl import load_workbook
from PIL import Image
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.empleados.models import Empleado
from apps.operaciones.models import Actividad, ActividadDetalle, Agenda

from .etl import convertidores as cv
from .etl import normalizadores as nz
from .models import (
    AgendaLogistica,
    AuditoriaLog,
    Conductor,
    ConsecutivoMensual,
    DatosBancariosVehiculo,
    EstadoSalida,
    EstadoWfmJob,
    FechaLimiteCierre,
    JefeValidador,
    Novedad,
    PagoVehiculoMensual,
    ReporteFotograficoVehiculo,
    ResidencialWfm,
    Salida,
    SalidaHistorial,
    TipoNovedad,
    TipoPago,
    TipoVehiculo,
    ValidacionSalida,
    Vehiculo,
    WfmJob,
)
from .serializers.jefe_serializer import JefeValidadorSerializer
from .services import calendario
from .services import (
    ConductorService,
    FlotaService,
    InformeService,
    LiquidacionService,
    ParametrosService,
    PermisoService,
    PlanillaService,
    ReporteFotograficoService,
    SalidaService,
    ValidacionService,
    WfmService,
)
from .services.flota_service import COLUMNAS_CSV_BANCARIOS
from .services.periodos import restar_meses
from .services.reporte_fotografico_service import MSG_OT_VACIA, MSG_OT_VACIA_WFM
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


def _asegurar_tablas_wfm():
    """
    ResidencialWfm y AgendaLogistica son managed=False (BD azul, módulos
    ajenos) y en tests el router está desactivado: se crean aquí desde
    este archivo, igual que Empleado. Andamiaje solo de tests de
    transporte; nunca se tocan residencial ni logística.
    """
    existentes = connection.introspection.table_names()
    with connection.schema_editor() as editor:
        if "residencial_base_wfm" not in existentes:
            editor.create_model(ResidencialWfm)
        if "logistica_actividades_modulo_agenda" not in existentes:
            editor.create_model(AgendaLogistica)


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
        contenido2 = "placa;cedula_banco;nombre;tipo_cuenta;banco;cuenta\nABC123;222;PEDRO;CORRIENTE;PRODUBANCO;999"
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
    """QR de verificación: PNG en `media/transporte/codigos-qr/` con
    caché por placa (contrato revisado, ver ROADMAP · D-A8).

    Payload = placa, igual que el legacy: el kiosco recibe lo escaneado
    como texto de placa (S1), así que el contenido del QR no puede cambiar.
    """

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
        """Regenerable: mismo vehículo → mismos bytes, con y sin caché."""
        vehiculo = self._vehiculo()
        en_cache = FlotaService.generar_qr(vehiculo.pk)
        forzado = FlotaService.generar_qr(vehiculo.pk, forzar=True)
        self.assertEqual(en_cache, forzado)
        self.assertEqual(
            forzado, FlotaService.generar_qr(vehiculo.pk, forzar=True)
        )

    def test_payload_es_la_placa(self):
        """El payload NUNCA cambia: el kiosco S1 decodifica la placa.

        Se fuerza la regeneración porque `crear` ya persiste el QR y sin
        `forzar` la caché devolvería el archivo sin pasar por `add_data`.
        """
        vehiculo = self._vehiculo()
        capturados = []
        original = qrcode.QRCode.add_data

        def espia(self, data):
            capturados.append(data)
            return original(self, data)

        with mock.patch.object(qrcode.QRCode, "add_data", espia):
            FlotaService.generar_qr(vehiculo.pk, forzar=True)

        self.assertEqual(capturados, [vehiculo.placa])

    def test_cambia_placa_no_devuelve_el_qr_anterior(self):
        """Regresión: si cambia la placa, la caché NO puede seguir
        sirviendo el PNG de la placa anterior."""
        vehiculo = self._vehiculo("VIEJA01")
        self.assertTrue(
            FlotaService.generar_qr(vehiculo.pk).startswith(b"\x89PNG")
        )
        vehiculo.refresh_from_db(fields=["codigo_qr"])
        ruta_vieja = vehiculo.codigo_qr.name
        self.assertTrue(ruta_vieja, "el QR debe quedar persistido al crear")
        self.assertTrue(default_storage.exists(ruta_vieja))

        FlotaService.actualizar(
            vehiculo.pk, {"placa": "NUEVA99"}, actor=None
        )
        vehiculo.refresh_from_db()

        # El PNG de la placa anterior queda huérfano y se retira.
        self.assertFalse(default_storage.exists(ruta_vieja))
        # Y lo que devuelve ahora es el QR de la placa NUEVA.
        ruta_nueva = FlotaService.obtener_ruta_qr(vehiculo.pk).name
        self.assertEqual(ruta_nueva, "transporte/codigos-qr/qr_NUEVA99.png")

        capturados = []
        original = qrcode.QRCode.add_data

        def espia(self, data):
            capturados.append(data)
            return original(self, data)

        with mock.patch.object(qrcode.QRCode, "add_data", espia):
            FlotaService.generar_qr(vehiculo.pk, forzar=True)
        self.assertEqual(capturados, ["NUEVA99"])

    def test_persiste_archivo_qr(self):
        vehiculo = self._vehiculo("PERSIST1")
        ruta_esperada = os.path.join(
            settings.MEDIA_ROOT, "transporte", "codigos-qr", f"qr_{vehiculo.placa}.png"
        )
        self.assertTrue(os.path.exists(ruta_esperada))
        vehiculo.refresh_from_db()
        self.assertEqual(
            vehiculo.codigo_qr.name, f"transporte/codigos-qr/qr_{vehiculo.placa}.png"
        )

    def test_obtener_ruta_qr(self):
        vehiculo = self._vehiculo("RUTA123")
        qr_file = FlotaService.obtener_ruta_qr(vehiculo.pk)
        self.assertTrue(bool(qr_file))
        self.assertEqual(qr_file.name, f"transporte/codigos-qr/qr_{vehiculo.placa}.png")

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

    def test_reportado_a_validado_permitido_por_wfm(self):
        """D-A11: el WFM masivo valida `reportado → validado` directo, sin
        pasar por `aprobado` (transporte_validacion_wfm_service.php 427:
        `SET estado='validado' WHERE estado='reportado'`)."""
        salida = self._salida()
        SalidaService.validar(salida.pk, usuario=self.jefe)
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)
        fila = salida.historial.filter(
            estado=EstadoSalida.VALIDADO
        ).first()
        self.assertIsNotNone(fila)

    def test_reportado_a_validado_tambien_exige_gestion(self):
        """Abrir la transición no abre el endpoint: el WFM es un proceso
        autónomo, pero un operador sigue sin poder validar."""
        salida = self._salida()
        with self.assertRaisesMessage(
            ValueError, "No tiene permiso para gestionar"
        ):
            SalidaService.validar(salida.pk, usuario=self.operador)

    def test_aprobado_a_rechazado_d_a11(self):
        """D-A11: el rechazo puede caer sobre una salida ya aprobada
        (base_salida_transporte.php 1159: su único guard es
        `estado != 'eliminado'`, no mira el estado previo)."""
        salida = self._salida(estado=EstadoSalida.APROBADO)
        SalidaService.rechazar(
            salida.pk, "Documento vencido", usuario=self.jefe
        )
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.RECHAZADO)
        fila = salida.historial.filter(
            estado=EstadoSalida.RECHAZADO
        ).first()
        self.assertEqual(fila.motivo, "Documento vencido")

    def test_eliminado_es_terminal(self):
        """Endurecido vs legado: el único guard que SÍ comparte con el
        legado (`estado != 'eliminado'`) es que nada resucita un
        ELIMINADO, ni siquiera un jefe."""
        salida = self._salida(estado=EstadoSalida.ELIMINADO)
        for llamada in (
            lambda: SalidaService.aprobar(salida.pk, usuario=self.jefe),
            lambda: SalidaService.validar(salida.pk, usuario=self.jefe),
            lambda: SalidaService.rechazar(
                salida.pk, "motivo", usuario=self.jefe
            ),
        ):
            with self.assertRaisesMessage(ValueError, "Transición no permitida"):
                llamada()

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

    def test_listar_filtro_conductor_no_reventa_con_texto(self):
        """REGRESIÓN (2026-10-21): `?conductor=` iba a un `int()` crudo.

        `GET /salidas/?conductor=JUAN` levantaba
        `ValueError: invalid literal for int() with base 10: 'JUAN'` → 500.
        `?vehiculo=` ya distinguía pk/placa; `conductor` ahora hace lo mismo.

        NOTA: si viene todo numérico se sigue interpretando como **pk** (es el
        contrato documentado). Para buscar por CÉDULA de quien sale está
        `?search=`, que ya cubre cédula y nombre.
        """
        salida = self._salida(conductor=self.conductor)
        self._salida(
            vehiculo=self.vehiculo2, fecha=self.hoy + timedelta(days=1)
        )

        # pk numérico → FK.
        self.assertEqual(
            [
                s.pk
                for s in SalidaService.listar(
                    {"conductor": str(self.conductor.pk)}
                )
            ],
            [salida.pk],
        )
        # Texto no numérico → nombre de quien sale (antes: ValueError → 500).
        self.assertEqual(
            [
                s.pk
                for s in SalidaService.listar({"conductor": "externo"})
            ],
            [salida.pk],
        )
        # Texto sin coincidencia → 0 filas, no excepción.
        self.assertEqual(
            list(SalidaService.listar({"conductor": "JUAN"})), []
        )

    def test_listar_no_hace_join_cross_database(self):
        """REGRESIÓN (2026-10-20): `tecnico_asignado` → Empleado, que vive en
        la BD `azul`. `select_related` genera un JOIN que Django no puede
        emitir contra `default` y MySQL responde
        `(1146, "Table 'db_cincosas.cinco_base_de_personal' doesn't exist")`
        → `GET /salidas/` y `/salidas/{id}/` devolvían 500.

        En tests el router está desactivado y todo comparte una SQLite, por
        eso los tests de suite no lo veían: solo explotaba contra MySQL real.
        El contrato es prefetch (query aparte, 1 por listado) y no JOIN.
        """
        self._salida()

        # `query.select_related` es `False` (no dict) cuando está vacío.
        rel = SalidaService.listar({}).query.select_related
        campos = set(rel) if isinstance(rel, dict) else set()
        self.assertNotIn(
            "tecnico_asignado",
            campos,
            "listar() debe usar prefetch_related('tecnico_asignado'), no "
            f"select_related (JOIN cross-BD contra azul). Actual: {rel}",
        )

        # obtener() devuelve la instancia con el FK ya resuelto: acceder no
        # debe emitir ninguna query (si volviera a select_related, aquí
        # reventaría contra MySQL aunque en SQLite pase desapercibido).
        salida = self._salida(tecnico_asignado=self.personal)
        obtenida = SalidaService.obtener(salida.pk)
        with self.assertNumQueries(0):
            self.assertEqual(obtenida.tecnico_asignado.cedula, self.personal.cedula)

    def test_listar_y_obtener_acceden_tecnico_sin_n_mas_uno(self):
        """El prefetch debe resolver el FK cross-BD en 1 query extra."""
        self._salida(tecnico_asignado=self.personal)

        # 1 de la lista + 1 del prefetch de tecnico_asignado.
        with self.assertNumQueries(2):
            salidas = list(SalidaService.listar({}))
            # Acceder al objeto precargado NO emite otra query.
            self.assertEqual(salidas[0].tecnico_asignado.cedula, self.personal.cedula)

        # obtener() es de 1 sola fila, también resuelto por el prefetch.
        with self.assertNumQueries(2):
            salida = SalidaService.obtener(salidas[0].pk)
            self.assertEqual(salida.tecnico_asignado.cedula, self.personal.cedula)

    def test_serializer_expone_detalle_de_personas(self):
        """Las columnas de la tabla B1 pintan PERSONAS, no PKs.

        `conductor_detalle` = legacy `movil_sale` (quién SALE) y
        `tecnico_asignado_detalle` = legacy `cc_asignada` (móvil de nómina).
        Ambos comparten la MISMA forma `{nombre, cedula}` para que el front
        tenga un solo shape, y devuelven `None` cuando no hay persona —
        así la tabla pinta '—' / 'Disponible' sin ramas extra.
        """
        from .serializers.salida_serializer import SalidaSerializer

        completa = self._salida(
            conductor=self.conductor, tecnico_asignado=self.personal
        )
        datos = SalidaSerializer(completa).data
        self.assertEqual(
            datos["conductor_detalle"],
            {"nombre": "LUIS EXTERNO", "cedula": "777888999"},
        )
        # Empleado guarda nombre y apellido SEPARADOS: el detalle los compone.
        self.assertEqual(
            datos["tecnico_asignado_detalle"],
            {"nombre": "MARIA GOMEZ", "cedula": "1234567890"},
        )

        # Sin personas → null (no {}), para que el front pueda usar `??`.
        vacia = self._salida(
            vehiculo=self.vehiculo2,
            fecha=self.hoy + timedelta(days=1),
            es_disponible=True,
        )
        datos_vacios = SalidaSerializer(vacia).data
        self.assertIsNone(datos_vacios["conductor_detalle"])
        self.assertIsNone(datos_vacios["tecnico_asignado_detalle"])

    def test_serializer_expone_novedad_detalle(self):
        """B6/B7 · `novedad_detalle` evita el borrado a ciegas.

        `valor_novedad` dice CUÁNTO pero no QUÉ era ni POR QUÉ: sin este
        detalle el front solo podría borrar sin ver, o pedirle al jefe que se
        acuerde del motivo que escribió hace semanas. Devuelve `None` cuando
        no hay novedad, igual que los otros `*_detalle` (para usar `??`).
        """
        from decimal import Decimal

        from .models import Novedad, TipoNovedad
        from .serializers.salida_serializer import SalidaSerializer

        con_novedad = self._salida(
            vehiculo=self.vehiculo,
            fecha=self.hoy,
            conductor=self.conductor,
        )
        Novedad.objects.create(
            salida=con_novedad,
            tipo=TipoNovedad.DESCUENTO,
            valor=Decimal("15000"),
            descripcion="Espera de 40 minutos en bodega",
        )
        datos = SalidaSerializer(con_novedad).data
        # `DecimalField(decimal_places=2)` NO fija 2 decimales en la salida:
        # usa `quantize` con ROUND_HALF_UP, que traeo los ceros y deja '15000'.
        self.assertEqual(
            datos["novedad_detalle"],
            {
                "tipo": "DESCUENTO",
                "valor": "15000",
                "descripcion": "Espera de 40 minutos en bodega",
            },
        )
        # El total B10 ya descuenta: una sola implementación del cálculo.
        # Se compara como número (no como cadena) porque el formato depende
        # de si el Decimal viene de BD (con escala) o de memoria (sin ella).
        self.assertEqual(Decimal(datos["valor_novedad"]), Decimal("15000"))

        sin_novedad = self._salida(
            vehiculo=self.vehiculo2,
            fecha=self.hoy + timedelta(days=1),
            es_disponible=True,
        )
        self.assertIsNone(SalidaSerializer(sin_novedad).data["novedad_detalle"])

    def test_aprobar_masivo_serializa_sin_n_mas_uno(self):
        """REGRESIÓN (2026-10-21): `POST /salidas/aprobar-lote/` (B12) devuelve
        N filas serializadas con las relaciones SIN precargar → 1 query por
        fila aprobada. Con `tecnico_asignado` era peor: un round-trip por fila
        hacia **otra base de datos** (azul).

        Contrato: el nº de queries de la respuesta NO crece con el nº de filas.
        """
        from django.test.utils import CaptureQueriesContext

        from .serializers.salida_serializer import SalidaSerializer

        def medir(n):
            salidas = [
                self._salida(
                    fecha=self.hoy - timedelta(days=d),
                    conductor=self.conductor,
                    tecnico_asignado=self.personal,
                )
                for d in range(n)
            ]
            aprobadas = SalidaService.aprobar_masivo(
                [s.pk for s in salidas], usuario=self.jefe
            )
            contexto = {"request": type("R", (), {"user": None})()}
            with CaptureQueriesContext(connection) as capturadas:
                SalidaSerializer(
                    aprobadas, many=True, context=contexto
                ).data
            return len(capturadas.captured_queries)

        self.assertEqual(
            medir(1),
            medir(4),
            "aprobar-lote hace N+1: serializar 4 filas debe costar lo mismo "
            "que serializar 1 (vehiculo/conductor/novedad/tecnico_asignado "
            "van con prefetch_related).",
        )

    def test_admin_search_fields_no_cruzan_base_externa(self):
        """REGRESIÓN (2026-10-21): `SalidaAdmin.search_fields` incluía
        ``tecnico_asignado__cedula`` -> ``Empleado``, que vive en **azul**
        (``managed=False``, ``db_table='cinco_base_de_personal'``).

        Un lookup con ``__`` en ``search_fields`` genera un JOIN que Django
        no puede emitir contra ``default``; MySQL responde
        ``(1146, "Table 'db_cincosas.cinco_base_de_personal' doesn't exist")``
        y la caja de búsqueda del admin devolvía 500.

        OJO: en tests el router está desactivado, así que ``db_for_read()``
        devuelve siempre ``default`` y NO sirve para detectarlo. Se detecta
        por ``Meta.managed=False``, que es como están declaradas las 8
        tablas externas de este proyecto (empleados, operaciones, common).
        """
        from django.apps import apps as django_apps
        from django.contrib import admin as django_admin

        externos = {
            m._meta.label_lower
            for m in django_apps.get_models()
            if not m._meta.managed
        }
        # Empleado es la tabla externa que originó la regresión.
        self.assertIn("empleados.empleado", externos)

        violaciones = []
        for modelo in django_apps.get_models():
            if modelo._meta.app_label != "transporte":
                continue
            registro = django_admin.site._registry.get(modelo)
            if registro is None:
                continue
            for campo in registro.search_fields or ():
                tramos = campo.split("__")
                actual = modelo
                for tramo in tramos[:-1]:  # el último es el valor, no FK
                    try:
                        relacion = actual._meta.get_field(tramo)
                    except Exception:
                        break
                    remoto = getattr(relacion, "related_model", None)
                    if remoto is None:
                        break
                    if remoto._meta.label_lower in externos:
                        violaciones.append(
                            f"{modelo._meta.label}.{campo} -> {remoto._meta.label}"
                        )
                        break
                    actual = remoto

        self.assertEqual(
            violaciones,
            [],
            "search_fields NO debe atravesar modelos externos (managed=False): "
            f"{violaciones}. Usa un campo snapshot local en su lugar.",
        )

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
        self.assertEqual(resp.json()["data"]["responsable_cedula"], "1000002")

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
        self.assertTrue(resp.json()["data"]["tiene_agenda"])
        self.assertEqual(resp.json()["data"]["origen"], "area_exenta")

    def test_vehiculo_placa(self):
        resp = self.api.get("/transporte/reportes-fotograficos/vehiculo-placa/?placa=API123")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["vehiculo"]["placa"], "API123")

    # --------------------------- consulta (backoffice) ------------------- #
    def _salida(self, vehiculo, fecha, estado=EstadoSalida.REPORTADO):
        return Salida.objects.create(
            vehiculo=vehiculo,
            fecha_salida=fecha,
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            valor_dia=Decimal("85000"), estado=estado,
        )

    def _crear_reporte(self):
        with ReporteFotograficoTests._con_reloj(self.RELOJ_OK):
            resp = self.api.post(
                "/transporte/reportes-fotograficos/",
                {"placa": "API123", "imagenes": [ReporteFotograficoTests._imagen()]},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()["data"]

    def test_list_pagina_y_trae_imagenes(self):
        """`GET /reportes-fotograficos/` debe responder y paginar.

        Sin `pagination_class` declarado `self.paginator` es `None`
        (el proyecto no fija `DEFAULT_PAGINATION_CLASS`) y la respuesta
        revienta con `AssertionError` → HTTP 500.
        """
        self._crear_reporte()

        resp = self.api.get("/transporte/reportes-fotograficos/")
        self.assertEqual(resp.status_code, 200, resp.content)
        cuerpo = resp.json()
        # Contrato paginado que ya consume `normalizarPagina` en el front.
        self.assertEqual(cuerpo["count"], 1)
        fila = cuerpo["results"][0]
        self.assertEqual(fila["placa"], "API123")
        self.assertEqual(len(fila["imagenes"]), 1)
        self.assertEqual(fila["responsable_cedula"], "1000002")

    def test_list_filtra_por_placa_y_por_fechas(self):
        self._crear_reporte()
        otro = Vehiculo.objects.create(
            **ReporteFotograficoTests._vehiculo_datos("OTR456")
        )
        self._salida(otro, self.RELOJ_OK.date())

        resp = self.api.get("/transporte/reportes-fotograficos/", {"vehiculo": "API123"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

        # Rango que excluye el reporte (creado el día de RELOJ_OK).
        fuera_de_rango = self.api.get(
            "/transporte/reportes-fotograficos/",
            {"desde": "1990-01-01", "hasta": "1990-01-02"},
        )
        self.assertEqual(fuera_de_rango.json()["count"], 0)

    def test_list_busca_por_placa_ot_y_responsable(self):
        """Una sola pantalla de búsqueda que cubre AMBOS orígenes.

        `search` toca placa/OT (transporte) y cédula/nombre (azul). Si se
        intentara con un solo `select_related` cruzado, MySQL rechazaría el
        JOIN; `listar()` resuelve primero los PKs de azul y compara por id.
        """
        self._crear_reporte()

        for termino in ("API123", "1000002", "API TEST", "api"):
            with self.subTest(termino=termino):
                resp = self.api.get(
                    "/transporte/reportes-fotograficos/", {"search": termino}
                )
                self.assertEqual(resp.status_code, 200, resp.content)
                self.assertEqual(resp.json()["count"], 1)

        # Término que no coincide con nada.
        nadie = self.api.get(
            "/transporte/reportes-fotograficos/", {"search": "ZZZZZZ"}
        )
        self.assertEqual(nadie.json()["count"], 0)

    # ---------------------------- B14 · badge ---------------------------- #
    def test_create_marca_salida_reportada(self):
        """REGRESIÓN B14: el badge REPORTE de la salida pasaba a "No" siempre.

        En el legacy el reporte escribía `datos.reporte` en la fila de la
        salida y el badge salía de ahí. Aquí eso se aplanó al campo
        `reportado` pero nada lo activaba.
        """
        salida = self._salida(self.vehiculo, self.RELOJ_OK.date())
        self.assertFalse(salida.reportado)

        self._crear_reporte()

        salida.refresh_from_db()
        self.assertTrue(salida.reportado)

    def test_create_no_remueve_eliminadas_ni_salidas_de_otro_dia(self):
        """Dos casillas de seguridad del badge."""
        eliminada = self._salida(
            self.vehiculo, self.RELOJ_OK.date(), estado=EstadoSalida.ELIMINADO
        )
        otro_dia = self._salida(self.vehiculo, date(2020, 1, 1))

        self._crear_reporte()

        eliminada.refresh_from_db()
        self.assertFalse(eliminada.reportado)
        otro_dia.refresh_from_db()
        self.assertFalse(otro_dia.reportado)


class ValidarAgendaOtTests(TestCase):
    """Refinamiento B3 diferido: match OT-específica contra la agenda.

    Port de ``validarOtActividadTransporte`` +
    ``validarOtActividadAgendaTransporte``
    (controlador_transporte_img_reporte_salida_fix.php 319–360 y 175–244).
    """

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        media = override_settings(
            MEDIA_ROOT=tempfile.mkdtemp(prefix="transporte_test_agenda_ot_")
        )
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user(username="2000001", password="x")
        self.empleado = Empleado.objects.create(
            cedula="2000001", codigo_sap="SAP-OT", nombre="TEC", apellido="OT",
            password="", area="TRANSPORTE", carpeta="LOGISTICA", estado="ACTIVO",
        )
        self.vehiculo = Vehiculo.objects.create(
            **ReporteFotograficoTests._vehiculo_datos("OT001")
        )
        self.fecha = date(2026, 10, 15)

    def _agendar(self, ot="OT-77", detalle=None, observacion=""):
        user, _ = User.objects.get_or_create(username="2000001")
        actividad = Actividad.objects.create(responsable=user, ot=ot)
        if detalle:
            ActividadDetalle.objects.create(
                actividad=actividad,
                tipo_trabajo=detalle.get("tipo_trabajo", ""),
                descripcion=detalle.get("descripcion", ""),
            )
        return Agenda.objects.create(
            actividad=actividad, responsable=user,
            fecha_inicio=self.fecha, fecha_fin=self.fecha, sede="MEDELLIN",
            observacion=observacion or None,
        )

    def _validar(self, ot, **kwargs):
        return ReporteFotograficoService.validar_agenda_ot(
            self.empleado, self.fecha, ot, **kwargs
        )

    # --------------------------- reglas base --------------------------- #
    def test_ot_agendada_valida(self):
        self._agendar(ot="OT-77")
        res = self._validar("OT-77")
        self.assertTrue(res["valida"])
        self.assertEqual(res["origen"], "agenda")
        self.assertEqual(res["ot"], "OT-77")

    def test_ot_no_agendada_rechaza_con_mensaje(self):
        self._agendar(ot="OT-77")
        res = self._validar("OT-999")
        self.assertFalse(res["valida"])
        self.assertIn("OT-999", res["msg"])
        self.assertIn("2000001", res["msg"])

    def test_comparacion_normalizada_mayusculas_y_espacios(self):
        # transporteTextoComparableAgenda: mayúsculas + espacios colapsados.
        self._agendar(ot="OT 77")
        self.assertTrue(self._validar("  ot   77 ")["valida"])

    def test_coincide_por_tipo_trabajo_del_detalle(self):
        self._agendar(ot="OT-77", detalle={"tipo_trabajo": "MANTENIMIENTO PREVENTIVO"})
        self.assertTrue(
            self._validar("Mantenimiento   Preventivo")["valida"]
        )

    def test_coincide_por_descripcion_del_detalle(self):
        self._agendar(
            ot="OT-77", detalle={"tipo_trabajo": "X", "descripcion": "CAMBIO DE ACEITE"}
        )
        self.assertTrue(self._validar("CAMBIO DE ACEITE")["valida"])

    def test_coincide_por_observacion_de_la_agenda(self):
        self._agendar(ot="OT-77", observacion="REVISION DE FRENOS")
        self.assertTrue(self._validar("REVISION DE FRENOS")["valida"])

    def test_no_coincide_ot_agendada_en_otra_fecha(self):
        user, _ = User.objects.get_or_create(username="2000001")
        actividad = Actividad.objects.create(responsable=user, ot="OT-77")
        Agenda.objects.create(
            actividad=actividad, responsable=user,
            fecha_inicio=self.fecha, fecha_fin=self.fecha, sede="MEDELLIN",
            is_deleted=True,  # borrada ⇒ no cuenta
        )
        res = self._validar("OT-77")
        self.assertFalse(res["valida"])

    # ---------------------- áreas exentas / WFM ------------------------ #
    def test_area_exenta_omite_la_validacion(self):
        self.empleado.area = "OM"
        self.empleado.carpeta = "CORRECTIVO"
        self.empleado.save()
        res = self._validar("OT-QUE-NO-EXISTE")
        self.assertTrue(res["valida"])
        self.assertEqual(res["origen"], "area_exenta")

    def test_area_wfm_im_recibe_sin_validar(self):
        # IM valida en WFM (subsistema aparte) ⇒ se recibe sin agendar.
        self.empleado.area = "IM"
        self.empleado.save()
        res = self._validar("OT-77777")
        self.assertTrue(res["valida"])
        self.assertEqual(res["origen"], "wfm")

    def test_ot_vacia_sin_area_wfm_exige_agenda(self):
        res = self._validar("")
        self.assertFalse(res["valida"])
        self.assertEqual(res["msg"], MSG_OT_VACIA)

    def test_ot_vacia_en_area_wfm_pide_ot_del_dia(self):
        self.empleado.area = "IM"
        self.empleado.save()
        res = self._validar("   ")
        self.assertFalse(res["valida"])
        self.assertEqual(res["msg"], MSG_OT_VACIA_WFM)

    # --------------------------- por guardar --------------------------- #
    def test_guardar_rechaza_ot_no_agendada(self):
        self._agendar(ot="OT-77")
        with ReporteFotograficoTests._con_reloj(
            ReporteFotograficoTests.RELOJ_OK
        ):
            with self.assertRaisesRegex(ValueError, "no está agendada"):
                ReporteFotograficoService.guardar(
                    vehiculo=self.vehiculo,
                    responsable=self.empleado,
                    imagenes=[ReporteFotograficoTests._imagen()],
                    ot_actividad="OT-999",
                    fecha=self.fecha,
                )
        self.assertEqual(
            ReporteFotograficoVehiculo.objects.filter(vehiculo=self.vehiculo).count(), 0
        )

    def test_guardar_con_ot_agendada_registra_la_validacion(self):
        self._agendar(ot="OT-77")
        with ReporteFotograficoTests._con_reloj(
            ReporteFotograficoTests.RELOJ_OK
        ):
            reporte = ReporteFotograficoService.guardar(
                vehiculo=self.vehiculo,
                responsable=self.empleado,
                imagenes=[ReporteFotograficoTests._imagen()],
                ot_actividad="ot-77",
                fecha=self.fecha,
            )
        self.assertEqual(reporte.validacion_ot["ot_valida"], True)
        self.assertEqual(reporte.validacion_ot["ot_origen"], "agenda")
        self.assertEqual(reporte.ot_actividad, "ot-77")

    def test_guardar_sin_ot_no_exige_match(self):
        # Sin OT declarada el gate sigue siendo solo la agenda (no se endurece
        # el comportamiento ya cerrado en B3).
        self._agendar(ot="OT-77")
        with ReporteFotograficoTests._con_reloj(
            ReporteFotograficoTests.RELOJ_OK
        ):
            reporte = ReporteFotograficoService.guardar(
                vehiculo=self.vehiculo,
                responsable=self.empleado,
                imagenes=[ReporteFotograficoTests._imagen()],
                fecha=self.fecha,
            )
        self.assertNotIn("ot_valida", reporte.validacion_ot)

    # ------------------------------ HTTP ------------------------------- #
    def test_validar_agenda_http_con_ot(self):
        self._agendar(ot="OT-77")
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            "/transporte/reportes-fotograficos/validar-agenda/",
            {"fecha": "2026-10-15", "ot_actividad": "OT-999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertFalse(data["tiene_agenda"])
        self.assertFalse(data["ot"]["valida"])
        self.assertIn("OT-999", data["msg"])

    def test_validar_agenda_http_ot_agendada(self):
        self._agendar(ot="OT-77")
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            "/transporte/reportes-fotograficos/validar-agenda/",
            {"fecha": "2026-10-15", "ot_actividad": "OT-77"},
            format="json",
        )
        data = resp.json()["data"]
        self.assertTrue(data["tiene_agenda"])
        self.assertTrue(data["ot"]["valida"])


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
        payload = resp.json()
        data = payload["data"]
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["validable"])
        self.assertFalse(data["duplicado_vehiculo"])
        self.assertFalse(data["duplicado_movil"])
        self.assertTrue(data["puede_registrar"])
        self.assertIsNone(data["mensaje"])
        self.assertIsNone(data["registro"])

    def test_s3_fuera_ventana_no_validable(self):
        resp = self._validar(timezone.localdate() - timedelta(days=30))
        data = resp.json()["data"]
        self.assertFalse(data["validable"])
        self.assertFalse(data["puede_registrar"])
        self.assertIn("No es posible registrar la salida", data["mensaje"])

    def test_s3_cr1_vehiculo_duplicado(self):
        hoy = timezone.localdate()
        self._salida(self.vehiculo, hoy, EstadoSalida.REPORTADO)
        data = self._validar(hoy).json()["data"]
        self.assertTrue(data["duplicado_vehiculo"])
        self.assertFalse(data["puede_registrar"])
        self.assertIn("Ya existe un registro de salida", data["mensaje"])
        self.assertIsNotNone(data["salida"])

    def test_s3_registro_aprobado_informativo(self):
        hoy = timezone.localdate()
        self._salida(self.vehiculo, hoy, EstadoSalida.APROBADO)
        data = self._validar(hoy).json()["data"]
        self.assertIsNotNone(data["registro"])
        self.assertEqual(data["registro"]["estado"], EstadoSalida.APROBADO)

    def test_s3_eliminado_no_bloquea(self):
        hoy = timezone.localdate()
        self._salida(self.vehiculo, hoy, EstadoSalida.ELIMINADO)
        data = self._validar(hoy).json()["data"]
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
        data = self._validar(hoy, movil_sale="777888999").json()["data"]
        self.assertTrue(data["duplicado_movil"])
        self.assertFalse(data["puede_registrar"])
        self.assertIn("Ya existe un registro de salida para esta móvil", data["mensaje"])

    def test_s3_disponible_no_aplica_cr2(self):
        hoy = timezone.localdate()
        data = self._validar(hoy, movil_sale="disponible").json()["data"]
        self.assertFalse(data["duplicado_movil"])
        self.assertTrue(data["puede_registrar"])

    # ------------------------------ S4 ------------------------------ #
    def test_s4_placa_ok_sin_salida(self):
        resp = self.api.get("/transporte/kiosco/vehiculo/KIO123/")
        data = resp.json()["data"]
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["vehiculo"]["placa"], "KIO123")
        self.assertIsNone(data["salida"])

    def test_s4_placa_con_salida_del_dia(self):
        self._salida(self.vehiculo, timezone.localdate())
        data = self.api.get("/transporte/kiosco/vehiculo/KIO123/").json()["data"]
        self.assertIsNotNone(data["salida"])
        self.assertEqual(data["salida"]["vehiculo"], self.vehiculo.pk)

    def test_s4_placa_inexistente(self):
        resp = self.api.get("/transporte/kiosco/vehiculo/ZZZ999/")
        self.assertEqual(resp.status_code, 400)

    def test_s4_eliminada_no_se_considera(self):
        self._salida(self.vehiculo, timezone.localdate(), EstadoSalida.ELIMINADO)
        data = self.api.get("/transporte/kiosco/vehiculo/KIO123/").json()["data"]
        self.assertIsNone(data["salida"])


class CuentaCobroTests(TestCase):
    """F5-1: cuenta de cobro imprimible (§5.7) — importe en servidor."""

    MES, ANIO = 10, 2026

    def _vehiculo(self, placa="CCB123"):
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

    def _salida(self, vehiculo, dia, estado, valor="85000"):
        return Salida.objects.create(
            vehiculo=vehiculo,
            fecha_salida=date(self.ANIO, self.MES, dia),
            valor_dia=Decimal(valor),
            estado=estado,
        )

    def _cuenta(self, vehiculo=None, mes=MES, anio=ANIO):
        return InformeService.cuenta_cobro(
            (vehiculo or self._vehiculo()).placa, mes, anio
        )

    # --------------------------- cálculo ---------------------------- #
    def test_importe_calculado_en_servidor(self):
        vehiculo = self._vehiculo()
        for dia in (1, 2, 3):
            self._salida(vehiculo, dia, EstadoSalida.APROBADO)
        datos = self._cuenta(vehiculo)
        self.assertEqual(datos["total_dias"], 3)
        # valor_base = 3 × 85000 = 255000; retefuente 1% = 2550;
        # pagar = 255000 − 2550 = 252450 (fórmula de la sábana).
        self.assertEqual(datos["valor_base"], Decimal("255000"))
        self.assertEqual(datos["retefuente"], Decimal("2550.00"))
        self.assertEqual(datos["pagar"], Decimal("252450.00"))

    def test_novedad_adicional_suma(self):
        vehiculo = self._vehiculo()
        salida = self._salida(vehiculo, 5, EstadoSalida.APROBADO)
        Novedad.objects.create(
            salida=salida, tipo=TipoNovedad.ADICIONAL,
            valor=Decimal("10000"), descripcion="adicional",
        )
        self.assertEqual(self._cuenta(vehiculo)["valor_base"], Decimal("95000"))

    def test_novedad_descuento_resta(self):
        vehiculo = self._vehiculo()
        salida = self._salida(vehiculo, 5, EstadoSalida.APROBADO)
        Novedad.objects.create(
            salida=salida, tipo=TipoNovedad.DESCUENTO,
            valor=Decimal("5000"), descripcion="descuento",
        )
        self.assertEqual(self._cuenta(vehiculo)["valor_base"], Decimal("80000"))

    def test_eliminadas_excluidas(self):
        vehiculo = self._vehiculo()
        self._salida(vehiculo, 1, EstadoSalida.APROBADO)
        self._salida(vehiculo, 2, EstadoSalida.ELIMINADO)
        self.assertEqual(self._cuenta(vehiculo)["total_dias"], 1)

    def test_periodo_diferente_no_suma(self):
        vehiculo = self._vehiculo()
        self._salida(vehiculo, 1, EstadoSalida.APROBADO)
        # Noviembre no debe sumar nada de octubre.
        self.assertEqual(self._cuenta(vehiculo, mes=11)["total_dias"], 0)

    def test_dia_siguiente_del_mes_no_cuenta(self):
        """Borde semiabierto [desde, hasta): el día 1 del mes siguiente
        no se cuela en el mes pedido."""
        vehiculo = self._vehiculo()
        self._salida(vehiculo, 1, EstadoSalida.APROBADO)
        Salida.objects.create(
            vehiculo=vehiculo,
            fecha_salida=date(self.ANIO, self.MES + 1, 1),
            valor_dia=Decimal("85000"), estado=EstadoSalida.APROBADO,
        )
        self.assertEqual(self._cuenta(vehiculo)["total_dias"], 1)

    def test_placa_inexistente_error(self):
        with self.assertRaises(ValueError):
            InformeService.cuenta_cobro("ZZZ999", self.MES, self.ANIO)

    # ---------------------------- pagador ---------------------------- #
    def test_pagador_desde_datos_bancarios(self):
        vehiculo = self._vehiculo()
        DatosBancariosVehiculo.objects.create(
            vehiculo=vehiculo, cedula_titular="888777666",
            nombre_titular="TITULAR BANCO", banco="BOGOTA",
            tipo_cuenta="AHORROS", numero_cuenta="12345",
        )
        datos = self._cuenta(vehiculo)
        self.assertEqual(datos["cedula_pago"], "888777666")
        self.assertEqual(datos["nombre_pago"], "TITULAR BANCO")
        self.assertEqual(datos["banco"], "BOGOTA")
        self.assertEqual(datos["cuenta_pago"], "12345")

    def test_pagador_fallback_propietario(self):
        vehiculo = self._vehiculo()
        datos = self._cuenta(vehiculo)
        self.assertEqual(datos["nombre_pago"], "CINCO SAS")
        self.assertEqual(datos["cedula_pago"], "900111222")
        self.assertEqual(datos["cuenta_pago"], "")

    def test_consecutivo_del_periodo(self):
        vehiculo = self._vehiculo()
        ConsecutivoMensual.objects.create(
            vehiculo=vehiculo, mes=self.MES, anio=self.ANIO, consecutivo=1042
        )
        self.assertEqual(self._cuenta(vehiculo)["consecutivo"], 1042)

    # ------------------------------ HTTP ----------------------------- #
    def setUp(self):
        self.user = User.objects.create_user(username="1000111", password="x")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _get(self, **extra):
        params = {"placa": "CCB123", "mes": self.MES, "anio": self.ANIO}
        params.update(extra)
        return self.api.get("/transporte/informes/cuenta-cobro/", params)

    def test_html_imprimible(self):
        vehiculo = self._vehiculo()
        for dia in (1, 2):
            self._salida(vehiculo, dia, EstadoSalida.APROBADO)
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp["Content-Type"])
        html = resp.content.decode()
        self.assertIn("CCB123", html)
        self.assertIn("OCTUBRE", html)
        self.assertIn("COMPAÑÍA INTEGRAL NEGOCIOS DE COLOMBIA", html)
        # 2 × 85000 = 170000; rete 1700; pagar 168300 → "168.300".
        self.assertIn("168.300", html)

    def test_seguridad_importe_no_viende_del_cliente(self):
        """El legacy imprimía `pagar`/`banco` desde campos ocultos del
        formulario: alterables desde el navegador. Aquí se ignoran."""
        vehiculo = self._vehiculo()
        self._salida(vehiculo, 1, EstadoSalida.APROBADO)
        resp = self._get(pagar="999999", banco="HACKED", nombre_pago="OTRO")
        html = resp.content.decode()
        self.assertNotIn("999999", html)
        self.assertNotIn("HACKED", html)
        self.assertNotIn("OTRO", html)
        # En cambio sí está el importe del servidor (85000 − 850 = 84150).
        self.assertIn("84.150", html)

    def test_periodo_invalido_http(self):
        self.assertEqual(self._get(mes=13).status_code, 400)
        self.assertEqual(self._get(anio=1999).status_code, 400)

    def test_placa_inexistente_http(self):
        resp = self.api.get(
            "/transporte/informes/cuenta-cobro/",
            {"placa": "ZZZ999", "mes": self.MES, "anio": self.ANIO},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("no encontrado", resp.json()["error"])


class SeriesChartTests(TestCase):
    """F5-2: gráfico "Pagos por Mes, por Área" (§5.7, legacy series_chart)."""

    def _vehiculo(self):
        return FlotaService.crear(
            {
                "placa": "GRA123",
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

    def _salida(self, vehiculo, fecha, area, estado, valor):
        return Salida.objects.create(
            vehiculo=vehiculo, fecha_salida=fecha, area=area,
            valor_dia=Decimal(valor), estado=estado,
        )

    def _por_area(self, anio=None):
        serie = InformeService.series_chart(anio)
        return {s["name"]: s for s in serie["series"]}

    def test_agrupa_por_area_y_mes(self):
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2026, 1, 5), "OPERACIONES", EstadoSalida.APROBADO, "100000")
        self._salida(vehiculo, date(2026, 1, 10), "OPERACIONES", EstadoSalida.APROBADO, "200000")
        self._salida(vehiculo, date(2026, 2, 5), "OPERACIONES", EstadoSalida.APROBADO, "50000")
        self._salida(vehiculo, date(2026, 1, 5), "LOGISTICA", EstadoSalida.APROBADO, "70000")
        areas = self._por_area()
        self.assertEqual(
            areas["OPERACIONES"]["points"],
            [["1/1/2026", 300000], ["2/1/2026", 50000]],
        )
        self.assertEqual(areas["LOGISTICA"]["points"], [["1/1/2026", 70000]])

    def test_novedad_ajusta_el_valor(self):
        vehiculo = self._vehiculo()
        salida = self._salida(
            vehiculo, date(2026, 3, 5), "OPERACIONES", EstadoSalida.APROBADO, "100000"
        )
        Novedad.objects.create(
            salida=salida, tipo=TipoNovedad.ADICIONAL,
            valor=Decimal("20000"), descripcion="adicional",
        )
        self.assertEqual(
            self._por_area()["OPERACIONES"]["points"], [["3/1/2026", 120000]]
        )

    def test_solo_validado_y_aprobado(self):
        """Como el legacy post-01/08/2024: no cuentan REPORTADO/RECHAZADO."""
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2026, 1, 5), "OPERACIONES", EstadoSalida.APROBADO, "100000")
        self._salida(vehiculo, date(2026, 1, 6), "OPERACIONES", EstadoSalida.VALIDADO, "50000")
        self._salida(vehiculo, date(2026, 1, 7), "OPERACIONES", EstadoSalida.REPORTADO, "99999")
        self._salida(vehiculo, date(2026, 1, 8), "OPERACIONES", EstadoSalida.RECHAZADO, "99999")
        self._salida(vehiculo, date(2026, 1, 9), "OPERACIONES", EstadoSalida.ELIMINADO, "99999")
        self.assertEqual(
            self._por_area()["OPERACIONES"]["points"], [["1/1/2026", 150000]]
        )

    def test_anio_filtra(self):
        """Corrección del hardcode `execute([2024])` del legacy."""
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2025, 1, 5), "OPERACIONES", EstadoSalida.APROBADO, "10000")
        self._salida(vehiculo, date(2026, 1, 5), "OPERACIONES", EstadoSalida.APROBADO, "20000")
        self.assertEqual(self._por_area(2025)["OPERACIONES"]["points"], [["1/1/2025", 10000]])
        self.assertEqual(self._por_area(2026)["OPERACIONES"]["points"], [["1/1/2026", 20000]])
        # Sin año: todo el histórico.
        self.assertEqual(len(self._por_area()["OPERACIONES"]["points"]), 2)

    def test_im_va_al_eje_secundario(self):
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2026, 1, 5), "I&M", EstadoSalida.APROBADO, "100000")
        serie_im = self._por_area()["I&M"]
        self.assertEqual(serie_im["yAxis"], "a2")
        self.assertEqual(serie_im["defaultPoint"]["type"], "line")
        self.assertEqual(serie_im["defaultPoint"]["marker"]["type"], "circle")
        self.assertEqual(serie_im["points"], [["1/1/2026", 100000]])

    def test_area_vacia_excluida(self):
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2026, 1, 5), "", EstadoSalida.APROBADO, "100000")
        self.assertEqual(self._por_area(), {})

    def test_http_series_chart(self):
        vehiculo = self._vehiculo()
        self._salida(vehiculo, date(2026, 1, 5), "OPERACIONES", EstadoSalida.APROBADO, "100000")
        user = User.objects.create_user(username="1000222", password="x")
        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.get("/transporte/informes/series-chart/", {"anio": 2026})
        self.assertEqual(resp.status_code, 200)
        serie = resp.json()["data"]["series"]
        self.assertEqual(serie[0]["name"], "OPERACIONES")
        self.assertEqual(serie[0]["points"], [["1/1/2026", 100000]])

    def test_http_anio_invalido(self):
        user = User.objects.create_user(username="1000333", password="x")
        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.get("/transporte/informes/series-chart/", {"anio": 1999})
        self.assertEqual(resp.status_code, 400)


class InformeMensualTests(TestCase):
    """F5-3: informe mensual día a día con filtros server-side (§5.7)."""

    MES, ANIO = 10, 2026

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()  # SalidaSerializer toca Empleado (B15)
        super().setUpClass()

    def setUp(self):
        self.user = User.objects.create_user(username="1000444", password="x")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.vehiculo = FlotaService.crear(
            {
                "placa": "INF123",
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

    def _salida(self, dia, estado=EstadoSalida.APROBADO, area="OPERACIONES",
                sede="MEDELLIN", placa=None):
        vehiculo = self.vehiculo
        if placa:
            vehiculo = FlotaService.crear(
                {
                    "placa": placa, "tipo_vehiculo": "CAMIONETA", "marca": "MAZDA",
                    "referencia": "CX5", "modelo_anio": 2022,
                    "tipo_contrato": "PROPIO", "nombre_propietario": "CINCO SAS",
                    "cedula_propietario": "900111222", "valor_dia_base": 85000,
                    "fecha_soat": date(2027, 1, 1), "fecha_cda": date(2026, 11, 15),
                },
                actor=None,
            )
        return Salida.objects.create(
            vehiculo=vehiculo, fecha_salida=date(self.ANIO, self.MES, dia),
            area=area, sede=sede, valor_dia=Decimal("85000"), estado=estado,
        )

    def _mes(self, **filtros):
        params = {"mes": self.MES, "anio": self.ANIO}
        params.update(filtros)
        return self.api.get("/transporte/informes/mensual/", params).json()

    def test_mes_filtra_y_excluye_eliminadas(self):
        self._salida(1)
        self._salida(2, estado=EstadoSalida.ELIMINADO)
        # Noviembre (mes siguiente) no debe aparecer.
        Salida.objects.create(
            vehiculo=self.vehiculo, fecha_salida=date(2026, 11, 1),
            area="OPERACIONES", sede="MEDELLIN", valor_dia=Decimal("85000"),
            estado=EstadoSalida.APROBADO,
        )
        results = self._mes()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["fecha_salida"], "2026-10-01")

    def test_orden_dia_a_ascendente(self):
        self._salida(10)
        self._salida(3)
        self._salida(7)
        fechas = [r["fecha_salida"] for r in self._mes()["results"]]
        self.assertEqual(fechas, ["2026-10-03", "2026-10-07", "2026-10-10"])

    def test_estado_explicito_puede_incluir_eliminadas(self):
        self._salida(1, estado=EstadoSalida.REPORTADO)
        self._salida(2, estado=EstadoSalida.APROBADO)
        self.assertEqual(len(self._mes(estado="REPORTADO")["results"]), 1)
        self.assertEqual(len(self._mes(estado="ELIMINADO")["results"]), 0)
        self.assertEqual(len(self._mes()["results"]), 2)

    def test_filtros_sede_y_area(self):
        self._salida(1, area="OPERACIONES", sede="MEDELLIN")
        self._salida(2, area="LOGISTICA", sede="BOGOTA")
        self.assertEqual(len(self._mes(area="LOGISTICA")["results"]), 1)
        self.assertEqual(len(self._mes(sede="BOGOTA")["results"]), 1)
        self.assertEqual(len(self._mes(area="LOGISTICA", sede="MEDELLIN")["results"]), 0)

    def test_search_por_placa(self):
        self._salida(1, placa="OTR789")
        self.assertEqual(len(self._mes(search="OTR789")["results"]), 1)
        self.assertEqual(len(self._mes(search="ZZZ")["results"]), 0)

    def test_areas_del_periodo(self):
        self._salida(1, area="OPERACIONES")
        self._salida(2, area="LOGISTICA")
        self._salida(3, area="OPERACIONES")
        self._salida(4, area="")
        resp = self.api.get(
            "/transporte/informes/areas/", {"mes": self.MES, "anio": self.ANIO}
        ).json()
        self.assertEqual(resp["data"]["areas"], ["LOGISTICA", "OPERACIONES"])

    def test_expose_placa_y_total(self):
        self._salida(1)
        fila = self._mes()["results"][0]
        self.assertEqual(fila["vehiculo_placa"], "INF123")
        self.assertEqual(float(fila["total_a_pagar"]), 85000.0)

    def test_periodo_invalido(self):
        resp = self.api.get("/transporte/informes/mensual/", {"mes": 13, "anio": 2026})
        self.assertEqual(resp.status_code, 400)
        resp = self.api.get("/transporte/informes/areas/", {"mes": 10, "anio": 1999})
        self.assertEqual(resp.status_code, 400)


class ExportTests(TestCase):
    """F5-4: export server-side xlsx/csv (fila B4, §5.7)."""

    @classmethod
    def setUpClass(cls):
        # listar() hace prefetch_related(tecnico_asignado) → FK a Empleado
        # (azul). En tests el router está desactivado, así que la tabla debe
        # existir en la BD de prueba para que el prefetch funcione.
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        self.user = User.objects.create_user(username="1000555", password="x")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.vehiculo = FlotaService.crear(
            {
                "placa": "EXP123", "tipo_vehiculo": "CAMIONETA", "marca": "MAZDA",
                "referencia": "CX5", "modelo_anio": 2022, "tipo_contrato": "PROPIO",
                "nombre_propietario": "CINCO SAS", "cedula_propietario": "900111222",
                "valor_dia_base": 85000, "fecha_soat": date(2027, 1, 1),
                "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )

    def _salida(self, dia, estado=EstadoSalida.APROBADO):
        return Salida.objects.create(
            vehiculo=self.vehiculo, fecha_salida=date(2026, 10, dia),
            area="OPERACIONES", valor_dia=Decimal("85000"), estado=estado,
        )

    def _get(self, **params):
        return self.api.get("/transporte/salidas/export/", params)

    def test_xlsx_con_filas_y_numeros_reales(self):
        self._salida(1)
        resp = self._get(formato="xlsx")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheetml", resp["Content-Type"])
        self.assertIn('attachment; filename="salidas.xlsx"', resp["Content-Disposition"])
        self.assertTrue(resp.content.startswith(b"PK"))  # es un zip
        libro = load_workbook(io.BytesIO(resp.content))
        filas = list(libro.active.iter_rows(values_only=True))
        self.assertEqual(filas[0][1], "PLACA")
        self.assertEqual(filas[1][1], "EXP123")
        # VALOR DIA y TOTAL A PAGAR quedan como número real, no texto.
        self.assertEqual(filas[1][7], 85000.0)
        self.assertEqual(filas[1][10], 85000.0)

    def test_csv_con_bom_y_separador_punto_y_coma(self):
        self._salida(1)
        resp = self._get(formato="csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertTrue(resp.content.startswith(b"\xef\xbb\xbf"))  # BOM utf-8
        texto = resp.content.decode("utf-8-sig")
        self.assertIn("FECHA;PLACA", texto)
        self.assertIn("EXP123", texto)

    def test_filtros_server_side(self):
        self._salida(1, EstadoSalida.APROBADO)
        self._salida(2, EstadoSalida.ELIMINADO)
        # Sin estado se excluyen las eliminadas: cabecera + 1 fila.
        lineas = self._get(formato="csv").content.decode("utf-8-sig").strip().splitlines()
        self.assertEqual(len(lineas), 2)
        # Filtro por estado explícito.
        lineas = self._get(formato="csv", estado="ELIMINADO").content.decode("utf-8-sig").strip().splitlines()
        self.assertEqual(len(lineas), 2)
        self.assertIn("ELIMINADO", lineas[1])

    def test_formato_no_soportado(self):
        self.assertEqual(self._get(formato="pdf").status_code, 400)

    def test_csv_con_novedad(self):
        salida = self._salida(1)
        Novedad.objects.create(
            salida=salida, tipo=TipoNovedad.DESCUENTO,
            valor=Decimal("5000"), descripcion="descuento",
        )
        texto = self._get(formato="csv").content.decode("utf-8-sig")
        self.assertIn("DESCUENTO", texto)
        self.assertIn("80000.00", texto)  # 85000 − 5000


# ═════════════════════════════════════════════════════════════════════════════
# §5.7 / F5-7: Agregados de sábana
# ═════════════════════════════════════════════════════════════════════════════

class InformeAgregadosTests(TestCase):
    """F5-7: agregados server-side de la sábana (día, área, matriz,
    nómina y liquidación por placa), portados del JS de la sábana."""

    def setUp(self):
        self.vehiculo = FlotaService.crear(
            {
                "placa": "AGR100", "tipo_vehiculo": "CAMIONETA",
                "marca": "MAZDA", "referencia": "CX5", "modelo_anio": 2022,
                "tipo_contrato": "PROPIO", "nombre_propietario": "CINCO SAS",
                "cedula_propietario": "900111222", "valor_dia_base": 100000,
                "fecha_soat": date(2027, 1, 1), "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )
        self.externo = FlotaService.crear(
            {
                "placa": "AGR200", "tipo_vehiculo": "FURGON",
                "marca": "CHEVROLET", "referencia": "NKR", "modelo_anio": 2021,
                "tipo_contrato": "EXTERNO", "nombre_propietario": "TERCERO",
                "cedula_propietario": "800111222", "valor_dia_base": 80000,
                "fecha_soat": date(2027, 1, 1), "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )
        self.renting = FlotaService.crear(
            {
                "placa": "AGR300", "tipo_vehiculo": "VANS_CARGA",
                "marca": "RENAULT", "referencia": "KANGOO", "modelo_anio": 2023,
                "tipo_contrato": "RENTING", "nombre_propietario": "ARRENDADORA",
                "cedula_propietario": "700111222", "valor_dia_base": 90000,
                "fecha_soat": date(2027, 1, 1), "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )

    def _salida(self, vehiculo, dia, estado, area="OPERACIONES",
                carpeta="LOGISTICA", valor="100000"):
        return Salida.objects.create(
            vehiculo=vehiculo, fecha_salida=dia, area=area, carpeta=carpeta,
            valor_dia=Decimal(valor), estado=estado,
        )

    def _area(self, datos, nombre):
        return next(a for a in datos["areas"] if a["area"] == nombre)

    # ------------------------------ por_dia ----------------------------- #
    def test_por_dia_agrupa_area_y_carpeta(self):
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        self._salida(self.externo, date(2026, 10, 5), EstadoSalida.REPORTADO,
                     carpeta="ASEO")
        self._salida(self.vehiculo, date(2026, 10, 6), EstadoSalida.APROBADO)
        datos = InformeService.por_dia(date(2026, 10, 5))
        area = self._area(datos, "OPERACIONES")
        self.assertEqual(area["propios"], 1)
        self.assertEqual(area["externos"], 1)
        self.assertEqual(area["total_vehi"], 2)
        self.assertEqual(area["total_dia"], 200000)
        # arr_estado: "reportado" es el estado REPORTADO.
        self.assertEqual(area["arr_estado"]["aprobado"]["cnt"], 1)
        self.assertEqual(area["arr_estado"]["reportado"]["cnt"], 1)
        self.assertEqual(area["arr_estado"]["total"]["cnt"], 2)
        carpetas = {c["carpeta"]: c for c in area["carpetas"]}
        self.assertEqual(set(carpetas), {"LOGISTICA", "ASEO"})
        self.assertEqual(carpetas["ASEO"]["externos"], 1)

    def test_por_dia_excluye_eliminado_y_fallbacks(self):
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.ELIMINADO)
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO,
                     area="", carpeta="")
        datos = InformeService.por_dia(date(2026, 10, 5))
        self.assertEqual(len(datos["areas"]), 1)
        area = datos["areas"][0]
        self.assertEqual(area["area"], "SIN AREA")
        self.assertEqual(area["carpetas"][0]["carpeta"], "SIN CARPETA")
        self.assertEqual(area["total_vehi"], 1)

    def test_por_dia_novedad_ajusta_valor(self):
        salida = self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        Novedad.objects.create(
            salida=salida, tipo=TipoNovedad.ADICIONAL,
            valor=Decimal("15000"), descripcion="adicional",
        )
        datos = InformeService.por_dia(date(2026, 10, 5))
        self.assertEqual(datos["areas"][0]["total_dia"], Decimal("115000.00"))

    def test_por_dia_separa_renting_de_propios(self):
        """RENTING ya no se cuenta dentro de `propios` (refactor vs legacy)."""
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        self._salida(self.renting, date(2026, 10, 5), EstadoSalida.APROBADO)
        self._salida(self.externo, date(2026, 10, 5), EstadoSalida.APROBADO)
        area = self._area(InformeService.por_dia(date(2026, 10, 5)), "OPERACIONES")
        self.assertEqual(area["propios"], 1)
        self.assertEqual(area["renting"], 1)
        self.assertEqual(area["externos"], 1)
        self.assertEqual(area["total_vehi"], 3)

    def test_por_dia_importes_con_decimales(self):
        """Los importes conservan centavos (el legacy los truncaba a entero)."""
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO,
                     valor="1000.25")
        area = self._area(InformeService.por_dia(date(2026, 10, 5)), "OPERACIONES")
        self.assertEqual(area["total_dia"], Decimal("1000.25"))
        self.assertEqual(area["arr_estado"]["aprobado"]["valor"], Decimal("1000.25"))
        self.assertEqual(area["arr_estado"]["total"]["valor"], Decimal("1000.25"))

    # ------------------------------ por_area ---------------------------- #
    def test_por_area_mes_y_solo_aprobados(self):
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        self._salida(self.vehiculo, date(2026, 10, 6), EstadoSalida.VALIDADO)
        self._salida(self.vehiculo, date(2026, 10, 7), EstadoSalida.REPORTADO)
        completo = InformeService.por_area(10, 2026)
        area = self._area(completo, "OPERACIONES")
        self.assertEqual(area["total_vehi"], 3)
        self.assertEqual(area["total_dia"], 300000)
        # solo_aprobados: los totales bajan a APROBADO/VALIDADO…
        solo = self._area(
            InformeService.por_area(10, 2026, solo_aprobados=True),
            "OPERACIONES",
        )
        self.assertEqual(solo["total_vehi"], 2)
        self.assertEqual(solo["total_dia"], 200000)
        # …pero arr_estado sigue reflejando todas las filas (JS 2860–2909).
        self.assertEqual(solo["arr_estado"]["reportado"]["cnt"], 1)
        self.assertEqual(solo["arr_estado"]["total"]["cnt"], 3)

    def test_por_area_excluye_otro_mes(self):
        self._salida(self.vehiculo, date(2026, 9, 30), EstadoSalida.APROBADO)
        self._salida(self.vehiculo, date(2026, 10, 1), EstadoSalida.APROBADO)
        area = self._area(InformeService.por_area(10, 2026), "OPERACIONES")
        self.assertEqual(area["total_vehi"], 1)

    # ---------------------------- areas_por_mes ------------------------- #
    def test_areas_por_mes_matriz(self):
        self._salida(self.vehiculo, date(2026, 1, 5), EstadoSalida.APROBADO)
        self._salida(self.externo, date(2026, 1, 6), EstadoSalida.REPORTADO)
        self._salida(self.vehiculo, date(2026, 3, 5), EstadoSalida.ELIMINADO)
        matriz = InformeService.areas_por_mes(2026)
        area = self._area(matriz, "OPERACIONES")
        self.assertEqual(len(area["meses"]), 1)  # ELIMINADO excluido
        mes = area["meses"][0]
        self.assertEqual(mes["mes"], 1)
        self.assertEqual(mes["propios"], 1)
        self.assertEqual(mes["externos"], 1)
        self.assertEqual(mes["total_dia"], 200000)

    def test_areas_por_mes_anio_invalido(self):
        with self.assertRaises(ValueError):
            InformeService.areas_por_mes(1999)

    # -------------------------------- nómina ---------------------------- #
    def test_nomina_excluye_reportado_y_calcula_rete(self):
        DatosBancariosVehiculo.objects.create(
            vehiculo=self.vehiculo, cedula_titular="900111222",
            nombre_titular="CINCO SAS", tipo_cuenta="AHORRO",
            banco="BANCO", numero_cuenta="1234567890",
        )
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        self._salida(self.vehiculo, date(2026, 10, 6), EstadoSalida.VALIDADO)
        self._salida(self.vehiculo, date(2026, 10, 7), EstadoSalida.REPORTADO)
        self._salida(self.externo, date(2026, 10, 5), EstadoSalida.APROBADO)
        datos = InformeService.nomina(10, 2026)
        filas = {f["placa"]: f for f in datos["filas"]}
        # REPORTADO excluido: 2 días del propio + 1 del externo.
        self.assertEqual(filas["AGR100"]["total_dias"], 2)
        self.assertEqual(filas["AGR100"]["valor_base"], Decimal("200000"))
        self.assertEqual(filas["AGR100"]["rte"], Decimal("2000.00"))
        self.assertEqual(filas["AGR100"]["total_pagar"], Decimal("198000.00"))
        # Pagador del dato bancario en servidor (CR-13).
        self.assertEqual(filas["AGR100"]["cedula_pago"], "900111222")
        self.assertEqual(filas["AGR100"]["nombre_pago"], "CINCO SAS")
        self.assertEqual(filas["AGR200"]["total_dias"], 1)

    def test_nomina_agrupa_por_carpeta(self):
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        self._salida(self.vehiculo, date(2026, 10, 6), EstadoSalida.APROBADO,
                     carpeta="ASEO")
        datos = InformeService.nomina(10, 2026)
        self.assertEqual(len(datos["filas"]), 2)  # MISMA placa, 2 carpetas

    # -------------------------- liquidación_placa ----------------------- #
    def test_liquidacion_por_placa(self):
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        salida = self._salida(self.vehiculo, date(2026, 10, 6), EstadoSalida.VALIDADO)
        Novedad.objects.create(
            salida=salida, tipo=TipoNovedad.DESCUENTO,
            valor=Decimal("10000"), descripcion="descuento",
        )
        self._salida(self.vehiculo, date(2026, 10, 7), EstadoSalida.REPORTADO)
        datos = InformeService.liquidacion_placa(10, 2026)
        self.assertEqual(len(datos["filas"]), 1)
        fila = datos["filas"][0]
        self.assertEqual(fila["placa"], "AGR100")
        self.assertEqual(fila["total_dias"], 2)  # REPORTADO excluido
        self.assertEqual(fila["valor_dia"], 100000)
        # valor_base = 100000 + (100000 − 10000 descuento).
        self.assertEqual(fila["valor_base"], Decimal("190000"))
        self.assertEqual(fila["rte"], Decimal("1900.00"))
        self.assertEqual(fila["pagar"], Decimal("188100.00"))
        self.assertEqual(fila["propietario"], "CINCO SAS")
        self.assertEqual(fila["consecutivo"], "")

    # ------------------------------ endpoints --------------------------- #
    def _api(self):
        user = User.objects.create_user(
            username="agr%s" % User.objects.count(), password="x"
        )
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    def test_endpoints_agregados(self):
        self._salida(self.vehiculo, date(2026, 10, 5), EstadoSalida.APROBADO)
        api = self._api()
        casos = [
            ("/transporte/informes/dia/", {"fecha": "2026-10-05"}),
            ("/transporte/informes/area/", {"mes": 10, "anio": 2026}),
            ("/transporte/informes/areas-mes/", {"anio": 2026}),
            ("/transporte/informes/nomina/", {"mes": 10, "anio": 2026}),
            ("/transporte/informes/liquidacion/", {"mes": 10, "anio": 2026}),
        ]
        for ruta, params in casos:
            resp = api.get(ruta, params)
            self.assertEqual(resp.status_code, 200, ruta)
            self.assertTrue(resp.json()["ok"], ruta)

    def test_endpoints_agregados_validan_entrada(self):
        api = self._api()
        self.assertEqual(
            api.get("/transporte/informes/dia/", {"fecha": "no-fecha"}).status_code,
            400,
        )
        self.assertEqual(
            api.get("/transporte/informes/area/", {"mes": 13, "anio": 2026}).status_code,
            400,
        )
        self.assertEqual(
            api.get("/transporte/informes/areas-mes/", {"anio": 1999}).status_code,
            400,
        )


class WfmVentanaTests(SimpleTestCase):
    """F5-5: ventana del WFM (legacy ResolveRange 24–66).

    Se usa la semana del 9 al 13 de noviembre de 2026 (lunes a viernes,
    sin festivos colombianos) para que el recuento de días hábiles sea
    predecible; el test de festivo lo cubre aparte.
    """

    HOY = date(2026, 11, 11)  # miércoles

    def test_limite_inferior_sin_finde(self):
        # miércoles 11 → martes 10 → lunes 9.
        self.assertEqual(
            WfmService.limite_inferior(self.HOY), date(2026, 11, 9)
        )

    def test_limite_inferior_cruza_finde(self):
        # lunes 16 → salta domingo 15 y sábado 14 → viernes 13 → jueves 12.
        self.assertEqual(
            WfmService.limite_inferior(date(2026, 11, 16)), date(2026, 11, 12)
        )

    def test_limite_inferior_salta_festivo(self):
        """El 12 de octubre es festivo (Día de la Raza): el legacy bloquea
        `$esSab`, `$esDom` Y `$esFest` (líneas 13–17)."""
        # miércoles 14 oct → martes 13 (1) → lunes 12 FESTIVO → viernes 9 (2).
        self.assertEqual(
            WfmService.limite_inferior(date(2026, 10, 14)), date(2026, 10, 9)
        )

    def test_limite_superior_incluye_hoy(self):
        self.assertEqual(
            WfmService.limite_superior(self.HOY), date(2026, 11, 12)
        )

    def test_resolver_rango_por_defecto_es_la_ventana(self):
        self.assertEqual(
            WfmService.resolver_rango(hoy=self.HOY),
            (date(2026, 11, 9), date(2026, 11, 12)),
        )

    def test_resolver_rango_explícito_se_acota_a_la_ventana(self):
        desde, hasta = WfmService.resolver_rango(
            fecha_inicio=date(2026, 11, 1), fecha_fin=date(2026, 11, 30),
            hoy=self.HOY,
        )
        self.assertEqual(desde, date(2026, 11, 9))
        self.assertEqual(hasta, date(2026, 11, 12))

    def test_resolver_rango_excluye_el_día_siguiente(self):
        """La fecha fin del POST es INCLUSIVA → se vuelve semiabierta."""
        desde, hasta = WfmService.resolver_rango(
            fecha_inicio=date(2026, 11, 10), fecha_fin=date(2026, 11, 10),
            hoy=self.HOY,
        )
        self.assertEqual((desde, hasta), (date(2026, 11, 10), date(2026, 11, 11)))

    def test_mes_fuera_de_la_ventana_rechaza(self):
        with self.assertRaisesMessage(ValueError, "no contiene fechas"):
            WfmService.resolver_rango(mes=8, yyyy=2026, hoy=self.HOY)

    def test_mes_invalido_no_rechaza_sino_que_usa_la_ventana(self):
        """Fiel al legado (44): `checkdate(13, 1, 2026)` es falso, así que
        la validación de mes se omite y el rango es la ventana normal."""
        self.assertEqual(
            WfmService.resolver_rango(mes=13, yyyy=2026, hoy=self.HOY),
            (date(2026, 11, 9), date(2026, 11, 12)),
        )

    def test_rango_invertido_rechaza(self):
        with self.assertRaisesMessage(ValueError, "no contiene fechas"):
            WfmService.resolver_rango(
                fecha_inicio=date(2026, 11, 20), fecha_fin=date(2026, 11, 21),
                hoy=self.HOY,
            )


class WfmServiceTests(TestCase):
    """F5-5: elegibilidad WFM, lote y cola de jobs."""

    @classmethod
    def setUpClass(cls):
        # WFM lee 3 tablas ajenas (cinco_base_de_personal,
        # residencial_base_wfm, logistica_actividades_modulo_agenda).
        _asegurar_tabla_empleados()
        _asegurar_tablas_wfm()
        super().setUpClass()

    def setUp(self):
        self.hoy = date(2026, 11, 11)  # miércoles; ventana [nov 9, nov 12)
        self.persona = Empleado.objects.create(
            cedula="111222333",
            codigo_sap="SAP-111222333",
            nombre="WFM",
            apellido="PRUEBA",
            area="OPERACIONES",
            carpeta="LOGISTICA",
            sede="MEDELLIN",
            movil="MOVIL-77",
            password="",
        )
        self.vehiculo = FlotaService.crear(
            {
                "placa": "WFM001", "tipo_vehiculo": "CAMIONETA",
                "marca": "KIA", "referencia": "SPORTAGE", "modelo_anio": 2023,
                "tipo_contrato": "PROPIO", "nombre_propietario": "CINCO SAS",
                "cedula_propietario": "900111222", "valor_dia_base": 85000,
            },
            actor=None,
        )

    # ------------------------------ fixtures ----------------------------- #
    def _salida(self, dia=None, **extra):
        datos = {
            "vehiculo": self.vehiculo,
            "fecha_salida": dia or self.hoy,
            "area": "OPERACIONES",
            "carpeta": "LOGISTICA",
            "sede": "MEDELLIN",
            "valor_dia": Decimal("85000"),
            "estado": EstadoSalida.REPORTADO,
            "tecnico_asignado": self.persona,
        }
        datos.update(extra)
        return Salida.objects.create(**datos)

    def _vehiculo_nuevo(self, placa):
        return FlotaService.crear(
            {
                "placa": placa, "tipo_vehiculo": "CAMIONETA",
                "marca": "KIA", "referencia": "X", "modelo_anio": 2023,
                "tipo_contrato": "PROPIO", "nombre_propietario": "C",
                "cedula_propietario": "900111222", "valor_dia_base": 85000,
            },
            actor=None,
        )

    @staticmethod
    def _wfm(external_id="", cc_auxiliar="", dia=None):
        dia = dia or date(2026, 11, 11)
        return ResidencialWfm.objects.create(
            external_id=external_id or None,
            cc_auxiliar=cc_auxiliar or None,
            fecha=datetime(dia.year, dia.month, dia.day, 8, 0),
        )

    @staticmethod
    def _agenda(cedula="", movil="", dia=None):
        dia = dia or date(2026, 11, 11)
        return AgendaLogistica.objects.create(
            cedula=cedula or None,
            movil=movil or None,
            fecha=datetime(dia.year, dia.month, dia.day, 8, 0),
        )

    def _elegibles(self, **extra):
        return WfmService.elegibles(
            date(2026, 11, 9), date(2026, 11, 12), hoy=self.hoy, **extra
        )

    def _lote(self, **extra):
        return WfmService.aplicar_lote(
            date(2026, 11, 9), date(2026, 11, 12), hoy=self.hoy, **extra
        )

    # --------------------------- elegibilidad ---------------------------- #
    def test_sin_evidencia_no_es_elegible(self):
        salida = self._salida()
        self.assertNotIn(salida.pk, self._elegibles())

    def test_evidencia_wfm_por_cedula_hace_elegible(self):
        salida = self._salida()
        self._wfm(external_id="111222333")
        self.assertIn(salida.pk, self._elegibles())

    def test_evidencia_wfm_por_cc_auxiliar_hace_elegible(self):
        salida = self._salida()
        self._wfm(cc_auxiliar="111222333")
        self.assertIn(salida.pk, self._elegibles())

    def test_evidencia_wfm_en_otro_dia_no_cuenta(self):
        salida = self._salida()
        self._wfm(external_id="111222333", dia=date(2026, 10, 20))
        self.assertNotIn(salida.pk, self._elegibles())

    def test_agenda_es_respaldo_cuando_no_hay_wfm(self):
        salida = self._salida()
        self._agenda(cedula="111222333")
        self.assertIn(salida.pk, self._elegibles())

    def test_agenda_por_movil_tambien_respalda(self):
        salida = self._salida()
        self._agenda(movil="MOVIL-77")
        self.assertIn(salida.pk, self._elegibles())

    def test_agenda_por_fecha_cierre_tambien_respalda(self):
        """El legado mira `fecha` y `fecha_cierre` por igual (305–321)."""
        salida = self._salida()
        AgendaLogistica.objects.create(
            cedula="111222333",
            fecha_cierre=datetime(2026, 11, 11, 17, 0),
        )
        self.assertIn(salida.pk, self._elegibles())

    def test_cruce_movil_cedula_expande_identidades(self):
        """Una móvil identifica a TODAS sus cédulas (legacy 244–257).

        Dos personas distintas comparten la móvil MOVIL-77 (cesión o
        reemplazo). La salida solo registra a la primera; el WFM la
        valida por la evidencia de la SEGUNDA, que solo se alcanza
        cruzando contra `cinco_base_de_personal`.
        """
        Empleado.objects.create(
            cedula="555666777", codigo_sap="SAP-555666777",
            nombre="REEMPLAZO", apellido="TEMPORAL",
            area="OPERACIONES", carpeta="LOGISTICA", sede="MEDELLIN",
            movil="MOVIL-77", password="",
        )
        salida = self._salida()
        self._wfm(external_id="555666777")
        self.assertIn(salida.pk, self._elegibles())

    def test_sin_identidades_no_puede_expandirse(self):
        """Sin conductor ni técnico no hay NINGUNA identidad que buscar:
        el cruce no tiene con qué arrancar y la salida nunca califica."""
        salida = self._salida(tecnico_asignado=None)
        self._wfm(external_id="111222333")
        self.assertNotIn(salida.pk, self._elegibles())

    def test_personal_inactivo_no_expande(self):
        """El legacy solo usa personal `activo` (211)."""
        self.persona.estado = "INACTIVO"
        self.persona.save()
        salida = self._salida(tecnico_asignado=None)
        self._wfm(external_id="111222333")
        self.assertNotIn(salida.pk, self._elegibles())

    def test_solo_estados_reportado(self):
        salida = self._salida(estado=EstadoSalida.APROBADO)
        self._wfm(external_id="111222333")
        self.assertNotIn(salida.pk, self._elegibles())

    def test_filtro_por_area(self):
        salida = self._salida()
        self._wfm(external_id="111222333")
        self.assertIn(salida.pk, self._elegibles(area="OPERACIONES"))
        self.assertNotIn(salida.pk, self._elegibles(area="OTRA"))
        # 'TODAS'/'TODOS' no filtra (legacy 152).
        self.assertIn(salida.pk, self._elegibles(area="TODAS"))

    def test_solo_ventana_permitida(self):
        """Fuera de [hoy−2 hábiles, mañana) no se elige nada."""
        dentro = self._salida(dia=date(2026, 11, 9))
        self._wfm(external_id="111222333", dia=date(2026, 11, 9))
        self.assertIn(dentro.pk, self._elegibles())
        # El límite inferior de hoy (mié 11) es lunes 9: el 8 queda fuera.
        fuera = self._salida(
            dia=date(2026, 11, 8), vehiculo=self._vehiculo_nuevo("FUERA1")
        )
        self._wfm(external_id="111222333", dia=date(2026, 11, 8))
        self.assertNotIn(fuera.pk, self._elegibles())

    def test_limite_del_lote(self):
        """Nunca devuelve más de `limite` IDs (legacy 116)."""
        for dia in (date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 11)):
            self._salida(dia=dia, vehiculo=self._vehiculo_nuevo("LOT%s" % dia.day))
            self._wfm(external_id="111222333", dia=dia)
        self.assertEqual(len(self._elegibles()), 3)
        self.assertEqual(len(self._elegibles(limite=2)), 2)

    # ------------------------------ el lote ------------------------------ #
    def test_aplicar_lote_valida_y_registra_historial(self):
        salida = self._salida()
        self._wfm(external_id="111222333")
        resultado = self._lote(edit_cedula="111222333")
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)
        self.assertTrue(resultado["success"])
        self.assertEqual(resultado["updated_count"], 1)
        self.assertEqual(resultado["selected_count"], 1)
        self.assertFalse(resultado["has_more_in_chunk"])
        # Observación literal del legado (438).
        fila = salida.historial.filter(estado=EstadoSalida.VALIDADO).first()
        self.assertEqual(fila.motivo, "validado por sistema")

    def test_aplicar_lote_sin_registros_responde_legacy(self):
        self._salida()
        resultado = self._lote()
        self.assertFalse(resultado["success"])
        self.assertEqual(
            resultado["message"], "No se encontraron registros para validar"
        )
        self.assertEqual(resultado["updated_count"], 0)
        # La fecha fin que devuelve es INCLUSIVA (legacy 470).
        self.assertEqual(resultado["fecha_fin"], "2026-11-11")
        self.assertEqual(resultado["area"], "TODAS")
        self.assertEqual(resultado["total_reportados"], 1)

    def test_aplicar_lote_es_idempotente(self):
        self._salida()
        self._wfm(external_id="111222333")
        primera = self._lote()
        segunda = self._lote()
        self.assertEqual(primera["updated_count"], 1)
        self.assertEqual(segunda["updated_count"], 0)
        self.assertFalse(segunda["success"])

    def test_aplicar_lote_marca_has_more_in_chunk(self):
        """Si quedan salidas elegibles, el chunk se repite (legacy 464)."""
        for dia in (date(2026, 11, 10), date(2026, 11, 11)):
            self._salida(dia=dia, vehiculo=self._vehiculo_nuevo("HAY%s" % dia.day))
            self._wfm(external_id="111222333", dia=dia)
        resultado = self._lote(limite=1)
        self.assertEqual(resultado["updated_count"], 1)
        self.assertTrue(resultado["has_more_in_chunk"])

    def test_wfm_no_exige_rol_de_gestion(self):
        """El WFM es proceso autónomo: valida sin que nadie sea jefe."""
        salida = self._salida()
        self._wfm(external_id="111222333")
        self._lote(edit_cedula="000000000")
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)

    # ------------------------------ la cola ------------------------------ #
    def _correr_worker(self, job, **extra):
        """Simula el worker: reclama y procesa chunks hasta completar."""
        for _ in range(20):  # tope de seguridad contra bucles
            reclamado = WfmService.reclamar_job(job.job_uuid, "worker-1")
            if reclamado is None:
                break
            job = WfmService.procesar_job(reclamado, **extra)
            if job.estado == EstadoWfmJob.COMPLETADO:
                break
        return job

    def test_crear_job_y_reutilizar_vigente(self):
        job, reutilizado = WfmService.crear_job(
            mes=11, yyyy=2026, area="OPERACIONES",
            creado_por="111222333", hoy=self.hoy,
        )
        self.assertFalse(reutilizado)
        self.assertEqual(job.estado, EstadoWfmJob.PENDIENTE)
        self.assertEqual(job.fecha_inicio, date(2026, 11, 9))
        # fecha_fin es INCLUSIVA (legacy 168).
        self.assertEqual(job.fecha_fin, date(2026, 11, 11))
        self.assertEqual(job.total_dias, 3)

        otro, reutilizado = WfmService.crear_job(
            mes=11, yyyy=2026, area="OPERACIONES",
            creado_por="111222333", hoy=self.hoy,
        )
        self.assertTrue(reutilizado)
        self.assertEqual(otro.pk, job.pk)

    def test_obtener_job_por_uuid_inexistente(self):
        self.assertIsNone(WfmService.obtener_job("no-existe"))

    def test_reclamar_job_bloquea_segundo_worker(self):
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        reclamado = WfmService.reclamar_job(job.job_uuid, "worker-1")
        self.assertIsNotNone(reclamado)
        self.assertEqual(reclamado.estado, EstadoWfmJob.PROCESANDO)
        self.assertEqual(reclamado.locked_by, "worker-1")
        # Un segundo worker no lo toma si está fresco.
        self.assertIsNone(
            WfmService.reclamar_job(job.job_uuid, "worker-2", stale_after=60)
        )

    def test_reclamar_job_colgado_lo_retoma(self):
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        WfmService.reclamar_job(job.job_uuid, "worker-1")
        WfmJob.objects.filter(pk=job.pk).update(
            locked_at=timezone.now() - timedelta(seconds=300)
        )
        retomado = WfmService.reclamar_job(job.job_uuid, "worker-2", stale_after=60)
        self.assertIsNotNone(retomado)
        self.assertEqual(retomado.locked_by, "worker-2")

    # ------------------------- worker (H5) ------------------------- #
    def test_reclamar_siguiente_toma_el_unico_pendiente(self):
        """H5: ClaimNextJob legacy — la cola vacía devuelve None y un
        pendiente se reclama con precedencia PROCESANDO-huérfano."""
        self.assertIsNone(WfmService.reclamar_siguiente("worker-1"))
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        reclamado = WfmService.reclamar_siguiente("worker-1")
        self.assertIsNotNone(reclamado)
        self.assertEqual(reclamado.pk, job.pk)
        self.assertEqual(reclamado.estado, EstadoWfmJob.PROCESANDO)
        self.assertEqual(reclamado.locked_by, "worker-1")

    def test_reclamar_siguiente_prefiere_procesando_huerfano(self):
        """El legacy ordena PROCESANDO antes que PENDIENTE: retoma un
        job huérfano antes que encolar uno nuevo."""
        viejo, _ = WfmService.crear_job(
            mes=11, yyyy=2026, area="OPERACIONES", hoy=self.hoy
        )
        WfmService.reclamar_job(viejo.job_uuid, "worker-caido")
        WfmJob.objects.filter(pk=viejo.pk).update(
            locked_at=timezone.now() - timedelta(minutes=30)
        )
        # Otra área ⇒ otro job (crear_job reutiliza el vigente por área).
        nuevo, _ = WfmService.crear_job(
            mes=11, yyyy=2026, area="LOGISTICA", hoy=self.hoy
        )
        reclamado = WfmService.reclamar_siguiente("worker-2")
        self.assertEqual(reclamado.pk, viejo.pk)
        # El nuevo sigue esperando su turno.
        self.assertEqual(
            WfmJob.objects.get(pk=nuevo.pk).estado, EstadoWfmJob.PENDIENTE
        )

    def test_reclamar_siguiente_no_toma_lock_fresco(self):
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        WfmService.reclamar_job(job.job_uuid, "worker-1")
        # Lock recién puesto: otro worker no lo roba.
        self.assertIsNone(WfmService.reclamar_siguiente("worker-2"))

    def test_comando_wfm_worker_sin_jobs_da_mensaje(self):
        stdout = io.StringIO()
        call_command("wfm_worker", stdout=stdout)
        self.assertIn("No hay jobs pendientes", stdout.getvalue())

    def test_comando_wfm_worker_procesa_hasta_completar(self):
        """H5: el comando reclama y procesa chunks como el worker PHP
        (`chunkDays=1, batch=15`), pero con --hasta-completar corre
        todos los días del job en una sola pasada."""
        self._salida()
        self._wfm(external_id="111222333", dia=self.hoy)
        WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        stdout = io.StringIO()
        call_command("wfm_worker", "--hasta-completar", stdout=stdout)

        job = WfmJob.objects.get()
        self.assertEqual(job.estado, EstadoWfmJob.COMPLETADO)
        self.assertEqual(job.total_validados, 1)
        salida = Salida.objects.get()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)
        # La respuesta del worker es JSON por línea (legado CLI).
        cuerpo = json.loads(stdout.getvalue().strip().splitlines()[-1])
        self.assertTrue(cuerpo["success"])
        self.assertEqual(cuerpo["estado"], "COMPLETADO")

    def test_comando_wfm_worker_job_inexistente(self):
        with self.assertRaises(CommandError):
            call_command("wfm_worker", "--job", "no-existe", stdout=io.StringIO())

    def test_procesar_job_avanza_dia_a_dia_hasta_completar(self):
        """Un chunk es UN día (legacy `chunkDays = 1`): el worker itera."""
        for dia in (date(2026, 11, 9), date(2026, 11, 11)):
            self._salida(dia=dia, vehiculo=self._vehiculo_nuevo("PR%s" % dia.day))
            self._wfm(external_id="111222333", dia=dia)
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        final = self._correr_worker(job, edit_cedula="111222333")

        self.assertEqual(final.estado, EstadoWfmJob.COMPLETADO)
        self.assertEqual(final.total_validados, 2)
        self.assertEqual(final.total_reportados, 2)
        self.assertEqual(final.dias_procesados, 3)
        self.assertIsNotNone(final.finished_at)
        self.assertIsNone(final.fecha_cursor)
        self.assertEqual(
            Salida.objects.filter(estado=EstadoSalida.VALIDADO).count(), 2
        )

    def test_chunk_saturado_no_avanza_cursor(self):
        """Si el lote de un día no se vacía, el cursor NO avanza y el
        mismo día se reintenta (legacy 701–706)."""
        dia = date(2026, 11, 9)
        self._salida(dia=dia, vehiculo=self._vehiculo_nuevo("SAT1"))
        self._salida(dia=dia, vehiculo=self._vehiculo_nuevo("SAT2"))
        self._wfm(external_id="111222333", dia=dia)
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        job = WfmService.reclamar_job(job.job_uuid, "worker-1")

        procesado = WfmService.procesar_job(job, batch_size=1)
        self.assertEqual(procesado.estado, EstadoWfmJob.PROCESANDO)
        self.assertEqual(procesado.fecha_cursor, date(2026, 11, 9))
        self.assertEqual(procesado.total_validados, 1)

        # El resto se validan en las pasadas siguientes.
        final = self._correr_worker(WfmService.obtener_job(job.job_uuid))
        self.assertEqual(final.estado, EstadoWfmJob.COMPLETADO)
        self.assertEqual(final.total_validados, 2)

    def test_procesar_job_sin_evidencia_completa_en_cero(self):
        """Sin evidencia WFM ni agenda no se valida nada, pero el job
        avanza día a día hasta completarse (no queda colgado)."""
        self._salida()  # reportado pero sin evidencia
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        final = self._correr_worker(job)
        self.assertEqual(final.estado, EstadoWfmJob.COMPLETADO)
        self.assertEqual(final.total_validados, 0)
        self.assertEqual(final.dias_procesados, 3)

    def test_el_rango_del_job_no_se_reacota_al_procesarlo(self):
        """Corrección sobre el legado: `ApplyValidationChunk` reclamps el
        rango con el `hoy` del momento (75–83), así que un job cuyo rango
        quedó fuera de la ventana del día NO perdería sus primeros días
        en silencio aquí.

        Este test lo materializa: el job cubre noviembre mientras el
        `hoy` real del entorno es octubre, y aun así valida."""
        salida = self._salida()
        self._wfm(external_id="111222333")
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        # Sin `hoy` forzado: `aplicar_lote` usaría el `hoy` REAL (octubre).
        final = self._correr_worker(job)
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)
        self.assertEqual(final.total_validados, 1)

    def test_fallar_job(self):
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        fallado = WfmService.fallar_job(job, "boom")
        self.assertEqual(fallado.estado, EstadoWfmJob.ERROR)
        self.assertEqual(fallado.detalle_error, "boom")
        self.assertEqual(fallado.mensaje, "El job finalizo con error")

    # ------------------------- respuesta del job ------------------------- #
    def test_formatear_respuesta_calcula_progreso(self):
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        WfmJob.objects.filter(pk=job.pk).update(dias_procesados=1, total_dias=4)
        respuesta = WfmService.formatear_respuesta(
            WfmService.obtener_job(job.job_uuid)
        )
        self.assertEqual(respuesta["progreso"], 25)
        self.assertEqual(respuesta["job_uuid"], job.job_uuid)
        self.assertFalse(respuesta["existing"])
        self.assertIn("fecha_cursor", respuesta)

    def test_formatear_respuesta_detecta_job_pendiente_colgado(self):
        job, _ = WfmService.crear_job(mes=11, yyyy=2026, hoy=self.hoy)
        WfmJob.objects.filter(pk=job.pk).update(
            created_at=timezone.now() - timedelta(seconds=300),
            updated_at=timezone.now() - timedelta(seconds=300),
        )
        respuesta = WfmService.formatear_respuesta(
            WfmService.obtener_job(job.job_uuid)
        )
        self.assertIn("revisa cron", respuesta["mensaje"])


class WfmApiTests(TestCase):
    """F5-5: los tres endpoints HTTP del WFM.

    El legacy los protegía con un HMAC que generaba y consumía el propio
    navegador; aquí exigen `change_salida` (ver wfm_view.py).
    """

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        _asegurar_tablas_wfm()
        super().setUpClass()

    def setUp(self):
        self.hoy = date(2026, 11, 11)
        # El endpoint no puede recibir `hoy`, así que se fija el reloj:
        # si no, el servicio usaría la fecha REAL y la ventana no
        # contendría los datos de prueba.
        reloj = mock.patch(
            "django.utils.timezone.localdate", return_value=self.hoy
        )
        reloj.start()
        self.addCleanup(reloj.stop)

        self.persona = Empleado.objects.create(
            cedula="111222333", codigo_sap="SAP-111222333",
            nombre="WFM", apellido="API", area="OPERACIONES",
            carpeta="LOGISTICA", sede="MEDELLIN", movil="MOVIL-77",
            password="",
        )
        self.vehiculo = FlotaService.crear(
            {
                "placa": "WFMAPI", "tipo_vehiculo": "CAMIONETA",
                "marca": "KIA", "referencia": "X", "modelo_anio": 2023,
                "tipo_contrato": "PROPIO", "nombre_propietario": "C",
                "cedula_propietario": "900111222", "valor_dia_base": 85000,
            },
            actor=None,
        )
        self.api = APIClient()

    def _usuario_con_permiso(self):
        user = User.objects.create_user(username="111222333", password="x")
        user.user_permissions.add(
            Permission.objects.get(codename="change_salida")
        )
        # Nueva instancia: los permisos se cachean en el objeto.
        return User.objects.get(pk=user.pk)

    def _salida(self, dia=None, **extra):
        datos = {
            "vehiculo": self.vehiculo,
            "fecha_salida": dia or self.hoy,
            "area": "OPERACIONES", "carpeta": "LOGISTICA",
            "sede": "MEDELLIN", "valor_dia": Decimal("85000"),
            "estado": EstadoSalida.REPORTADO,
            "tecnico_asignado": self.persona,
        }
        datos.update(extra)
        return Salida.objects.create(**datos)

    def _wfm(self, dia=None):
        dia = dia or self.hoy
        return ResidencialWfm.objects.create(
            external_id="111222333",
            fecha=datetime(dia.year, dia.month, dia.day, 8, 0),
        )

    # ------------------------------ validar ------------------------------ #
    def test_validar_lote(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        salida = self._salida()
        self._wfm()
        resp = self.api.post("/transporte/wfm/validar/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)

    def test_validar_sin_permiso_de_modelo(self):
        self.api.force_authenticate(
            user=User.objects.create_user(username="111222333", password="x")
        )
        self.assertEqual(
            self.api.post("/transporte/wfm/validar/", {}, format="json").status_code,
            403,
        )

    def test_validar_sin_autenticar(self):
        self.assertEqual(
            self.api.post("/transporte/wfm/validar/", {}, format="json").status_code
            in (401, 403),
            True,
        )

    def test_validar_periodo_no_validable(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        resp = self.api.post(
            "/transporte/wfm/validar/",
            {"fecha_inicio": "2020-01-01", "fecha_fin": "2020-01-31"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("no contiene fechas", resp.json()["detail"])

    def test_validar_mes_invalido_da_ventana_por_defecto(self):
        """Fiel al legado: un mes inexistente no lanza, usa la ventana."""
        self.api.force_authenticate(user=self._usuario_con_permiso())
        resp = self.api.post(
            "/transporte/wfm/validar/", {"mes": 13, "yyyy": 2026}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

    # ------------------------------ la cola ------------------------------ #
    def test_crear_job(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        resp = self.api.post(
            "/transporte/wfm/crear-job/",
            {"mes": 11, "yyyy": 2026, "area": "OPERACIONES"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        cuerpo = resp.json()
        self.assertTrue(cuerpo["success"])
        self.assertEqual(cuerpo["estado"], "PENDIENTE")
        self.assertEqual(cuerpo["fecha_inicio"], "2026-11-09")
        self.assertIn("cola de validacion", cuerpo["message"])

    def test_crear_job_reutiliza_el_vigente(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        datos = {"mes": 11, "yyyy": 2026, "area": "OPERACIONES"}
        primero = self.api.post("/transporte/wfm/crear-job/", datos, format="json")
        segundo = self.api.post("/transporte/wfm/crear-job/", datos, format="json")
        self.assertTrue(segundo.json()["existing"])
        self.assertEqual(
            primero.json()["job_uuid"], segundo.json()["job_uuid"]
        )

    def test_crear_job_periodo_no_validable(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        resp = self.api.post(
            "/transporte/wfm/crear-job/", {"mes": 8, "yyyy": 2026}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_estado_job_inexistente(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        resp = self.api.post(
            "/transporte/wfm/estado-job/", {"job_uuid": "nadie"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_estado_job_sin_uuid(self):
        self.api.force_authenticate(user=self._usuario_con_permiso())
        resp = self.api.post("/transporte/wfm/estado-job/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_estado_job_con_respaldo_sincrono(self):
        """El legacy empuja UN chunk si el worker no corrió (201–214)."""
        self.api.force_authenticate(user=self._usuario_con_permiso())
        salida = self._salida(dia=date(2026, 11, 9))
        self._wfm(dia=date(2026, 11, 9))
        creado = self.api.post(
            "/transporte/wfm/crear-job/",
            {"mes": 11, "yyyy": 2026, "area": "OPERACIONES"},
            format="json",
        ).json()
        self.assertEqual(creado["total_validados"], 0)

        estado = self.api.post(
            "/transporte/wfm/estado-job/", {"job_uuid": creado["job_uuid"]},
            format="json",
        ).json()
        salida.refresh_from_db()
        self.assertEqual(salida.estado, EstadoSalida.VALIDADO)
        self.assertEqual(estado["total_validados"], 1)
        self.assertEqual(estado["estado"], "PROCESANDO")  # 1 de 3 días


# ═════════════════════════════════════════════════════════════════════════════
# §5.6 / S5: Planilla Oficial de Salida
# ═════════════════════════════════════════════════════════════════════════════

class PlanillaServiceTests(TestCase):
    """Pruebas unitarias de PlanillaService (CR-11 / S5 / consecutivos / QR)."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.v_propio = FlotaService.crear(
            {
                "placa": "PLA111", "tipo_vehiculo": "CAMIONETA",
                "marca": "TOYOTA", "referencia": "HILUX", "modelo_anio": 2022,
                "tipo_contrato": "PROPIO", "nombre_propietario": "PROPIETARIO 1",
                "cedula_propietario": "1001", "valor_dia_base": 120000,
            },
            actor=None,
        )
        self.v_externo = FlotaService.crear(
            {
                "placa": "EXT222", "tipo_vehiculo": "FURGON",
                "marca": "CHEVROLET", "referencia": "NKR", "modelo_anio": 2021,
                "tipo_contrato": "EXTERNO", "nombre_propietario": "PROPIETARIO 2",
                "cedula_propietario": "1002", "valor_dia_base": 150000,
            },
            actor=None,
        )

    def test_validar_fecha_invalida(self):
        with self.assertRaises(ValueError) as ctx:
            PlanillaService._validar_fecha("fecha-no-valida")
        self.assertIn("Fecha inválida", str(ctx.exception))

    def test_validar_alcance_invalido(self):
        with self.assertRaises(ValueError) as ctx:
            PlanillaService._validar_alcance("DESCONOCIDO", placa=None)
        self.assertIn("inválido", str(ctx.exception))

    def test_alcance_placa_sin_placa_falla(self):
        with self.assertRaises(ValueError) as ctx:
            PlanillaService._validar_alcance("PLACA", placa="")
        self.assertIn("placa es obligatoria", str(ctx.exception))

    def test_generar_planilla_placa_exacta(self):
        resultado = PlanillaService.generar_planilla(
            fecha="2026-10-16", alcance="PLACA", placa="PLA111"
        )
        self.assertEqual(resultado["alcance"], "PLACA")
        self.assertEqual(len(resultado["vehiculos"]), 1)
        fila = resultado["vehiculos"][0]
        self.assertEqual(fila["placa"], "PLA111")
        self.assertEqual(fila["tipo_contrato"], "PROPIO")
        self.assertEqual(fila["consecutivo"], 1000)
        self.assertTrue(fila["consecutivo_creado"])
        self.assertIsNotNone(fila["ruta_qr"])
        self.assertTrue(fila["ruta_qr"].startswith("transporte/codigos-qr/"))

    def test_generar_planilla_alcance_propio(self):
        resultado = PlanillaService.generar_planilla(
            fecha="2026-10-16", alcance="PROPIO"
        )
        placas = [v["placa"] for v in resultado["vehiculos"]]
        self.assertIn("PLA111", placas)
        self.assertNotIn("EXT222", placas)

    def test_generar_planilla_alcance_todas(self):
        resultado = PlanillaService.generar_planilla(
            fecha="2026-10-16", alcance="TODAS"
        )
        placas = [v["placa"] for v in resultado["vehiculos"]]
        self.assertIn("PLA111", placas)
        self.assertIn("EXT222", placas)

    def test_planilla_excluye_motos(self):
        """H4 / CR-11: el filtro duro tipo != 'MOTO' aplica aunque el
        valor venga de datos legacy (fuera de los choices)."""
        Vehiculo.objects.create(
            placa="MOT001", tipo_vehiculo="MOTO", marca="AKT",
            referencia="NKD", modelo_anio=2020, tipo_contrato="PROPIO",
            nombre_propietario="DUEÑO MOTO", cedula_propietario="777",
            valor_dia_base=Decimal("30000"),
        )
        resultado = PlanillaService.generar_planilla(
            fecha="2026-10-16", alcance="TODAS"
        )
        placas = [v["placa"] for v in resultado["vehiculos"]]
        self.assertNotIn("MOT001", placas)
        self.assertIn("PLA111", placas)

    def test_salida_del_dia_incluye_cedula_del_tecnico(self):
        """H3: el formato físico imprime la CÉDULA del técnico asignado,
        no el id de la FK (bug: 'tecnico_cedula' devolvía el ID)."""
        persona = Empleado.objects.create(
            cedula="555666777", codigo_sap="SAP-555666777",
            nombre="TEC", apellido="NICO", area="OPERACIONES",
            carpeta="LOGISTICA", sede="MEDELLIN", movil="MOVIL-9",
            password="",
        )
        Salida.objects.create(
            vehiculo=self.v_propio, fecha_salida=date(2026, 10, 16),
            tecnico_asignado=persona, area="OPERACIONES",
            carpeta="LOGISTICA", sede="MEDELLIN",
            valor_dia=Decimal("120000"),
        )
        resultado = PlanillaService.generar_planilla(
            fecha="2026-10-16", alcance="PLACA", placa="PLA111"
        )
        salidas = resultado["vehiculos"][0]["salidas_del_dia"]
        self.assertEqual(len(salidas), 1)
        self.assertEqual(salidas[0]["tecnico_cedula"], "555666777")

class PlanillaAPITests(TestCase):
    """Pruebas del endpoint HTTP consolidado de la Planilla Oficial de Salida."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.vehiculo = FlotaService.crear(
            {
                "placa": "API999", "tipo_vehiculo": "CAMIONETA",
                "marca": "NISSAN", "referencia": "FRONTIER", "modelo_anio": 2024,
                "tipo_contrato": "PROPIO", "nombre_propietario": "PROPIETARIO API",
                "cedula_propietario": "999888", "valor_dia_base": 110000,
            },
            actor=None,
        )
        self.user = User.objects.create_user(username="test_planilla", password="x")
        # H2: /planillas/generar/ escribe consecutivos ⇒ exige
        # add_consecutivomensual (igual que el resto del módulo).
        self.user.user_permissions.add(
            Permission.objects.get(codename="add_consecutivomensual")
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.api = APIClient()

    def test_endpoint_sin_autenticacion_falla(self):
        resp = self.api.post(
            "/transporte/planillas/generar/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "API999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_endpoint_sin_permiso_de_modelo_falla(self):
        """H2: autenticado SIN permiso de modelo no puede generar (403)."""
        self.api.force_authenticate(
            user=User.objects.create_user(username="sin_permiso", password="x")
        )
        resp = self.api.post(
            "/transporte/planillas/generar/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "API999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_endpoint_generar_exitoso_estandarizado(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/planillas/generar/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "API999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        cuerpo = resp.json()
        self.assertTrue(cuerpo["ok"])
        datos = cuerpo["data"]
        self.assertEqual(datos["alcance"], "PLACA")
        self.assertEqual(len(datos["vehiculos"]), 1)
        self.assertEqual(datos["vehiculos"][0]["placa"], "API999")
        self.assertIsNotNone(datos["vehiculos"][0]["ruta_qr"])

    def test_endpoint_generar_error_estandarizado(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/planillas/generar/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "NOEXISTE"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        cuerpo = resp.json()
        self.assertFalse(cuerpo["ok"])
        self.assertIn("No existe un vehículo", cuerpo["error"])


class PlanillaFormatoFisicoTests(TestCase):
    """P1 cerrado: formato físico F-104 (reemplaza `planilla_salida.php`).

    Verificado contra el archivo legacy adjunto en la carpeta de migraciones:
    rótulo F-104, período mensual, casillas de firmas en blanco, tabla de
    2 bloques × 7 columnas con 16 filas y LETTER horizontal.
    """

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.vehiculo = FlotaService.crear(
            {
                "placa": "F104AA", "tipo_vehiculo": "CAMIONETA",
                "marca": "TOYOTA", "referencia": "HILUX", "modelo_anio": 2024,
                "tipo_contrato": "PROPIO", "nombre_propietario": "PROPIETARIO F104",
                "cedula_propietario": "333444", "valor_dia_base": 120000,
            },
            actor=None,
        )
        self.user = User.objects.create_user(username="f104", password="x")
        self.user.user_permissions.add(
            Permission.objects.get(codename="add_consecutivomensual")
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.api = APIClient()

    def _planilla(self, fecha="2026-10-16", alcance="PLACA", placa="F104AA"):
        return PlanillaService.generar_planilla(
            fecha=fecha, alcance=alcance, placa=placa
        )

    def _html(self, fecha="2026-10-16", alcance="PLACA", placa="F104AA"):
        return PlanillaService.html_formato(self._planilla(fecha, alcance, placa))

    # --------------------------- formato base --------------------------- #
    def test_rubrica_periodo_y_consecutivo(self):
        html = self._html()
        self.assertIn(
            "F-104 PLANILLA CONTROL DE VEHÍCULOS CINCO S.A.S MENSUAL", html
        )
        self.assertIn("VERSIÓN: 01", html)
        # Período del mes completo de la fecha (el legacy lo calculaba igual).
        self.assertIn("DEL 01 DE OCTUBRE AL 31 DE OCTUBRE DE 2026", html)
        self.assertIn("CONSECUTIVO: 1000", html)

    def test_no_imprime_la_fecha_fija_del_legacy(self):
        # planilla_salida.php 131 imprimía "FECHA: 16/02/2022" hardcodeado.
        html = self._html()
        self.assertNotIn("16/02/2022", html)
        self.assertIn("FECHA:", html)

    def test_casillas_de_valores_y_qr(self):
        html = self._html()
        self.assertIn("F104AA", html)
        self.assertIn("PROPIETARIO F104", html)
        self.assertIn("$ 120.000", html)                    # valor_día real
        self.assertIn("data:image/png;base64,", html)      # QR autocontenido
        self.assertIn("LETTER landscape", html)             # impresión horizontal
        # Sin código de barras: D-A8 lo eliminó como artefacto regenerable.
        self.assertNotIn("codigo_barras", html)
        self.assertNotIn("barras_", html)

    def test_tabla_de_firmas_16_filas_y_2_bloques(self):
        html = self._html()
        self.assertEqual(html.count("<th>DÍA</th>"), 2)     # 2 bloques de 7 cols
        self.assertEqual(html.count("<tr><td>1</td>"), 1)   # fila del día 1
        self.assertIn("<td>16</td>", html)
        # Octubre tiene 31 días ⇒ la columna derecha llega al 31, no al 32.
        self.assertIn("<td>31</td>", html)
        self.assertNotIn("<td>32</td>", html)

    def test_febrero_recorta_las_celdas_sin_dia(self):
        html = self._html(fecha="2026-02-15")
        self.assertIn("DEL 01 DE FEBRERO AL 28 DE FEBRERO DE 2026", html)
        self.assertIn("<td>28</td>", html)
        self.assertNotIn("<td>29</td>", html)
        self.assertIn('class="vacio"', html)                # celdas sin borde

    def test_casillas_en_blanco_para_diligenciar_a_mano(self):
        # TOTAL DÍAS / DESCUENTOS / ADICIONALES / VALOR TOTAL se escriben
        # a mano durante el mes (el importe se liquida en la sábana).
        html = self._html()
        for rotulo in ("TOTAL DÍAS:", "DESCUENTOS:", "ADICIONALES:", "VALOR TOTAL:"):
            self.assertIn(rotulo, html)

    # -------------------------- datos reales ---------------------------- #
    def test_conductor_y_telefono_reales(self):
        """El legacy dejaba esas casillas VACÍAS (su consulta estaba comentada)."""
        conductor = Conductor.objects.create(
            cedula="777888999", nombre_completo="LUIS EXTERNO",
            celular="3001112233", fecha_ingreso=date(2026, 1, 1),
        )
        self.vehiculo.conductor_habitual = conductor
        self.vehiculo.save(update_fields=["conductor_habitual"])

        html = self._html()
        self.assertIn("LUIS EXTERNO", html)
        self.assertIn("3001112233", html)

    def test_escapa_lo_que_el_usuario_escriba(self):
        """El legacy imprimía entrada del usuario sin escapar."""
        vehiculo = FlotaService.crear(
            {
                "placa": "XSS001", "tipo_vehiculo": "CAMIONETA", "marca": "M",
                "referencia": "R", "modelo_anio": 2024, "tipo_contrato": "PROPIO",
                "nombre_propietario": "<script>alert(1)</script>",
                "cedula_propietario": "1", "valor_dia_base": 1000,
            },
            actor=None,
        )
        html = PlanillaService.html_formato(
            PlanillaService.generar_planilla(
                fecha="2026-10-16", alcance="PLACA", placa=vehiculo.placa
            )
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_una_hoja_por_vehiculo(self):
        FlotaService.crear(
            {
                "placa": "F104BB", "tipo_vehiculo": "FURGON", "marca": "M",
                "referencia": "R", "modelo_anio": 2023, "tipo_contrato": "PROPIO",
                "nombre_propietario": "PROPIETARIO 2", "cedula_propietario": "555",
                "valor_dia_base": 90000,
            },
            actor=None,
        )
        html = self._html(alcance="TODAS", placa="")
        self.assertEqual(html.count('<section class="hoja">'), 2)
        self.assertIn("F104AA", html)
        self.assertIn("F104BB", html)

    # ------------------------------ HTTP -------------------------------- #
    def test_formato_http_devuelve_html(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/planillas/formato/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "F104AA"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp["Content-Type"])
        self.assertIn("F-104 PLANILLA", resp.content.decode())

    def test_formato_http_exige_permiso_de_modelo(self):
        self.api.force_authenticate(
            user=User.objects.create_user(username="f104_sin", password="x")
        )
        resp = self.api.post(
            "/transporte/planillas/formato/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "F104AA"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_formato_http_error_estandarizado(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/planillas/formato/",
            {"fecha": "2026-10-16", "alcance": "PLACA", "placa": "NOEXISTE"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])


class KioscoAPITests(TestCase):
    """Pruebas de los endpoints consolidados del kiosco."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.vehiculo = FlotaService.crear(
            {
                "placa": "KSK100", "tipo_vehiculo": "CAMIONETA",
                "marca": "RENAULT", "referencia": "DUSTER", "modelo_anio": 2023,
                "tipo_contrato": "PROPIO", "nombre_propietario": "PROPIETARIO KIOSCO",
                "cedula_propietario": "555444", "valor_dia_base": 95000,
            },
            actor=None,
        )
        self.user = User.objects.create_user(username="test_kiosco", password="x")
        self.api = APIClient()

    def test_identificar_por_placa(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/kiosco/identificar/",
            {"placa": "KSK100"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        cuerpo = resp.json()
        self.assertTrue(cuerpo["ok"])
        self.assertEqual(cuerpo["data"]["vehiculo"]["placa"], "KSK100")

    def test_identificar_por_qr(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/kiosco/identificar/",
            {"qr": "KSK100"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        cuerpo = resp.json()
        self.assertTrue(cuerpo["ok"])
        self.assertEqual(cuerpo["data"]["vehiculo"]["placa"], "KSK100")

    def test_identificar_no_encontrado(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/kiosco/identificar/",
            {"placa": "INEXISTENTE"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        cuerpo = resp.json()
        self.assertFalse(cuerpo["ok"])
        self.assertIn("no encontrado", cuerpo["error"])

    def test_alias_escanear_retrocompatible(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.post(
            "/transporte/kiosco/escanear/",
            {"contenido": "KSK100"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    def test_alias_get_vehiculo(self):
        self.api.force_authenticate(user=self.user)
        resp = self.api.get("/transporte/kiosco/vehiculo/KSK100/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(resp.json()["data"]["vehiculo"]["placa"], "KSK100")


class TransportePaginacionYValidacionAPITests(TestCase):
    """
    Verifica que todos los endpoints paginados respondan HTTP 200 con la
    estructura canónica de PaginacionTransporte (count, next, previous, results)
    y que la ruta /transporte/validaciones/ esté registrada y operativa.
    """

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_superuser(
            username="admin_test", email="admin@test.com", password="x"
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_endpoints_paginados_retornan_200_con_estructura_canonica(self):
        rutas = [
            "/transporte/conductores/",
            "/transporte/vehiculos/",
            "/transporte/parametros/cierres/",
            "/transporte/parametros/jefes/",
            "/transporte/liquidaciones/",
            "/transporte/validaciones/",
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                resp = self.api.get(ruta)
                self.assertEqual(
                    resp.status_code,
                    200,
                    f"Falla HTTP 200 en {ruta}: {resp.content}",
                )
                data = resp.json()
                self.assertIn("count", data, f"Falta 'count' en {ruta}")
                self.assertIn("next", data, f"Falta 'next' en {ruta}")
                self.assertIn("previous", data, f"Falta 'previous' en {ruta}")
                self.assertIn("results", data, f"Falta 'results' en {ruta}")
                self.assertIsInstance(data["results"], list)

    def test_post_validaciones_cierre_area_via_http(self):
        empleado = Empleado.objects.create(
            cedula="999888777",
            codigo_sap="SAP-999888777",
            nombre="MARIO",
            apellido="VALIDADOR",
            password="",
        )
        ParametrosService.crear_jefe(
            {
                "empleado": empleado,
                "areas": ["OPERACIONES"],
                "carpetas_por_area": {"OPERACIONES": []},
            },
            actor=None,
        )
        user_jefe = User.objects.create_user(
            username="999888777", password="x", is_staff=True
        )
        # Asignar permisos de modelo para ValidacionSalida
        perm_add = Permission.objects.get(
            codename="add_validacionsalida",
            content_type__app_label="transporte",
        )
        user_jefe.user_permissions.add(perm_add)

        self.api.force_authenticate(user=user_jefe)
        resp = self.api.post(
            "/transporte/validaciones/",
            {
                "area": "OPERACIONES",
                "mes": 10,
                "anio": 2026,
                "datos": {"resumen": "cierre mensual test"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        cuerpo = resp.json()
        self.assertEqual(cuerpo["area"], "OPERACIONES")
        self.assertEqual(cuerpo["mes"], 10)
        self.assertEqual(cuerpo["anio"], 2026)


# ═════════════════════════════════════════════════════════════════════════════
# E3 / CR-8: PermisoService y GET /permisos/estado/
# ═════════════════════════════════════════════════════════════════════════════

def _perm(codename):
    """Permiso custom por codename (creado por la migración 0006)."""
    return Permission.objects.get(
        codename=codename, content_type__app_label="transporte"
    )


class PermisoServiceYEstadoTests(TestCase):
    """E3: las cédulas hardcodeadas del legacy se traducen a grupos y
    permisos Django (§5.9); GET /permisos/estado/ expone el snapshot."""

    @classmethod
    def setUpClass(cls):
        _asegurar_tabla_empleados()
        super().setUpClass()

    def _user(self, username="u1"):
        return User.objects.create_user(username=username, password="x")

    def test_anonimo_todo_false(self):
        estado = PermisoService.estado(None)
        self.assertFalse(estado["autenticado"])
        for flag in ("es_admin", "es_operador", "puede_programar",
                     "permiso_especial", "editar_tras_cierre", "es_jefe"):
            self.assertFalse(estado[flag], flag)

    def test_superuser_tiene_todo(self):
        user = User.objects.create_superuser(username="root", password="x")
        estado = PermisoService.estado(user)
        self.assertTrue(estado["es_admin"])
        self.assertTrue(estado["puede_programar"])
        self.assertTrue(estado["permiso_especial"])
        self.assertTrue(estado["editar_tras_cierre"])

    def test_permiso_puede_programar_concedido(self):
        user = self._user("prog")
        self.assertFalse(PermisoService.puede_programar(user))
        user.user_permissions.add(_perm("puede_programar"))
        user = User.objects.get(pk=user.pk)  # recachea permisos
        self.assertTrue(PermisoService.puede_programar(user))
        self.assertTrue(PermisoService.estado(user)["puede_programar"])

    def test_grupo_admin_da_permisos_de_admin(self):
        user = self._user("adm")
        user.groups.create(name="transporte_admin")
        estado = PermisoService.estado(user)
        self.assertTrue(estado["es_admin"])
        self.assertTrue(estado["puede_programar"])
        self.assertTrue(estado["permiso_especial"])
        self.assertTrue(estado["editar_tras_cierre"])

    def test_grupo_operador_marca_es_operador(self):
        user = self._user("ope")
        user.groups.create(name="transporte_operador")
        estado = PermisoService.estado(user)
        self.assertTrue(estado["es_operador"])
        self.assertFalse(estado["puede_programar"])

    def test_permiso_especial_y_editar_tras_cierre(self):
        user = self._user("esp")
        self.assertFalse(PermisoService.permiso_especial(user))
        self.assertFalse(PermisoService.puede_editar_tras_cierre(user))
        user.user_permissions.add(_perm("permiso_especial"))
        user.user_permissions.add(_perm("editar_tras_cierre"))
        user = User.objects.get(pk=user.pk)
        self.assertTrue(PermisoService.permiso_especial(user))
        self.assertTrue(PermisoService.puede_editar_tras_cierre(user))

    def test_jefe_expone_areas(self):
        empleado = Empleado.objects.create(
            cedula="555444333", codigo_sap="SAP-555444333",
            nombre="JEFE", apellido="AREA", password="",
        )
        ParametrosService.crear_jefe(
            {"empleado": empleado, "areas": ["OPERACIONES", "LOGISTICA"],
             "carpetas_por_area": {"OPERACIONES": []}},
            actor=None,
        )
        user = self._user("555444333")
        estado = PermisoService.estado(user)
        self.assertTrue(estado["es_jefe"])
        self.assertEqual(estado["areas_jefe"], ["LOGISTICA", "OPERACIONES"])

    def test_endpoint_permisos_estado(self):
        user = self._user("front")
        user.groups.create(name="transporte_operador")
        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.get("/transporte/permisos/estado/")
        self.assertEqual(resp.status_code, 200, resp.content)
        datos = resp.json()["data"]
        self.assertTrue(datos["autenticado"])
        self.assertTrue(datos["es_operador"])
        self.assertEqual(datos["username"], "front")


# ═════════════════════════════════════════════════════════════════════════════
# E1: catálogo operativo de vehículos
# ═════════════════════════════════════════════════════════════════════════════

class CatalogoOperativoTests(TestCase):
    """E1: GET /vehiculos/catalogo-operativo/ reemplaza al controlador
    externo get_vehiculos_transp; solo vehículos activos."""

    def setUp(self):
        self.activo = FlotaService.crear(
            {
                "placa": "CAT100", "tipo_vehiculo": "CAMIONETA",
                "marca": "MAZDA", "referencia": "CX5", "modelo_anio": 2022,
                "tipo_contrato": "PROPIO", "nombre_propietario": "CINCO SAS",
                "cedula_propietario": "900111222", "valor_dia_base": 100000,
                "fecha_soat": date(2027, 1, 1), "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )
        self.inactivo = FlotaService.crear(
            {
                "placa": "CAT999", "tipo_vehiculo": "FURGON",
                "marca": "CHEVROLET", "referencia": "NKR", "modelo_anio": 2021,
                "tipo_contrato": "EXTERNO", "nombre_propietario": "TERCERO",
                "cedula_propietario": "800111222", "valor_dia_base": 80000,
                "fecha_soat": date(2027, 1, 1), "fecha_cda": date(2026, 11, 15),
            },
            actor=None,
        )
        FlotaService.inactivar(self.inactivo.pk, actor=None)
        self.api = APIClient()
        self.api.force_authenticate(
            user=User.objects.create_superuser(username="op", password="x")
        )

    def test_solo_devuelve_activos(self):
        resp = self.api.get("/transporte/vehiculos/catalogo-operativo/")
        self.assertEqual(resp.status_code, 200, resp.content)
        placas = [v["placa"] for v in resp.json()["results"]]
        self.assertIn("CAT100", placas)
        self.assertNotIn("CAT999", placas)  # inactivo excluido

    def test_incluye_campos_y_semaforo(self):
        resp = self.api.get("/transporte/vehiculos/catalogo-operativo/")
        fila = next(
            v for v in resp.json()["results"] if v["placa"] == "CAT100"
        )
        self.assertEqual(fila["tipo_vehiculo"], "CAMIONETA")
        self.assertEqual(fila["tipo_contrato"], "PROPIO")
        self.assertIn("estado_soat", fila)
        self.assertIn("estado_cda", fila)
        self.assertIn("conductor_habitual_detalle", fila)

