import io
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIRequestFactory, APIClient, force_authenticate

from apps.smu.models import (
    SmuActividad,
    SmuActividadTecnico,
    SmuActividadMaterial,
    SmuActividadEvidencia,
    SmuDetallePreventivoAa,
    SmuPreventivoAaCompresor,
    SmuDetalleFallaIntervencion,
    SmuDetalleCapex,
    SmuDetalleCapexSptFila,
)
from apps.smu.serializers import SmuActividadSerializer
from apps.smu.serializers.smu_actividad_serializer import (
    DETALLES_POR_TIPO,
    TIPOS_POR_CATEGORIA,
)
from apps.smu.services import crear_actividad_smu
from apps.smu.views import SmuActividadViewSet


class SmuCrearActividadServiceTests(TestCase):
    def test_crear_actividad_preventivo_aa_completa(self):
        payload = {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'codigo_ot': 'OT-AA-001',
            'nombre_estacion': 'ESTACION NORTE',
            'responsable_cedula': '12345678',
            'responsable_nombre': 'Juan Perez',
            'fecha_inicio': timezone.localdate(),
            'fecha_fin': timezone.localdate(),
            'tecnicos': [
                {
                    'cedula': '12345678',
                    'nombre': 'Juan Perez',
                    'es_principal': True,
                    'ruta_firma': 'firmas/firma1.png',
                }
            ],
            'materiales': [
                {
                    'tipo_registro': 'insumo',
                    'codigo_sap': 'SAP-101',
                    'texto_sap': 'Filtro Aire',
                    'cantidad_real': 2.0,
                    'unidad_medida': 'UND',
                }
            ],
            'detalle_preventivo_aa': {
                'marca': 'Carrier',
                'modelo': 'X-200',
                'voltaje_entrada': 220.0,
                'corriente': 15.2,
                'temp_cuarto': 21.5,
            },
            'aa_compresores': [
                {
                    'orden': 1,
                    'marca': 'Danfoss',
                    'amp_l1': 12.5,
                }
            ],
        }

        actividad = crear_actividad_smu(payload)

        self.assertIsNotNone(actividad.id)
        self.assertEqual(actividad.nombre_estacion, 'ESTACION NORTE')
        self.assertEqual(actividad.estado, 'enviado')
        self.assertEqual(actividad.tecnicos.count(), 1)
        self.assertEqual(actividad.materiales.count(), 1)
        self.assertEqual(actividad.aa_compresores.count(), 1)
        self.assertTrue(hasattr(actividad, 'detalle_preventivo_aa'))
        self.assertEqual(actividad.detalle_preventivo_aa.marca, 'Carrier')

    def test_crear_actividad_correctivo_emergencia(self):
        payload = {
            'categoria': 'correctivos',
            'tipo_formulario': 'estandar',
            'codigo_ot': 'OT-CORR-002',
            'nombre_estacion': 'ESTACION SUR',
            'categoria_criticidad': '1. ALTA',
            'responsable_cedula': '87654321',
            'responsable_nombre': 'Pedro Gomez',
            'fecha_inicio': timezone.localdate(),
            'detalle_falla_intervencion': {
                'tipo_equipo_falla': 'Energia AC',
                'descripcion_falla': 'Corte general por sobretensión',
                'descripcion_solucion': 'Reemplazo de protecciones y fusibles',
                'cambio': 'SI',
                'detalles_plano': 'Croquis tablero principal',
            },
        }

        actividad = crear_actividad_smu(payload)

        self.assertIsNotNone(actividad.id)
        self.assertEqual(actividad.categoria, 'correctivos')
        self.assertEqual(actividad.categoria_criticidad, '1. ALTA')
        self.assertTrue(hasattr(actividad, 'detalle_falla_intervencion'))
        self.assertEqual(actividad.detalle_falla_intervencion.tipo_equipo_falla, 'Energia AC')
        self.assertEqual(actividad.detalle_falla_intervencion.cambio, 'SI')

    def test_crear_actividad_capex_con_spt(self):
        payload = {
            'categoria': 'correctivos_capex',
            'tipo_formulario': 'tipologia1',
            'codigo_ot': 'OT-CAPEX-003',
            'nombre_estacion': 'ESTACION ORIENTE',
            'responsable_cedula': '11223344',
            'responsable_nombre': 'Carlos Ruiz',
            'fecha_inicio': timezone.localdate(),
            'detalle_capex': {
                'tipologia': 'tipologia1',
                'descripcion_general_actividades': 'Adecuacion de puesta a tierra',
                'spt_naturaleza': 'Rocoso',
                'spt_recomendacion': 'Instalar malla perimetral',
            },
            'spt_filas': [
                {
                    'orden': 1,
                    'distancia': '5.0 m',
                    'medida_ohmio': '3.8',
                    'resistividad': '119.38',
                }
            ],
        }

        actividad = crear_actividad_smu(payload)

        self.assertIsNotNone(actividad.id)
        self.assertEqual(actividad.tipo_formulario, 'tipologia1')
        self.assertTrue(hasattr(actividad, 'detalle_capex'))
        self.assertEqual(actividad.detalle_capex.spt_naturaleza, 'Rocoso')
        self.assertEqual(actividad.spt_filas.count(), 1)


class SmuSerializerValidationTests(TestCase):
    def test_validacion_fecha_fin_anterior_a_inicio(self):
        data = {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACION TEST',
            'responsable_cedula': '12345',
            'responsable_nombre': 'Tester',
            'fecha_inicio': timezone.localdate(),
            'fecha_fin': timezone.localdate() - timedelta(days=2),
        }

        serializer = SmuActividadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_fin', serializer.errors)

    def test_validacion_fecha_fuera_de_rango(self):
        """La digitación '12/12/1212' no viaja: la tabla no la podría formatear.

        Esa fecha se guardaba sin más y DRF la serializa con el offset
        histórico del año, que `new Date()` del navegador rechaza (columna
        "INICIO" en "-")."""
        data = {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACION TEST',
            'responsable_cedula': '12345',
            'responsable_nombre': 'Tester',
            'fecha_inicio': '1212-12-12T00:12:00',
        }

        serializer = SmuActividadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_inicio', serializer.errors)

        # Una fecha creíble sigue pasando sin problemas.
        data['fecha_inicio'] = '2026-10-01T08:00:00'
        serializer = SmuActividadSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_auto_aprobado_al_crear_se_normaliza_a_enviado(self):
        data = {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACION TEST',
            'responsable_cedula': '12345',
            'responsable_nombre': 'Tester',
            'estado': 'aprobado',
        }

        serializer = SmuActividadSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['estado'], 'enviado')


class SmuApiActividadesTests(TestCase):
    """La API de SMU expone POST (creación), GET listado paginado y GET detalle."""

    def setUp(self):
        self.user = User.objects.create_user(username='testadmin', password='password123')
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.actividad = crear_actividad_smu({
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACION PRUEBA VIEW',
            'responsable_cedula': '99999999',
            'responsable_nombre': 'Operador View',
            'estado': 'borrador',
        })

    def test_post_crea_actividad(self):
        response = self.api.post('/smu/actividades/', {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACION POR URL',
            'responsable_cedula': '55555555',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['nombre_estacion'], 'ESTACION POR URL')

    def test_get_listado_actividades(self):
        response = self.api.get('/smu/actividades/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 1)
        item = response.data['results'][0]
        self.assertIn('nombre_estacion', item)
        self.assertIn('tipo_formulario_display', item)

    def test_get_listado_expone_las_columnas_de_gestion(self):
        """Columnas que muestra la tabla de gestión/supervisión SMU."""
        response = self.api.get('/smu/actividades/')

        self.assertEqual(response.status_code, 200, response.data)
        item = response.data['results'][0]
        for campo in ('tipo_formulario', 'tipo_formulario_display',
                      'tipo_estacion', 'codigo_ot', 'responsable_nombre',
                      'responsable_cedula', 'estado', 'estado_display',
                      'categoria_display', 'created_at'):
            with self.subTest(campo=campo):
                self.assertIn(campo, item)
        # Los display son etiquetas legibles, no el valor crudo del choice.
        self.assertEqual(item['tipo_formulario_display'], 'Aire acondicionado')
        self.assertEqual(item['estado_display'], 'Borrador')

    def test_get_listado_filtra_por_categoria_y_tipo_formulario(self):
        response = self.api.get(
            '/smu/actividades/',
            {'categoria': 'preventivos', 'tipo_formulario': 'aire_acondicionado'},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertGreaterEqual(len(response.data['results']), 1)
        for item in response.data['results']:
            self.assertEqual(item['categoria'], 'preventivos')
            self.assertEqual(item['tipo_formulario'], 'aire_acondicionado')

    def test_get_detalle_actividad(self):
        url = f'/smu/actividades/{self.actividad.id}/'
        response = self.api.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.actividad.id)
        self.assertEqual(response.data['nombre_estacion'], 'ESTACION PRUEBA VIEW')

    def test_metodos_no_permitidos_en_coleccion(self):
        for metodo in ('put', 'patch', 'delete'):
            with self.subTest(metodo=metodo):
                response = getattr(self.api, metodo)(
                    '/smu/actividades/', {}, format='json'
                )
                self.assertEqual(response.status_code, 405)


class SmuValidacionNegocioTests(TestCase):
    """B4 · Validación de negocio en el POST /smu/actividades/: enumeración
    de `tipo_formulario`, coherencia `categoria` ↔ `tipo_formulario`,
    un solo bloque de detalle y rango de `item_numero`."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='validador', password='password123'
        )
        self.factory = APIRequestFactory()

    def _payload(self, categoria, tipo_formulario, **extra):
        data = {
            'categoria': categoria,
            'tipo_formulario': tipo_formulario,
            'nombre_estacion': 'ESTACION VALIDACION',
            'responsable_cedula': '12345678',
        }
        data.update(extra)
        return data

    def _post(self, data):
        request = self.factory.post('/smu/actividades/', data, format='json')
        force_authenticate(request, user=self.user)
        view = SmuActividadViewSet.as_view({'post': 'create'})
        return view(request)

    def test_los_6_formularios_del_modulo_creadan(self):
        pares = [
            ('preventivos', 'aire_acondicionado'),
            ('preventivos', 'planta'),
            ('correctivos', 'estandar'),
            ('emergencias', 'estandar'),
            ('correctivos_capex', 'tipologia1'),
            ('correctivos_capex', 'tipologia3'),
            ('correctivos_capex', 'tipologia5'),
        ]
        for categoria, tipo in pares:
            with self.subTest(categoria=categoria, tipo_formulario=tipo):
                response = self._post(self._payload(categoria, tipo))
                self.assertEqual(response.status_code, 201, response.data)

    def test_tipo_formulario_de_texto_libre_devuelve_400(self):
        response = self._post(self._payload('correctivos', 'mi_formulario_raro'))

        self.assertEqual(response.status_code, 400)
        self.assertIn('tipo_formulario', response.data)
        self.assertIn('Opciones válidas', str(response.data))

    def test_categoria_incoherente_con_tipo_formulario_devuelve_400(self):
        response = self._post(self._payload('preventivos', 'estandar'))

        self.assertEqual(response.status_code, 400)
        self.assertIn('tipo_formulario', response.data)
        self.assertIn('no corresponde', str(response.data))

    def test_capex_no_acepta_otros_tipos_de_formulario(self):
        response = self._post(
            self._payload('correctivos_capex', 'aire_acondicionado')
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('no corresponde', str(response.data))

    def test_dos_detalles_a_la_vez_devuelven_400(self):
        response = self._post(self._payload(
            'preventivos',
            'aire_acondicionado',
            detalle_preventivo_aa={'marca': 'Daikin'},
            detalle_capex={'tipologia': 'tipologia1'},
        ))

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('Solo puede enviarse un bloque', str(response.data))
        self.assertIn('detalle_preventivo_aa', str(response.data))

    def test_bloque_de_detalle_no_corresponde_al_tipo_devuelve_400(self):
        response = self._post(self._payload(
            'correctivos',
            'estandar',
            detalle_capex={'tipologia': 'tipologia1'},
        ))

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('detalle_capex', response.data)
        self.assertIn('no corresponde', str(response.data))

    def test_item_numero_fuera_de_rango_devuelve_400(self):
        for item_numero in (0, 40, -1):
            with self.subTest(item_numero=item_numero):
                response = self._post(self._payload(
                    'preventivos',
                    'aire_acondicionado',
                    checklist_aa=[{'item_numero': item_numero, 'estado': 'Bueno'}],
                ))

                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn('checklist_aa', response.data)
                self.assertIn('entre 1 y 39', str(response.data))

    def test_item_numero_en_el_rango_crea_el_checklist(self):
        response = self._post(self._payload(
            'preventivos',
            'aire_acondicionado',
            checklist_aa=[{'item_numero': 39, 'estado': 'Bueno'}],
        ))

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['checklist_aa'][0]['item_numero'], 39)

    def test_las_reglas_y_el_enum_no_pueden_divergir(self):
        """Anti-deriva (E6): una tipología nueva en el modelo obliga a ubicarla
        en las reglas de coherencia, y viceversa."""
        enum = {valor for valor, _ in SmuActividad.TIPO_FORMULARIO_CHOICES}
        reglas = set().union(*TIPOS_POR_CATEGORIA.values())
        self.assertEqual(enum, reglas)

        categorias = {valor for valor, _ in SmuActividad.CATEGORIA_CHOICES}
        self.assertEqual(categorias, set(TIPOS_POR_CATEGORIA))

        for tipos in DETALLES_POR_TIPO.values():
            self.assertTrue(tipos <= enum, tipos - enum)


class SmuEvidenciaUploadTests(TestCase):
    """A1: subida real de fotos (`POST /smu/evidencias/`).

    Las fotos se suben **al guardar** el formulario (decisión registrada en
    `auditoria_guardado_fotos_smu_2026-09-29.md`), o sea antes de crear la
    actividad: por eso la carpeta por defecto es `borrador/`.
    """

    def setUp(self):
        # MEDIA_ROOT temporal: los tests nunca escriben en la media real.
        self.tmp = tempfile.TemporaryDirectory()
        self._media = override_settings(MEDIA_ROOT=self.tmp.name)
        self._media.enable()
        self.addCleanup(self._media.disable)
        self.addCleanup(self.tmp.cleanup)

        self.user = User.objects.create_user(
            username='fotos', password='password123'
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    # ── utilidades ────────────────────────────────────────────────────────
    @staticmethod
    def _imagen(fmt='JPEG', size=(12, 12)):
        buf = io.BytesIO()
        Image.new('RGB', size, (120, 40, 200)).save(buf, format=fmt)
        return buf.getvalue()

    def _subir(self, contenido, nombre='foto.jpg',
               content_type='image/jpeg', **extra):
        datos = {
            'archivo': SimpleUploadedFile(nombre, contenido, content_type),
            'seccion': 'anexos_planta',
            'campo_origen': 'slot_1',
        }
        datos.update(extra)
        return self.api.post('/smu/evidencias/', datos, format='multipart')

    def _crear_actividad(self, **extra):
        datos = {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACION FOTOS',
            'responsable_cedula': '77777777',
        }
        datos.update(extra)
        return self.api.post('/smu/actividades/', datos, format='json')

    # ── subida feliz ──────────────────────────────────────────────────────
    def test_subida_ok_devuelve_ruta_webp_en_disco(self):
        response = self._subir(self._imagen())

        self.assertEqual(response.status_code, 201, response.data)
        ruta = response.data['ruta_archivo']
        self.assertTrue(
            ruta.startswith('smu/evidencias/borrador/anexos_planta/'), ruta
        )
        self.assertTrue(ruta.endswith('.webp'), ruta)
        self.assertTrue(response.data['url'].startswith('/media/'))
        # el archivo existe físicamente y ya está re-encriptado a WebP
        from django.conf import settings
        from pathlib import Path
        en_disco = Path(settings.MEDIA_ROOT) / ruta
        self.assertTrue(en_disco.is_file(), en_disco)
        with Image.open(en_disco) as img:
            self.assertEqual(img.format, 'WEBP')

    def test_con_actividad_usa_la_carpeta_de_la_actividad(self):
        creada = self._crear_actividad()
        self.assertEqual(creada.status_code, 201, creada.data)
        id_actividad = creada.data['id']

        response = self._subir(self._imagen('PNG'), nombre='foto.png'
        
        
        ,
                               content_type='image/png',
                               actividad_id=id_actividad)

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            response.data['ruta_archivo'].startswith(
                f'smu/evidencias/{id_actividad}/'
            ),
            response.data['ruta_archivo'],
        )

    def test_listado_solo_admite_post(self):
        self.assertEqual(self.api.get('/smu/evidencias/').status_code, 405)

    # ── rechazos de archivo (magic bytes, no la extensión) ────────────────
    def test_rechaza_archivo_que_no_es_imagen(self):
        # HTML renombrado a .jpg con content_type de imagen: lo pilla
        # la lectura de magic bytes de Pillow.
        response = self._subir(b'<html><body>no soy foto</body></html>')

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('archivo', response.data)

    def test_rechaza_formato_no_permitido(self):
        gif = io.BytesIO()
        Image.new('RGB', (4, 4)).save(gif, format='GIF')

        response = self._subir(gif.getvalue(), nombre='foto.gif',
                               content_type='image/gif')

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('Formato no permitido', str(response.data))

    def test_rechaza_archivo_vacio(self):
        response = self._subir(b'')

        # Se comprueba por `code` y no por el texto: el mensaje lo traduce
        # DRF según el idioma de la petición.
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('archivo', response.data)
        codigos = [
            getattr(error, 'code', None) for error in response.data['archivo']
        ]
        self.assertIn('empty', codigos, response.data)

    def test_rechaza_archivo_mayor_a_5mb(self):
        grande = b'\xff\xd8\xff\xe0' + b'0' * (5 * 1024 * 1024 + 1)
        response = self._subir(grande)

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('5 MB', str(response.data))

    def test_rechaza_actividad_inexistente(self):
        response = self._subir(self._imagen(), actividad_id=999999)

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('actividad', str(response.data).lower())

    # ── reglas sobre el payload de la actividad ───────────────────────────
    def test_ruta_blob_o_data_no_se_guarda(self):
        response = self._crear_actividad(evidencias=[{
            'seccion': 'anexos_planta',
            'campo_origen': 'slot_1',
            'ruta_archivo': 'blob:http://localhost:3000/abc-123',
        }])

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('blob', str(response.data).lower())

    def test_tope_de_5_fotos_por_campo(self):
        def evidencias(cantidad):
            return [
                {
                    'seccion': 'anexos_planta',
                    'campo_origen': 'slot_1',
                    'ruta_archivo': f'smu/evidencias/borrador/f{i}.webp',
                }
                for i in range(cantidad)
            ]

        excedido = self._crear_actividad(evidencias=evidencias(6))
        self.assertEqual(excedido.status_code, 400, excedido.data)
        self.assertIn('Máximo 5 fotos por campo', str(excedido.data))

        exacto = self._crear_actividad(evidencias=evidencias(5))
        self.assertEqual(exacto.status_code, 201, exacto.data)
        self.assertEqual(len(exacto.data['evidencias']), 5)

    def test_tope_no_apania_campos_distintos(self):
        evidencias = [
            {'seccion': 'anexos_planta', 'campo_origen': f'slot_{i}',
             'ruta_archivo': f'smu/evidencias/borrador/f{i}.webp'}
            for i in range(6)
        ]
        response = self._crear_actividad(evidencias=evidencias)

        self.assertEqual(response.status_code, 201, response.data)


class SmuExportExcelTests(TestCase):
    """``GET /smu/actividades/<id>/export/``: el Excel se adapta a los datos.

    La plantilla es solo el estilo de referencia; las filas (materiales, fotos,
    bloques de texto) deben crecer o encoger según lo que tenga la actividad.
    """

    def setUp(self):
        # MEDIA_ROOT temporal: el exporte incrusta fotos de este directorio.
        self.tmp = tempfile.TemporaryDirectory()
        self._media = override_settings(MEDIA_ROOT=self.tmp.name)
        self._media.enable()
        self.addCleanup(self._media.disable)
        self.addCleanup(self.tmp.cleanup)

        self.user = User.objects.create_user(
            username='exporta', password='password123'
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    # ── utilidades ────────────────────────────────────────────────────────
    def _emergencia(self, **extra):
        datos = {
            'categoria': 'emergencias',
            'tipo_formulario': 'estandar',
            'nombre_estacion': 'ESTACIÓN PRADERA',
            'codigo_ot': 'OT-777',
            'regional': 'ANTIOQUIA',
            'numero_inc': 'INC-9',
            'responsable_cedula': '11111111',
            'responsable_nombre': 'Tester Export',
            'fecha_inicio': timezone.now(),
            'materiales': [
                {'tipo_registro': 'material_emergencia',
                 'descripcion': 'Fibra 12H', 'cantidad_real': 3,
                 'unidad_medida': 'MT'},
                {'tipo_registro': 'material_emergencia',
                 'descripcion': 'Conector SC', 'cantidad_real': 1,
                 'unidad_medida': 'UND'},
            ],
            'transportes': [{'tipo_transporte': 'Camioneta',
                             'distancia_km': 12,
                             'observacion': 'Traslado nocturno'}],
            'detalle_falla_intervencion': {
                'tipo_actividad': 'Correctivo',
                'tipo_equipo_falla': 'Antena',
                'descripcion_falla': 'Se detecta falla en el equipo. ' * 8,
                'descripcion_solucion': 'Se reemplaza el módulo.',
            },
        }
        datos.update(extra)
        return crear_actividad_smu(datos)

    def _exportar(self, actividad):
        return self.api.get(f'/smu/actividades/{actividad.pk}/export/')

    @staticmethod
    def _libro(response):
        import openpyxl
        return openpyxl.load_workbook(io.BytesIO(response.content))

    @staticmethod
    def _valores_columna(ws, columna):
        return [
            str(celda.value)
            for fila in ws.iter_rows()
            for celda in fila
            if celda.column == columna and celda.value is not None
        ]

    @staticmethod
    def _todos(ws):
        """Todos los valores con texto de la hoja (para buscar contenido)."""
        return [
            str(celda.value)
            for fila in ws.iter_rows()
            for celda in fila
            if celda.value is not None
        ]

    @staticmethod
    def _fila_de(ws, valor, columna):
        """Fila (1-based) de la primera celda de `columna` con `valor`."""
        for fila in ws.iter_rows():
            for celda in fila:
                if celda.column == columna and str(celda.value) == valor:
                    return celda.row
        return None

    @staticmethod
    def _imagenes(ws):
        """(fila, columna) 1-based de cada foto incrustada en la hoja."""
        from openpyxl.utils.cell import coordinate_to_tuple

        celdas = []
        for img in ws._images:
            origen = getattr(img.anchor, '_from', None)
            if origen is None:
                # Ancla guardada como referencia de celda ('J12').
                celdas.append(coordinate_to_tuple(str(img.anchor)))
            else:
                celdas.append((origen.row + 1, origen.col + 1))
        return celdas

    # ── respuestas ────────────────────────────────────────────────────────
    def test_export_emergencia_devuelve_el_archivo(self):
        actividad = self._emergencia()
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertIn(
            'application/vnd.openxmlformats-officedocument'
            '.spreadsheetml.sheet',
            response['Content-Type'],
        )
        self.assertIn('emergencia_ESTACION_PRADERA_OT777.xlsx',
                      response['Content-Disposition'])
        # El archivo es un .xlsx legible con la hoja del formato.
        libro = self._libro(response)
        self.assertEqual(libro.active.title, 'Emergencia')

    def test_export_tipo_sin_plantilla_responde_400(self):
        actividad = self._emergencia()
        # Las 6 parejas válidas del módulo ya tienen plantilla, así que se
        # fuerza una pareja fuera del registro para ejercitar el 400.
        SmuActividad.objects.filter(pk=actividad.pk).update(
            categoria='preventivos', tipo_formulario='interno'
        )
        actividad.refresh_from_db()
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 400, response.content[:400])
        self.assertIn('plantilla', str(response.data))

    # ── contenido ─────────────────────────────────────────────────────────
    def test_llena_la_cabecera_y_el_ot(self):
        ws = self._libro(self._exportar(self._emergencia())).active

        self.assertEqual(ws['D8'].value, 'ESTACIÓN PRADERA')
        self.assertEqual(ws['J8'].value, 'Emergencias')
        self.assertEqual(ws['D9'].value, 'ANTIOQUIA')
        self.assertIn('Tester Export', str(ws['J9'].value))
        self.assertIn('INC-9', str(ws['J10'].value))
        # El OT no estaba en la plantilla original y sí es clave en la tabla.
        self.assertIn('OT-777', self._valores_columna(ws, 4))

    def test_detalles_del_formulario_llegan_a_su_seccion(self):
        ws = self._libro(self._exportar(self._emergencia())).active
        valores = [str(v) for v in self._valores_columna(ws, 4)]
        todos = valores + [str(c.value) for f in ws.iter_rows() for c in f
                           if c.value is not None]

        self.assertIn('Correctivo', todos)
        self.assertIn('Antena', todos)
        self.assertIn('Se reemplaza el módulo.', todos)

    def test_filas_de_materiales_segun_la_cantidad(self):
        ws = self._libro(self._exportar(self._emergencia())).active
        materiales = self._valores_columna(ws, 4)

        self.assertIn('Fibra 12H', materiales)
        self.assertIn('Conector SC', materiales)

        # Una sola actividad con un material -> una sola fila diligenciada.
        una_sola = crear_actividad_smu({
            'categoria': 'emergencias',
            'tipo_formulario': 'estandar',
            'nombre_estacion': 'ESTACION UNO',
            'responsable_cedula': '33333333',
            'materiales': [{'tipo_registro': 'material_emergencia',
                            'descripcion': 'Cable UNICO', 'cantidad_real': 1}],
        })
        ws_uno = self._libro(self._exportar(una_sola)).active
        materiales_uno = self._valores_columna(ws_uno, 4)

        self.assertIn('Cable UNICO', materiales_uno)
        self.assertNotIn('Fibra 12H', materiales_uno)

    def test_texto_largo_ocupa_mas_filas(self):
        largo = self._emergencia(detalle_falla_intervencion={
            'tipo_actividad': 'Correctivo',
            'descripcion_falla': ('Descripción muy larga. ' * 40).strip(),
        })
        corto = self._emergencia(detalle_falla_intervencion={
            'tipo_actividad': 'Correctivo',
            'descripcion_falla': 'Corta',
        })

        filas_largo = self._libro(self._exportar(largo)).active.max_row
        filas_corto = self._libro(self._exportar(corto)).active.max_row

        self.assertGreater(filas_largo, filas_corto)

    def test_seccion_observaciones_y_hallazgos_se_pinta(self):
        # Regresión: la rama "ACTIVIDAD / HALLAZGOS" (emergencia.py) usaba
        # ALTO_FILA sin importarlo y reventaba el export con NameError → 500.
        actividad = self._emergencia(
            observaciones='Se dejó el sitio limpio.',
            hallazgos='Falta proteger el cableado.',
            recomendaciones='Instalar canaleta este mes.',
        )
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        # El texto de hallazgos se pinta junto a las recomendaciones, así que
        # se busca sobre la hoja completa en vez de celda a celda.
        hoja = '\n'.join(self._todos(self._libro(response).active))
        self.assertIn('OBSERVACIONES DE LA ACTIVIDAD', hoja)
        self.assertIn('HALLAZGOS / PLAN DE MEJORA', hoja)
        self.assertIn('Falta proteger el cableado.', hoja)
        self.assertIn('RECOMENDACIONES: Instalar canaleta este mes.', hoja)

        # La otra entrada de la misma rama: "actividad realizada" viene del
        # detalle de falla (descripcion_generales / descripcion_fallas_componentes).
        con_actividad = self._emergencia(
            detalle_falla_intervencion={
                'tipo_actividad': 'Correctivo',
                'descripcion_fallas_componentes': 'Se cambió el módulo RF.',
            },
        )
        response = self._exportar(con_actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        hoja = '\n'.join(self._todos(self._libro(response).active))
        self.assertIn('Se cambió el módulo RF.', hoja)
        self.assertIn('HALLAZGOS / PLAN DE MEJORA', hoja)

    # ── fotos ─────────────────────────────────────────────────────────────
    def _guardar_fotos(self, cantidad):
        carpeta = Path(self.tmp.name) / 'smu/evidencias/borrador/evidencias'
        carpeta.mkdir(parents=True, exist_ok=True)
        rutas = []
        for i in range(cantidad):
            nombre = f'foto{i}.webp'
            Image.new('RGB', (60, 40), (10, 200, 90)).save(
                carpeta / nombre, format='WEBP'
            )
            rutas.append(f'smu/evidencias/borrador/evidencias/{nombre}')
        return rutas

    def test_las_fotos_se_incrustan_en_el_archivo(self):
        rutas = self._guardar_fotos(3)
        actividad = self._emergencia(evidencias=[
            {'seccion': 'evidencias', 'campo_origen': str(i + 1),
             'ruta_archivo': ruta, 'orden': i + 1}
            for i, ruta in enumerate(rutas)
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        # Una foto por bloque: 3 evidencias -> 3 imágenes embebidas (convertidas
        # de WebP a JPEG porque Excel no soporta WebP).
        self.assertEqual(len(medios), 3, medios)

    def test_sin_fotos_también_exporta(self):
        actividad = self._emergencia(evidencias=[])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(medios, [])

    def test_foto_con_ruta_inexistente_no_tumba_el_exporte(self):
        actividad = self._emergencia(evidencias=[
            {'seccion': 'evidencias', 'campo_origen': '1',
             'ruta_archivo': 'smu/evidencias/borrador/no_existe.webp',
             'orden': 1},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])

    def test_las_fotos_de_material_pintan_su_columna_sin_duplicarse(self):
        rutas = self._guardar_fotos(3)
        actividad = self._emergencia(evidencias=[
            {'seccion': 'materiales', 'campo_origen': 'material_1_foto_antes',
             'ruta_archivo': rutas[0], 'orden': 1},
            {'seccion': 'materiales', 'campo_origen': 'material_2_foto_despues',
             'ruta_archivo': rutas[1], 'orden': 2},
            {'seccion': 'evidencias', 'campo_origen': '1',
             'ruta_archivo': rutas[2], 'orden': 3},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        # 3 fotos en total: la de material no se repite en el bloque 5.
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 3, medios)

        ws = self._libro(response).active
        imagenes = self._imagenes(ws)
        fila_fibra = self._fila_de(ws, 'Fibra 12H', 4)
        fila_conector = self._fila_de(ws, 'Conector SC', 4)
        self.assertIsNotNone(fila_fibra)
        self.assertIsNotNone(fila_conector)
        # FOTO ANTES (columna J) de la 1ª fila y FOTO DESPUÉS (L) de la 2ª.
        self.assertIn((fila_fibra, 10), imagenes)
        self.assertIn((fila_conector, 11), imagenes)
        self.assertNotIn((fila_conector, 10), imagenes)
        self.assertNotIn((fila_fibra, 11), imagenes)

    def test_foto_de_material_sin_fila_que_coincidir_cae_en_el_registro(self):
        rutas = self._guardar_fotos(1)
        actividad = self._emergencia(evidencias=[
            # Solo hay 2 materiales: la fila 9 no existe y la foto no se pierde.
            {'seccion': 'materiales', 'campo_origen': 'material_9_foto_antes',
             'ruta_archivo': rutas[0], 'orden': 1},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 1, medios)
        # Ninguna fila de material la absorbió: sigue en el registro general.
        ws = self._libro(response).active
        self.assertNotIn(
            (self._fila_de(ws, 'Fibra 12H', 4), 10), self._imagenes(ws)
        )
        self.assertIn('5. EVIDENCIAS FOTOGRÁFICAS', self._todos(ws))

    # ── cabecera de cada foto y lo que no es evidencia ───────────────────────
    def test_el_rotulo_de_foto_prefiere_la_descripcion_escrita(self):
        from types import SimpleNamespace

        from apps.smu.export.base import rotulo_evidencia

        # 1. La descripción que el usuario escribió manda sobre cualquier cosa.
        self.assertEqual(
            rotulo_evidencia(SimpleNamespace(
                descripcion='  Módulo quemado   en el tablero ',
                campo_origen='ev-1790875901691', orden=1)),
            'MÓDULO QUEMADO EN EL TABLERO',
        )
        # 2. Sin descripción, un identificador interno no es legible: se usa
        #    el orden (que es lo que ya mostraba el formato de emergencias).
        self.assertEqual(
            rotulo_evidencia(SimpleNamespace(
                descripcion='', campo_origen='ev-1790875901691', orden=2)),
            'FOTO EVIDENCIA 2',
        )
        # 3. Sin descripción, el nombre del campo con espacios.
        self.assertEqual(
            rotulo_evidencia(SimpleNamespace(
                descripcion=None, campo_origen='condensadora_pos_mantenimiento',
                orden=3)),
            'CONDENSADORA POS MANTENIMIENTO',
        )

    def test_el_exporte_usa_la_descripcion_como_cabecera_de_la_foto(self):
        ruta = self._guardar_fotos(1)[0]
        actividad = self._emergencia(evidencias=[
            {'seccion': 'evidencias', 'campo_origen': 'ev-1790875901691',
             'ruta_archivo': ruta, 'orden': 1,
             'descripcion': 'Fuga en la conexión SC/PC'},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        ws = self._libro(response).active
        valores = self._todos(ws)
        self.assertIn('FUGA EN LA CONEXIÓN SC/PC', valores)
        # El identificador interno no llega a la cabecera.
        self.assertNotIn('EV-1790875901691', valores)

    def test_las_fotos_de_certificado_se_incrustan_en_el_reporte(self):
        rutas = self._guardar_fotos(2)
        actividad = self._preventivo_aa(certificados=[{
            'tipo': 'CONTE', 'categoria': 'Alturas',
            'ruta_certificado': rutas[0], 'ruta_foto_sitio': rutas[1],
            'orden': 1,
        }])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 2, medios)
        valores = self._todos(self._libro(response).active)
        self.assertIn('CERTIFICADO LABORAL — CONTE · ALTURAS', valores)
        self.assertIn('FOTO DEL CERTIFICADO EN SITIO — CONTE · ALTURAS', valores)

    def test_la_firma_con_imagen_también_se_incrusta(self):
        ruta = self._guardar_fotos(1)[0]
        actividad = self._emergencia(firmas_cierre=[
            {'rol': 'tecnico', 'nombre': 'Jorge Técnico',
             'ruta_firma': ruta, 'orden': 1},
            {'rol': 'revisor', 'nombre': 'Ana Revisora',
             'ruta_firma': 'firma firmmita', 'orden': 2},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 1, medios)
        valores = self._todos(self._libro(response).active)
        self.assertIn('FIRMA TECNICO · JORGE TÉCNICO', valores)
        # La revisora solo escribió texto en el campo: no es una imagen, así
        # que no se abre una caja en blanco por ella.
        self.assertNotIn('FIRMA REVISOR · ANA REVISORA', valores)

    def test_un_mismo_archivo_usado_dos_veces_no_se_pinta_dos_veces(self):
        ruta = self._guardar_fotos(1)[0]
        actividad = self._preventivo_aa(certificados=[{
            'tipo': 'CONTE', 'categoria': 'Alturas',
            'ruta_certificado': ruta, 'ruta_foto_sitio': ruta, 'orden': 1,
        }])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        # Certificado y foto de sitio apuntan al mismo archivo: una sola caja.
        self.assertEqual(len(medios), 1, medios)

    def test_los_adjuntos_se_pintan_en_los_6_formatos(self):
        pares = [
            ('preventivos', 'aire_acondicionado'),
            ('preventivos', 'planta'),
            ('correctivos', 'estandar'),
            ('emergencias', 'estandar'),
            ('correctivos_capex', 'tipologia1'),
            ('correctivos_capex', 'tipologia5'),
        ]
        for categoria, tipo in pares:
            with self.subTest(categoria=categoria, tipo_formulario=tipo):
                ruta = self._guardar_fotos(1)[0]
                actividad = crear_actividad_smu({
                    'categoria': categoria,
                    'tipo_formulario': tipo,
                    'nombre_estacion': f'EST {tipo}',
                    'responsable_cedula': '99999999',
                    'certificados': [{'tipo': 'CONTE', 'categoria': 'Alturas',
                                      'ruta_certificado': ruta, 'orden': 1}],
                })
                response = self._exportar(actividad)

                self.assertEqual(response.status_code, 200,
                                 response.content[:400])
                ws = self._libro(response).active
                self.assertIn('CERTIFICADO LABORAL — CONTE · ALTURAS',
                              self._todos(ws))
                self.assertEqual(len(ws._images), 1, (categoria, tipo))

    def test_las_fotos_se_distribuyen_tres_por_fila(self):
        rutas = self._guardar_fotos(5)
        evidencias = [
            {'seccion': 'anexos_fotograficos', 'campo_origen': f'foto_{i}',
             'ruta_archivo': rutas[i - 1], 'orden': i}
            for i in range(1, 6)
        ]
        actividad = self._emergencia(evidencias=evidencias)
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        ws = self._libro(response).active
        imagenes = self._imagenes(ws)

        # 5 fotos en dos filas: 3 + 2 (no 2 + 2 + 1).
        filas = sorted({fila for fila, _ in imagenes})
        self.assertEqual(len(imagenes), 5, imagenes)
        self.assertEqual(
            [sum(1 for fila, _ in imagenes if fila == fila_) for fila_ in filas],
            [3, 2],
        )
        # Las cajas arrancan en A, E o I: 4 columnas cada una.
        self.assertTrue(all(col in (1, 5, 9) for _, col in imagenes), imagenes)

        # El hueco que sobra en la última fila no se dibuja como caja gris.
        cajas = [rango for rango in ws.merged_cells.ranges
                 if rango.max_row - rango.min_row == 5
                 and rango.max_col - rango.min_col == 3]
        self.assertEqual(sorted(rango.min_col for rango in cajas),
                         [1, 1, 5, 5, 9], cajas)

    # ── las 6 fichas del módulo ──────────────────────────────────────────────
    def test_las_6_fichas_del_modulo_se_exportan(self):
        pares = [
            ('preventivos', 'aire_acondicionado'),
            ('preventivos', 'planta'),
            ('correctivos', 'estandar'),
            ('emergencias', 'estandar'),
            ('correctivos_capex', 'tipologia1'),
            ('correctivos_capex', 'tipologia3'),
            ('correctivos_capex', 'tipologia5'),
        ]
        for categoria, tipo in pares:
            with self.subTest(categoria=categoria, tipo_formulario=tipo):
                actividad = crear_actividad_smu({
                    'categoria': categoria,
                    'tipo_formulario': tipo,
                    'nombre_estacion': f'EST {tipo}',
                    'responsable_cedula': '99999999',
                })
                response = self._exportar(actividad)

                self.assertEqual(response.status_code, 200,
                                 response.content[:400])

    # ── preventivo de aire acondicionado ─────────────────────────────────────
    def _preventivo_aa(self, **extra):
        datos = {
            'categoria': 'preventivos',
            'tipo_formulario': 'aire_acondicionado',
            'nombre_estacion': 'ESTACIÓN AIRE 1',
            'codigo_ot': 'OT-AA-9',
            'departamento': 'ANTIOQUIA',
            'direccion': 'Calle 10 #20-30',
            'tipo_estacion': 'EB',
            'site_owner': 'TIGO',
            'empresa': 'CINCO SAS',
            'responsable_cedula': '44444444',
            'responsable_nombre': 'Tester AA',
            'fecha_inicio': timezone.now(),
            'tecnicos': [
                {'cedula': '44444444', 'nombre': 'Tester AA',
                 'es_principal': True},
                {'cedula': '55555555', 'nombre': 'Segundo Tecnico'},
            ],
            'detalle_preventivo_aa': {
                'marca': 'Carrier', 'modelo': 'X-200', 'serial': 'SN123',
                'id_activo': 'ACT-1', 'tipo_aire': 'Split',
                'alimentacion_ac': '110V', 'voltaje_entrada': 110,
                'corriente': 12.5, 'capacidad_btu': 12000,
                'gestion_remota_ip': '10.0.0.5', 'cantidad_compresores': 2,
                'temp_cuarto': 24.5, 'temp_entrada': 18, 'temp_salida': 12,
                'temp_display': 21, 'ajuste_termostato': '21',
                'mp_termostato_post': '22',
                'acciones_observaciones': 'Se ajustó el termostato.',
                'plan_mejora': 'Cambiar filtros en la próxima visita.',
            },
            'checklist_aa': [
                {'item_numero': 1, 'estado': 'Bueno'},
                {'item_numero': 39, 'estado': 'Malo'},
            ],
            'aa_compresores': [{
                'orden': 1, 'marca': 'Copeland', 'serial': 'C1',
                'refrigerante': 'R410A', 'presion_succion': 120,
                'vl1': 110, 'vl2': 111, 'vl3': 112,
                'amp_l1': 1, 'amp_l2': 2, 'amp_l3': 3,
            }],
            'aa_condensadoras': [{
                'orden': 1, 'marca': 'Carrier', 'modelo': 'M1', 'serial': 'S1',
                'temperatura_entrada': 30, 'temperatura_salida': 25,
            }],
            'aa_manejadoras': [{'orden': 1, 'marca': 'Daikin', 'modelo': 'D1'}],
            'aa_acciones': [
                {'clave': 'limpieza_serpentines', 'valor': 'SI', 'orden': 1},
                {'clave': 'otras_reparaciones', 'valor': 'NO', 'orden': 1},
            ],
        }
        datos.update(extra)
        return crear_actividad_smu(datos)

    def test_export_preventivo_aa_devuelve_su_formato(self):
        actividad = self._preventivo_aa()
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertIn('preventivo_aa_ESTACION_AIRE_1_OTAA9.xlsx',
                      response['Content-Disposition'])
        ws = self._libro(response).active
        self.assertEqual(ws.title, 'Preventivo AA')
        valores = self._todos(ws)
        self.assertIn('MANTENIMIENTO PREVENTIVO AIRES ACONDICIONADOS', valores)
        self.assertIn('Carrier', valores)
        self.assertIn('Copeland', valores)
        self.assertIn('Daikin', valores)
        self.assertIn('LIMPIEZA DE SERPENTINES', valores)
        self.assertIn('SÍ', valores)
        # Responsables 1 y 2 (la plantilla los pide explícitos).
        self.assertIn('Tester AA (CC 44444444)', valores)
        self.assertIn('Segundo Tecnico (CC 55555555)', valores)
        self.assertIn('Se ajustó el termostato.', valores)

    def test_export_preventivo_aa_checklist_solo_los_diligenciados(self):
        ws = self._libro(self._exportar(self._preventivo_aa())).active
        valores = self._todos(ws)

        self.assertTrue(any(
            v.startswith('La fijación de las unidades condensadoras')
            for v in valores
        ))
        self.assertIn('Bueno', valores)
        self.assertIn('Malo', valores)
        # El ítem 8 no se diligenció: su párrafo no debe existir en el archivo.
        self.assertFalse(any(
            'Buena circulación de aire natural' in v for v in valores
        ))

    def test_export_preventivo_aa_incrusta_las_fotos(self):
        rutas = self._guardar_fotos(2)
        actividad = self._preventivo_aa(evidencias=[
            {'seccion': 'anexos_fotograficos',
             'campo_origen': 'condensadora_pos_mantenimiento',
             'ruta_archivo': rutas[0], 'orden': 1},
            {'seccion': 'anexos_fotograficos',
             'campo_origen': 'filtros_pos_mantenimiento',
             'ruta_archivo': rutas[1], 'orden': 2},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 2, medios)
        valores = self._todos(self._libro(response).active)
        self.assertIn('CONDENSADORA POS MANTENIMIENTO', valores)

    # ── preventivo de planta eléctrica ───────────────────────────────────────
    def _preventivo_planta(self, **extra):
        datos = {
            'categoria': 'preventivos',
            'tipo_formulario': 'planta',
            'nombre_estacion': 'ESTACIÓN GRUPO 7',
            'codigo_ot': 'OT-P-77',
            'regional': 'OCCIDENTE',
            'direccion': 'Vereda el Roble',
            'site_owner': 'CLARO',
            'empresa': 'CINCO SAS',
            'coordinador_aliado': 'Pedro Aliado',
            'responsable_cedula': '66666666',
            'responsable_nombre': 'Tester Planta',
            'fecha_inicio': timezone.now(),
            'detalle_preventivo_planta': {
                'jefatura': 'Jefatura Norte', 'zona_om': 'Zona 1',
                'modalidad': 'Alquiler', 'cantidad_plantas': 2,
                'estructura': 'EB-77', 'orden_trabajo_tas': 'TAS-99',
                'fecha_elaboracion_informe': timezone.localdate(),
                'plan_mejora_estado': 'Pendiente aprobación del plan.',
                'prueba_vacio': 'OK', 'prueba_con_carga': 'OK',
                'observaciones_pruebas': 'Sin novedades.',
                'cambio_aceite': 'SÍ', 'cambio_filtros_aire': 'NO',
                'observaciones_filtracion': 'Cambiar filtros el próximo mes.',
            },
            'plantas': [{
                'orden': 1, 'nombre_unidad': 'Planta Cummins',
                'equipo_marca': 'Cummins', 'equipo_modelo': 'C9',
                'equipo_serial': 'CN-9', 'equipo_rpm': 1800,
                'equipo_horas_trabajo': 1500.5,
                'param_vac_l1_l2': 220,
                'dimensionamiento_porc_carga': 75.5,
            }],
            'checklist_planta': [{
                'sistema': 'combustible', 'componente': 'conexiones',
                'estado': 'Bueno', 'detectar': 'Inspección visual',
                'corregir': 'Ajustar abrazaderas',
            }],
            'hallazgos_planta': [
                {'orden': 1, 'descripcion': 'Fuga en manguera.'},
            ],
        }
        datos.update(extra)
        return crear_actividad_smu(datos)

    def test_export_preventivo_planta_devuelve_su_formato(self):
        actividad = self._preventivo_planta()
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertIn('preventivo_planta_ESTACION_GRUPO_7_OTP77.xlsx',
                      response['Content-Disposition'])
        ws = self._libro(response).active
        self.assertEqual(ws.title, 'Preventivo Planta')
        valores = self._todos(ws)
        self.assertIn('MANTENIMIENTO PREVENTIVO PLANTA ELÉCTRICA', valores)
        self.assertIn('Jefatura Norte', valores)
        self.assertIn('PLANTA 1: Planta Cummins', valores)
        self.assertIn('Cummins', valores)
        self.assertIn('conexiones', valores)
        self.assertIn('Inspección visual', valores)
        self.assertIn('Fuga en manguera.', valores)
        self.assertIn('PRUEBA CON CARGA:', valores)

    def test_export_preventivo_planta_minimo_también_exporta(self):
        actividad = crear_actividad_smu({
            'categoria': 'preventivos',
            'tipo_formulario': 'planta',
            'nombre_estacion': 'GRUPO SOLO CABECERA',
            'responsable_cedula': '77777777',
        })
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])

    def test_export_preventivo_planta_fotos_de_hallazgo_y_anexos(self):
        rutas = self._guardar_fotos(2)
        actividad = self._preventivo_planta(evidencias=[
            {'seccion': 'hallazgos_planta',
             'campo_origen': 'hallazgo_1_evidencia_1',
             'ruta_archivo': rutas[0], 'orden': 1},
            {'seccion': 'anexos_planta', 'campo_origen': 'placa_planta',
             'ruta_archivo': rutas[1], 'orden': 2},
        ])
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 2, medios)
        valores = self._todos(self._libro(response).active)
        self.assertIn('PLACA PLANTA', valores)

    # ── correctivos CAPEX (tipologías 1, 3 y 5) ─────────────────────────────
    def _capex(self, tipologia='tipologia1', evidencias=None, **extra):
        datos = {
            'categoria': 'correctivos_capex',
            'tipo_formulario': tipologia,
            'nombre_estacion': 'ESTACIÓN SPT 5',
            'codigo_ot': 'OT-C-55',
            'tipo_estacion': 'Torre',
            'site_owner': 'MOVISTAR',
            'empresa': 'CINCO SAS',
            'coordinador_aliado': 'Luis Aliado',
            'responsable_cedula': '88888888',
            'responsable_nombre': 'Tester Capex',
            'fecha_inicio': timezone.now(),
            'materiales': [
                {'tipo_registro': 'inventario_capex',
                 'texto_sap': 'VARILLA 5/8', 'codigo_sap': '1001',
                 'alcance': '3 unidades por sitio',
                 'comentarios': 'Suministro en bodega',
                 'cantidad_estandar': 3, 'cantidad_real': 2,
                 'unidad_medida': 'UND'},
                {'tipo_registro': 'mano_obra_capex',
                 'texto_sap': 'EXCAVACION MANUAL', 'codigo_sap': '2002',
                 'descripcion': 'Excavación y prepare de terreno',
                 'cantidad_real': 4, 'unidad_medida': 'UND'},
            ],
            'transportes': [{'tipo_transporte': 'Camioneta',
                             'codigo_sap': 'TR-5', 'distancia_km': 8,
                             'tiempo_traslado': '30 min',
                             'descripcion': 'Traslado de materiales'}],
            'detalle_capex': {
                'tipologia': tipologia,
                'recomendacion_final': 'Aprobado por ingeniería.',
            },
            'spt_filas': [],
        }
        if tipologia == 'tipologia1':
            datos['detalle_capex'].update({
                'descripcion_general_actividades':
                    'Se ejecutó la reforma del SPT.',
                'spt_naturaleza': 'Terreno arcilloso',
                'spt_recomendacion': 'Volver a medir en temporada seca.',
                'panoramica_recomendacion': 'Ver plano adjunto.',
                'otras_actividades_1': 'Movimiento de tierras',
                'texto_justificacion_otras_actividades':
                    'Aprobado por ingeniería de sitio.',
                'matricula_nombre': 'Ing. Prueba',
                'matricula_numero': '12345',
                'matricula_fecha': timezone.localdate(),
                'recomendaciones_aliado': 'Usar cable 6 AWG.',
            })
            datos['spt_filas'] = [
                {'orden': 1, 'distancia': '1.5 m', 'medida_ohmio': '12',
                 'resistividad': '45'},
            ]
        if evidencias is not None:
            datos['evidencias'] = evidencias
        datos.update(extra)
        return crear_actividad_smu(datos)

    def test_export_capex_tipologia1_devuelve_su_formato(self):
        actividad = self._capex()
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertIn('capex_tipologia1_ESTACION_SPT_5_OTC55.xlsx',
                      response['Content-Disposition'])
        ws = self._libro(response).active
        self.assertEqual(ws.title, 'Tipologia SPT')
        valores = self._todos(ws)
        self.assertTrue(any('SISTEMA DE PUESTA A TIERRA' in v for v in valores))
        self.assertIn('VARILLA 5/8', valores)
        self.assertIn('1001', valores)
        self.assertTrue(any('Camioneta' in v for v in valores))
        self.assertIn('Terreno arcilloso', valores)
        self.assertIn('1.5 m', valores)
        self.assertTrue(any('Movimiento de tierras' in v for v in valores))
        self.assertIn('Ing. Prueba', valores)
        # Metadatos normativos de la plantilla de la tipología 1.
        self.assertIn('Reposición por Hurto Renovación por alto deterioro',
                      valores)

    def test_export_capex_tipologias_3_y_5(self):
        for tipologia, hoja in (('tipologia3', 'Tipologia 3'),
                                ('tipologia5', 'Tipologia 5')):
            with self.subTest(tipologia=tipologia):
                actividad = self._capex(tipologia)
                response = self._exportar(actividad)

                self.assertEqual(response.status_code, 200,
                                 response.content[:400])
                ws = self._libro(response).active
                self.assertEqual(ws.title, hoja)
                valores = self._todos(ws)
                self.assertIn('VARILLA 5/8', valores)
                # Sin datos SPT ni metadatos: esas secciones no existen.
                self.assertFalse(any('REFORMA SPT' in v for v in valores))
                self.assertFalse(any('Caso de uso' in v for v in valores))
                self.assertIn(f'capex_{tipologia}_',
                              response['Content-Disposition'])

    def test_export_capex_incrusta_todas_las_fotos(self):
        rutas = self._guardar_fotos(4)
        evidencias = [
            {'seccion': 'inventario', 'campo_origen': 'insumo_1_foto',
             'ruta_archivo': rutas[0], 'orden': 1},
            {'seccion': 'mano_obra', 'campo_origen': 'mo_1_foto_antes',
             'ruta_archivo': rutas[1], 'orden': 2},
            {'seccion': 'panoramica',
             'campo_origen': 'foto_panoramica_preview',
             'ruta_archivo': rutas[2], 'orden': 3},
            {'seccion': 'justificacion',
             'campo_origen': 'fotos_justificacion_1',
             'ruta_archivo': rutas[3], 'orden': 4},
        ]
        actividad = self._capex(evidencias=evidencias)
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        # Cada foto queda en su sección (inventario, mano de obra, panorámica
        # y justificación): ninguna se pierde ni se duplica.
        self.assertEqual(len(medios), 4, medios)

    def test_export_capex_fotos_sin_destino_caen_en_el_registro(self):
        rutas = self._guardar_fotos(2)
        evidencias = [
            {'seccion': 'inventario', 'campo_origen': 'insumo_9_foto',
             'ruta_archivo': rutas[0], 'orden': 1},
            {'seccion': 'ejecucion', 'campo_origen': 'foto_durante_1',
             'ruta_archivo': rutas[1], 'orden': 2},
        ]
        actividad = self._capex(evidencias=evidencias)
        response = self._exportar(actividad)

        self.assertEqual(response.status_code, 200, response.content[:400])
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            medios = [n for n in z.namelist() if n.startswith('xl/media/')]
        self.assertEqual(len(medios), 2, medios)
        valores = self._todos(self._libro(response).active)
        self.assertIn('EJECUCION', valores)
