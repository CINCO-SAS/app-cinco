"""
Tests del módulo Transporte.

Ejecución (usa config.settings_test → SQLite en memoria, sin MySQL):
    python backend/manage.py test apps.transporte --settings=config.settings_test
"""
from datetime import date

from django.test import SimpleTestCase, TestCase

from .models import Conductor, Novedad, Salida, TipoVehiculo, Vehiculo
from .services import ConductorService


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
