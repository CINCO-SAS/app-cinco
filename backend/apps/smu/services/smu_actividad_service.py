from django.db import transaction
from apps.smu.models import (
    SmuActividad,
    SmuActividadTecnico,
    SmuActividadMaterial,
    SmuActividadEvidencia,
    SmuActividadTransporte,
    SmuActividadCierreFirma,
    SmuActividadCertificado,
    SmuDetallePreventivoAa,
    SmuDetallePreventivoAaChecklist,
    SmuPreventivoAaCompresor,
    SmuPreventivoAaCondensadora,
    SmuPreventivoAaManejadora,
    SmuPreventivoAaAccion,
    SmuDetallePreventivoPlanta,
    SmuPreventivoPlanta,
    SmuPreventivoPlantaHallazgo,
    SmuDetallePreventivoPlantaChecklist,
    SmuDetalleFallaIntervencion,
    SmuDetalleCapex,
    SmuDetalleCapexSptFila,
)


@transaction.atomic
def crear_actividad_smu(validated_data):
    """
    Crea una actividad central SMU y todas sus tablas/relaciones anidadas
    dentro de una sola transacción atómica.
    """
    tecnicos_data = validated_data.pop('tecnicos', [])
    materiales_data = validated_data.pop('materiales', [])
    evidencias_data = validated_data.pop('evidencias', [])
    transportes_data = validated_data.pop('transportes', [])

    # Firmas de cierre y certificados
    firmas_cierre_data = validated_data.pop('firmas_cierre', [])
    certificados_data = validated_data.pop('certificados', [])

    # Detalle Preventivo AA + sus subtablas
    detalle_aa_data = validated_data.pop('detalle_preventivo_aa', None)
    checklist_aa_data = validated_data.pop('checklist_aa', [])
    aa_compresores_data = validated_data.pop('aa_compresores', [])
    aa_condensadoras_data = validated_data.pop('aa_condensadoras', [])
    aa_manejadoras_data = validated_data.pop('aa_manejadoras', [])
    aa_acciones_data = validated_data.pop('aa_acciones', [])

    # Detalle Preventivo Planta + sus subtablas
    detalle_planta_data = validated_data.pop('detalle_preventivo_planta', None)
    checklist_planta_data = validated_data.pop('checklist_planta', [])
    plantas_data = validated_data.pop('plantas', [])
    hallazgos_planta_data = validated_data.pop('hallazgos_planta', [])

    # Detalle Falla / Intervención
    detalle_falla_data = validated_data.pop('detalle_falla_intervencion', None)

    # Detalle CAPEX + filas SPT
    detalle_capex_data = validated_data.pop('detalle_capex', None)
    spt_filas_data = validated_data.pop('spt_filas', [])

    # 1. Crear actividad cabecera principal
    actividad = SmuActividad.objects.create(**validated_data)

    # 2. Crear Técnicos
    for tec in tecnicos_data:
        SmuActividadTecnico.objects.create(actividad=actividad, **tec)

    # 3. Crear Materiales y guardar referencia para evidencias si aplica
    materiales_creados = []
    for mat in materiales_data:
        material_obj = SmuActividadMaterial.objects.create(actividad=actividad, **mat)
        materiales_creados.append(material_obj)

    # 4. Crear Evidencias
    for ev in evidencias_data:
        SmuActividadEvidencia.objects.create(actividad=actividad, **ev)

    # 5. Crear Transportes
    for tr in transportes_data:
        SmuActividadTransporte.objects.create(actividad=actividad, **tr)

    # 6. Crear Firmas de Cierre (si aplica)
    for firma in firmas_cierre_data:
        SmuActividadCierreFirma.objects.create(actividad=actividad, **firma)

    # 7. Crear Certificados (si aplica)
    for cert in certificados_data:
        SmuActividadCertificado.objects.create(actividad=actividad, **cert)

    # 8. Crear Detalle Preventivo Aire Acondicionado + Checklist (si aplica)
    if detalle_aa_data:
        SmuDetallePreventivoAa.objects.create(actividad=actividad, **detalle_aa_data)

    for chk_aa in checklist_aa_data:
        SmuDetallePreventivoAaChecklist.objects.create(actividad=actividad, **chk_aa)

    # 9. Crear Compresores AA (si aplica)
    for comp in aa_compresores_data:
        SmuPreventivoAaCompresor.objects.create(actividad=actividad, **comp)

    # 10. Crear Condensadoras AA (si aplica)
    for cond in aa_condensadoras_data:
        SmuPreventivoAaCondensadora.objects.create(actividad=actividad, **cond)

    # 11. Crear Manejadoras AA (si aplica)
    for man in aa_manejadoras_data:
        SmuPreventivoAaManejadora.objects.create(actividad=actividad, **man)

    # 12. Crear Acciones AA tri-estado (si aplica)
    for acc in aa_acciones_data:
        SmuPreventivoAaAccion.objects.create(actividad=actividad, **acc)

    # 13. Crear Detalle Preventivo Planta Eléctrica + Checklist (si aplica)
    if detalle_planta_data:
        SmuDetallePreventivoPlanta.objects.create(actividad=actividad, **detalle_planta_data)

    for chk_planta in checklist_planta_data:
        SmuDetallePreventivoPlantaChecklist.objects.create(actividad=actividad, **chk_planta)

    # 14. Crear Plantas Eléctricas registradas (si aplica)
    for planta in plantas_data:
        SmuPreventivoPlanta.objects.create(actividad=actividad, **planta)

    # 15. Crear Hallazgos del Plan de Mejora (si aplica)
    for hall in hallazgos_planta_data:
        SmuPreventivoPlantaHallazgo.objects.create(actividad=actividad, **hall)

    # 16. Crear Detalle Falla / Intervención (si aplica)
    if detalle_falla_data:
        SmuDetalleFallaIntervencion.objects.create(actividad=actividad, **detalle_falla_data)

    # 17. Crear Detalle CAPEX (si aplica)
    if detalle_capex_data:
        SmuDetalleCapex.objects.create(actividad=actividad, **detalle_capex_data)

    # 18. Crear Filas SPT / Resistividad Wenner (si aplica)
    for fila in spt_filas_data:
        SmuDetalleCapexSptFila.objects.create(actividad=actividad, **fila)

    return actividad
