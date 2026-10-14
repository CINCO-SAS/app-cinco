"""
Tests del módulo Transporte.

Ejecución (aislada de otros módulos; SQLite en memoria, sin MySQL):
    python backend/manage.py test apps.transporte --settings=config.settings_test_transporte
"""
import os
import tempfile
from datetime import date
from decimal import Decimal
from unittest import mock

import qrcode
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings

from apps.empleados.models import Empleado

from .models import (
    Conductor,
    ConsecutivoMensual,
    EstadoSalida,
    FechaLimiteCierre,
    JefeValidador,
    Novedad,
    PagoVehiculoMensual,
    Salida,
    TipoNovedad,
    TipoPago,
    TipoVehiculo,
    Vehiculo,
)
from .serializers.jefe_serializer import JefeValidadorSerializer
from .services import ConductorService, FlotaService, LiquidacionService, ParametrosService
from .services.flota_service import COLUMNAS_CSV_BANCARIOS
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
