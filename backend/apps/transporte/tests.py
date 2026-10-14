"""
Tests del módulo Transporte.

Ejecución (aislada de otros módulos; SQLite en memoria, sin MySQL):
    python backend/manage.py test apps.transporte --settings=config.settings_test_transporte
"""
import os
import tempfile
from datetime import date
from unittest import mock

import qrcode
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from .models import Conductor, Novedad, Salida, TipoVehiculo, Vehiculo
from .services import ConductorService, FlotaService
from .services.flota_service import COLUMNAS_CSV_BANCARIOS
from .services.vigencia import estado_vigencia


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
