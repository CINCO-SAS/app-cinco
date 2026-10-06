from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from apps.smu.models import SmuEstacion, SmuMatrizLpu
from apps.smu.services.smu_maestras_loader import (
    SmuMaestrasLoaderService,
    convertir_decimal,
    limpiar_texto,
)


class SmuEstacionesModelTests(TestCase):
    """Pruebas de integridad y validaciones para SmuEstacion (Fase 1)."""

    def test_creacion_estacion_valida_1fn(self):
        """Valida la creación correcta de una estación con atributos 1FN."""
        estacion = SmuEstacion.objects.create(
            nombre_sitio='ESTACION PRINCIPAL NORTE',
            regional='NOROCCIDENTE',
            departamento='ANTIOQUIA',
            municipio='MEDELLIN',
            zona='URBANA',
            direccion='Calle 10 # 40-20',
            latitud=Decimal('6.2442030'),
            longitud=Decimal('-75.5812110'),
            tipo_estacion='NODO',
            tipo_sitio='ROOFTOP',
            site_owner='TOWER_CO',
            categoria_criticidad='1. ALTA',
            activo=True
        )
        self.assertIsNotNone(estacion.id)
        self.assertEqual(str(estacion), 'ESTACION PRINCIPAL NORTE')
        self.assertEqual(estacion.departamento, 'ANTIOQUIA')

    def test_restriccion_unique_en_nombre_sitio(self):
        """Demuestra que la BD rechaza duplicados en el nombre del sitio."""
        SmuEstacion.objects.create(nombre_sitio='ESTACION DUPLICADA')
        with self.assertRaises(IntegrityError):
            SmuEstacion.objects.create(nombre_sitio='ESTACION DUPLICADA')


class SmuMatrizLpuModelTests(TestCase):
    """Pruebas de integridad y precisión numérica para SmuMatrizLpu (Fase 1)."""

    def test_creacion_lpu_y_precision_decimal_monetaria(self):
        """Demuestra que los valores monetarios mantienen exactitud decimal estricta sin redondeos flotantes."""
        item = SmuMatrizLpu.objects.create(
            codigo_sap='SAP-998877',
            codigo_liquidacion='LIQ-01',
            texto_sap='CONECTOR BNC MACHO CRIMP',
            descripcion='Conector coaxial de precisión',
            unidad_medida='UN',
            valor_unitario=Decimal('15420.75'),
            tipo_registro='material_correctivo',
            activo=True
        )
        self.assertIsNotNone(item.id)
        self.assertEqual(item.valor_unitario, Decimal('15420.75'))
        self.assertEqual(str(item), 'SAP-998877 - CONECTOR BNC MACHO CRIMP')

    def test_restriccion_unique_en_codigo_sap(self):
        """Demuestra que la BD rechaza códigos SAP duplicados."""
        SmuMatrizLpu.objects.create(
            codigo_sap='SAP-DUPLICADO-01',
            texto_sap='Item A'
        )
        with self.assertRaises(IntegrityError):
            SmuMatrizLpu.objects.create(
                codigo_sap='SAP-DUPLICADO-01',
                texto_sap='Item B'
            )


class SmuMaestrasLoaderServiceTests(TestCase):
    """Pruebas para el servicio de auditoría, saneamiento y deduplicación (Fase 1)."""

    def test_utilidades_limpieza_y_conversion_decimal(self):
        self.assertEqual(limpiar_texto("  Estacion Central  "), "Estacion Central")
        self.assertEqual(limpiar_texto(None), "")
        # Formato colombiano/latino con punto de mil y coma decimal
        self.assertEqual(convertir_decimal("$ 1.250.000,50", decimales=2), Decimal('1250000.50'))
        # Formato estándar con coma de mil y punto decimal
        self.assertEqual(convertir_decimal("1,250.75", decimales=2), Decimal('1250.75'))
        # Precisión de 7 decimales para coordenadas GPS
        self.assertEqual(convertir_decimal("6.2442030", decimales=7), Decimal('6.2442030'))
        self.assertEqual(convertir_decimal(None), Decimal('0.00'))


    def test_procesar_estaciones_dry_run_detecta_duplicados_sin_escribir(self):
        registros = [
            {'nombre_sitio': 'SITIO ALFA', 'regional': 'CENTRO'},
            {'nombre_sitio': 'SITIO BETA', 'regional': 'NORTE'},
            {'nombre_sitio': 'sitio alfa', 'regional': 'CENTRO'},  # Duplicado por case
            {'nombre_sitio': '', 'regional': 'SUR'},  # Inconsistencia
        ]
        reporte = SmuMaestrasLoaderService.procesar_estaciones(registros, dry_run=True)
        self.assertEqual(reporte['total_recibidos'], 4)
        self.assertEqual(reporte['total_validos'], 2)
        self.assertEqual(reporte['total_duplicados_omitidos'], 1)
        self.assertEqual(reporte['total_inconsistencias'], 1)
        # En dry run no se escribe en la BD
        self.assertEqual(SmuEstacion.objects.count(), 0)

    def test_procesar_matriz_lpu_dry_run_detecta_duplicados_y_inconsistencias(self):
        registros = [
            {'codigo_sap': 'SAP-001', 'texto_sap': 'Cable UTP Cat 6', 'valor_unitario': '4500.00'},
            {'codigo_sap': 'SAP-002', 'texto_sap': 'Patch Cord 1m', 'valor_unitario': '12000.50'},
            {'codigo_sap': 'sap-001', 'texto_sap': 'Cable UTP Duplicado', 'valor_unitario': '4500.00'},
            {'codigo_sap': '', 'texto_sap': 'Sin codigo'},
        ]
        reporte = SmuMaestrasLoaderService.procesar_matriz_lpu(registros, dry_run=True)
        self.assertEqual(reporte['total_recibidos'], 4)
        self.assertEqual(reporte['total_validos'], 2)
        self.assertEqual(reporte['total_duplicados_omitidos'], 1)
        self.assertEqual(reporte['total_inconsistencias'], 1)
        self.assertEqual(SmuMatrizLpu.objects.count(), 0)


class SmuIntegridadReferencialFase2Tests(TestCase):
    """Pruebas de integridad referencial, claves foráneas y protección de borrado (Fase 2)."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='tecnico_admin', password='password123')
        self.estacion = SmuEstacion.objects.create(nombre_sitio='ESTACION INTEGRIDAD TEST')
        self.material = SmuMatrizLpu.objects.create(
            codigo_sap='SAP-INTEGRIDAD-01',
            texto_sap='FILTRO DE ACEITE PLANTA',
            valor_unitario=Decimal('85000.00')
        )

    def test_proteccion_de_borrado_estacion_con_actividades(self):
        """Demuestra que la BD protege contra borrado accidental de estaciones vinculadas."""
        from django.db.models import ProtectedError
        from apps.smu.models import SmuActividad

        actividad = SmuActividad.objects.create(
            categoria='preventivos',
            tipo_formulario='planta',
            estacion=self.estacion,
            nombre_estacion=self.estacion.nombre_sitio,
            responsable=self.user,
            responsable_cedula='12345678'
        )
        self.assertEqual(actividad.estacion_id, self.estacion.id)

        with self.assertRaises(ProtectedError):
            self.estacion.delete()

    def test_proteccion_de_borrado_material_lpu(self):
        """Demuestra que la BD protege contra borrado de ítems LPU utilizados en actividades."""
        from django.db.models import ProtectedError
        from apps.smu.models import SmuActividad, SmuActividadMaterial

        actividad = SmuActividad.objects.create(
            categoria='preventivos',
            tipo_formulario='planta',
            estacion=self.estacion,
            nombre_estacion=self.estacion.nombre_sitio,
            responsable_cedula='12345678'
        )
        SmuActividadMaterial.objects.create(
            actividad=actividad,
            material_lpu=self.material,
            tipo_registro='inventario_preventivo',
            codigo_sap=self.material.codigo_sap,
            texto_sap=self.material.texto_sap,
            cantidad_real=Decimal('1.00')
        )

        with self.assertRaises(ProtectedError):
            self.material.delete()

    def test_regla_compras_locales_fuera_de_catalogo(self):
        """Permite registrar materiales comprados en campo con material_lpu nulo."""
        from apps.smu.models import SmuActividad, SmuActividadMaterial

        actividad = SmuActividad.objects.create(
            categoria='correctivos',
            tipo_formulario='estandar',
            nombre_estacion='SITIO REMOTO',
            responsable_cedula='12345678'
        )
        mat_local = SmuActividadMaterial.objects.create(
            actividad=actividad,
            material_lpu=None,
            comprado_operario=True,
            tipo_registro='material_correctivo',
            texto_sap='CINTA AISLANTE FERRETERIA LOCAL',
            cantidad_real=Decimal('3.00')
        )
        self.assertIsNone(mat_local.material_lpu)
        self.assertTrue(mat_local.comprado_operario)


class SmuEndpointsRestMaestrasTests(TestCase):
    """Pruebas para los endpoints REST de Estaciones y Matriz LPU."""

    def setUp(self):
        from rest_framework.test import APIClient
        from django.contrib.auth.models import User
        self.client = APIClient()
        self.user = User.objects.create_user(username='api_tester', password='password123')
        self.client.force_authenticate(user=self.user)

        self.estacion1 = SmuEstacion.objects.create(
            nombre_sitio='NODO POBLADO',
            regional='NOROCCIDENTE',
            departamento='ANTIOQUIA',
            municipio='MEDELLIN',
            activo=True
        )
        self.estacion2 = SmuEstacion.objects.create(
            nombre_sitio='NODO CHICO',
            regional='CENTRO',
            departamento='CUNDINAMARCA',
            municipio='BOGOTA',
            activo=True
        )
        self.lpu1 = SmuMatrizLpu.objects.create(
            codigo_sap='SAP-001-TEST',
            texto_sap='CABLE COAXIAL RG6',
            valor_unitario=Decimal('2500.00'),
            tipo_registro='material_correctivo',
            activo=True
        )

    def test_listar_y_buscar_estaciones(self):
        response = self.client.get('/api/smu/estaciones/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        # Búsqueda por nombre
        response_search = self.client.get('/api/smu/estaciones/?search=POBLADO')
        self.assertEqual(response_search.status_code, 200)
        self.assertEqual(response_search.data['count'], 1)
        self.assertEqual(response_search.data['results'][0]['nombre_sitio'], 'NODO POBLADO')

    def test_listar_y_buscar_materiales_lpu(self):
        response = self.client.get('/api/smu/materiales-lpu/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['codigo_sap'], 'SAP-001-TEST')
        self.assertEqual(response.data['results'][0]['valor_unitario'], '2500.00')


