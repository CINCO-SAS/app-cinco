from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import TestCase as DjangoTestCase

from apps.operaciones.models import (
	Actividad,
	ActividadOT,
	normalize_ot_values,
)
from apps.operaciones.serializers.actividad_serializer import ActividadWriteSerializer
from apps.operaciones.services.actividad_service import ActividadService


class ActividadServiceTests(TestCase):
	def test_ot_helpers_normalize_and_serialize_values(self):
		values = normalize_ot_values([" OT-1 ", "OT-2", "OT-1", "", None])

		self.assertEqual(values, ["OT-1", "OT-2"])

	def test_eliminar_hard_delete_requires_superuser(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, is_superuser=False)

		result = ActividadService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=True,
		)

		self.assertFalse(result)
		instance.delete.assert_not_called()

	def test_eliminar_hard_delete_superuser(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, is_superuser=True)

		result = ActividadService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=True,
		)

		self.assertTrue(result)
		instance.delete.assert_called_once()

	def test_eliminar_soft_delete_marks_flags(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, id=99)

		result = ActividadService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=False,
		)

		self.assertTrue(result)
		self.assertTrue(instance.is_deleted)
		self.assertEqual(instance.deleted_by_id, 99)
		instance.save.assert_called_once_with(
			update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at']
		)

	def test_actualizar_asigna_updated_by_id_correctamente(self):
		instance = MagicMock()
		instance.id = 10
		validated_data = {"estado": "en_progreso"}

		ActividadService.actualizar(
			instance,
			validated_data,
			actor_user_id=45,
		)

		self.assertEqual(instance.estado, "en_progreso")
		self.assertEqual(instance.updated_by_id, 45)
		instance.save.assert_called_once()

	@patch('apps.operaciones.services.actividad_service.Actividad.objects')
	def test_listar_applies_default_base_filter(self, actividad_objects):
		queryset = MagicMock()
		queryset.select_related.return_value = queryset
		queryset.prefetch_related.return_value = queryset
		actividad_objects.filter.return_value = queryset

		ActividadService.listar(usuario_id=None, filtros={})

		actividad_objects.filter.assert_called_once_with(is_deleted=False)
		queryset.select_related.assert_called_once_with(
			'detalle',
			'ubicacion',
			'responsable_snapshot'
		)
		queryset.prefetch_related.assert_called_once_with('ot_relaciones')


class ActividadOTRulesTests(DjangoTestCase):
	def test_validar_ots_unicas_detecta_ot_en_otra_actividad(self):
		actividad = Actividad.objects.create(
			ot='OT-100',
			responsable_id=1,
		)
		ActividadOT.objects.create(
			actividad=actividad,
			ot='OT-100',
			created_by=1,
			updated_by=1,
		)

		with self.assertRaisesMessage(
			ValueError,
			'Las siguientes OTs ya están asociadas a otra actividad: OT-100',
		):
			ActividadService.validar_ots_unicas(['OT-100'], actividad_id=2)

	def test_validar_ots_unicas_permita_ot_de_la_misma_actividad(self):
		actividad = Actividad.objects.create(
			ot='OT-100',
			responsable_id=1,
		)
		ActividadOT.objects.create(
			actividad=actividad,
			ot='OT-100',
			created_by=1,
			updated_by=1,
		)

		ActividadService.validar_ots_unicas(['OT-100'], actividad_id=actividad.id)


class ActividadServiceOTSyncTests(DjangoTestCase):
	def test_sync_ots_recalcula_fechas_padre_correctamente(self):
		actividad = Actividad.objects.create(
			responsable_id=1,
			fecha_inicio="2026-05-01",
			fecha_fin_estimado="2026-05-02"
		)

		ots_data = [
			{'ot': 'OT-A', 'fecha_inicio': '2026-05-05', 'fecha_fin': '2026-05-15'},
			{'ot': 'OT-B', 'fecha_inicio': '2026-05-03', 'fecha_fin': '2026-05-10'},
			{'ot': 'OT-C', 'fecha_inicio': '2026-05-07', 'fecha_fin': '2026-05-20'},
		]

		ActividadService._sync_ots(actividad, ots_data, actor_user_id=1)
		actividad.refresh_from_db()

		self.assertEqual(actividad.ot, 'OT-A')
		from datetime import date
		self.assertEqual(actividad.fecha_inicio, date(2026, 5, 3))
		self.assertEqual(actividad.fecha_fin_estimado, date(2026, 5, 20))


class AgendaServiceTests(DjangoTestCase):
	def test_buscar_actividad_ot_retorna_none_cuando_no_existe(self):
		from apps.operaciones.services.agenda_service import AgendaService
		res = AgendaService.buscar_actividad_por_ot("OT-INEXISTENTE-99999")
		self.assertIsNone(res)

	def test_buscar_actividad_ot_retorna_fechas_correctas(self):
		from apps.operaciones.models import Actividad
		from apps.operaciones.services.agenda_service import AgendaService
		act = Actividad.objects.create(
			ot="OT-TEST-AGENDA-01",
			responsable_id=1,
			fecha_inicio="2026-06-15",
			fecha_fin_estimado="2026-06-20",
		)
		res = AgendaService.buscar_actividad_por_ot("OT-TEST-AGENDA-01")
		self.assertIsNotNone(res)
		self.assertEqual(res["ot"], "OT-TEST-AGENDA-01")
		self.assertEqual(res["fecha_inicio"], "2026-06-15")
		self.assertEqual(res["fecha_fin_estimado"], "2026-06-20")




class ActividadWriteSerializerValidationTests(TestCase):
	def test_acepta_campos_opcionales_del_front_en_blanco(self):
		payload = {
			"ots": [
				{
					"ot": "00010",
					"fecha_inicio": "",
					"fecha_fin": "",
				}
			],
			"estado": "pendiente",
			"responsable_id": 1,
			"fecha_inicio": "2026-06-10",
			"fecha_fin_estimado": "2026-06-12",
			"detalle": {
				"tipo_trabajo": "MANTENIMIENTO",
				"descripcion": "",
			},
			"ubicacion": {
				"direccion": "Calle 1",
				"coordenada_x": "",
				"coordenada_y": "",
				"zona": "",
				"nodo": "",
			},
		}

		with patch('apps.operaciones.serializers.actividad_serializer.EmpleadoService.existe', return_value=True), \
			 patch('apps.operaciones.serializers.actividad_serializer.ActividadService.validar_ots_unicas'):
			serializer = ActividadWriteSerializer(data=payload)
			self.assertTrue(serializer.is_valid(), serializer.errors)
			self.assertEqual(serializer.validated_data.get('responsable_id'), 1)

	def test_acepta_ubicacion_con_campos_opcionales_vacios(self):
		payload = {
			"ots": [
				{
					"ot": "00010",
					"fecha_inicio": "2026-06-10",
					"fecha_fin": "2026-06-12",
				}
			],
			"estado": "pendiente",
			"responsable_id": 1,
			"fecha_inicio": "2026-06-10",
			"fecha_fin_estimado": "2026-06-12",
			"detalle": {
				"tipo_trabajo": "MANTENIMIENTO",
				"descripcion": "Prueba",
			},
			"ubicacion": {
				"direccion": "Calle 1",
				"coordenada_x": "",
				"coordenada_y": "",
				"zona": "",
				"nodo": "N600",
			},
		}

		with patch('apps.operaciones.serializers.actividad_serializer.EmpleadoService.existe', return_value=True), \
			 patch('apps.operaciones.serializers.actividad_serializer.ActividadService.validar_ots_unicas'):
			serializer = ActividadWriteSerializer(data=payload)
			self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_acepta_ot_sin_fechas_cuando_front_las_envia_vacias(self):
		payload = {
			"ots": [
				{
					"ot": "00010",
					"fecha_inicio": "",
					"fecha_fin": "",
				},
				{
					"ot": "00011",
					"fecha_inicio": "",
					"fecha_fin": "",
				}
			],
			"estado": "pendiente",
			"responsable_id": 1,
			"fecha_inicio": "2026-06-10",
			"fecha_fin_estimado": "2026-06-12",
			"detalle": {
				"tipo_trabajo": "MANTENIMIENTO",
				"descripcion": "Prueba",
			},
			"ubicacion": {
				"direccion": "Calle 1",
				"coordenada_x": "",
				"coordenada_y": "",
				"zona": "",
				"nodo": "",
			},
		}

		with patch('apps.operaciones.serializers.actividad_serializer.EmpleadoService.existe', return_value=True), \
			 patch('apps.operaciones.serializers.actividad_serializer.ActividadService.validar_ots_unicas'):
			serializer = ActividadWriteSerializer(data=payload)
			self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_rechaza_fecha_fin_estimado_menor_a_fecha_inicio(self):
		payload = {
			"ots": [
				{
					"ot": "00010",
					"fecha_inicio": "2026-06-10",
					"fecha_fin": "2026-06-12",
				}
			],
			"estado": "pendiente",
			"responsable_id": 1,
			"fecha_inicio": "2026-06-10",
			"fecha_fin_estimado": "2026-06-01",
			"detalle": {
				"tipo_trabajo": "MANTENIMIENTO",
				"descripcion": "Prueba",
			},
			"ubicacion": {
				"direccion": "Calle 1",
				"coordenada_x": "",
				"coordenada_y": "",
				"zona": "",
				"nodo": "N600",
			},
		}

		with patch('apps.operaciones.serializers.actividad_serializer.EmpleadoService.existe', return_value=True), \
			 patch('apps.operaciones.serializers.actividad_serializer.ActividadService.validar_ots_unicas'):
			serializer = ActividadWriteSerializer(data=payload)
			self.assertFalse(serializer.is_valid())
			self.assertEqual(
				serializer.errors["fecha_fin_estimado"][0],
				"La fecha fin estimada no puede ser menor que la fecha inicio.",
			)

	def test_rechaza_ot_con_fecha_fin_menor_a_fecha_inicio(self):
		payload = {
			"ots": [
				{
					"ot": "00010",
					"fecha_inicio": "2026-06-10",
					"fecha_fin": "2026-06-01",
				}
			],
			"estado": "pendiente",
			"responsable_id": 1,
			"fecha_inicio": "2026-06-10",
			"fecha_fin_estimado": "2026-06-12",
			"detalle": {
				"tipo_trabajo": "MANTENIMIENTO",
				"descripcion": "Prueba",
			},
			"ubicacion": {
				"direccion": "Calle 1",
				"coordenada_x": "",
				"coordenada_y": "",
				"zona": "",
				"nodo": "N600",
			},
		}

		with patch('apps.operaciones.serializers.actividad_serializer.EmpleadoService.existe', return_value=True), \
			 patch('apps.operaciones.serializers.actividad_serializer.ActividadService.validar_ots_unicas'):
			serializer = ActividadWriteSerializer(data=payload)
			self.assertFalse(serializer.is_valid())
			self.assertEqual(
				serializer.errors["ots"][0],
				"La OT 00010 tiene una fecha fin menor que la fecha inicio.",
			)


class AgendaApiTests(TestCase):
	def test_serializer_agenda_mes_query_valido(self):
		from apps.operaciones.serializers.agenda_serializer import AgendaMesQuerySerializer
		serializer = AgendaMesQuerySerializer(data={"mes": "06", "yyyy": "2026"})
		self.assertTrue(serializer.is_valid())

	def test_serializer_agenda_parametros_carpeta(self):
		from apps.operaciones.serializers.agenda_serializer import AgendaParametrosCarpetaSaveSerializer
		serializer = AgendaParametrosCarpetaSaveSerializer(data={"sede": "medellin", "data_param": [{"param": "1", "color": "#ff0000"}]})
		self.assertTrue(serializer.is_valid())

	def test_serializer_agenda_importar_csv(self):
		from django.core.files.uploadedfile import SimpleUploadedFile
		from apps.operaciones.serializers.agenda_serializer import AgendaImportarCsvSerializer
		file = SimpleUploadedFile("test.csv", b"cedula,ot,fecha_inicio,fecha_fin\n123,OT1,2026-06-01,2026-06-02", content_type="text/csv")
		serializer = AgendaImportarCsvSerializer(data={"file": file})
		self.assertTrue(serializer.is_valid(), serializer.errors)
