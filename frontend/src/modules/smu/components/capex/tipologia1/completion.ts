import { STEPS_CONFIG_TIPOLOGIA_1 } from "./constants";
import {
  ActividadMOItem,
  FilaMedidaSPT,
  FormCapexTipologia1Data,
  InsumoSAPItem,
} from "./types";

/**
 * Evaluación de completitud del formulario CAPEX Tipología 1.
 *
 * Cada paso de STEPS_CONFIG_TIPOLOGIA_1 tiene aquí su regla (indexada por
 * `id`). El resultado alimenta:
 *
 *  - `isTipologia1FormComplete` → decide si consolidar muestra el aviso.
 *  - `getPendingStepTitles`     → lista los pasos faltantes en el aviso.
 *
 * ⚠️ Las reglas de "obligatorio" son de negocio: ajústalas aquí si algún campo
 * debe pasar a ser opcional (fotos, matrícula, etc.).
 */

const filled = (value?: string | null): boolean =>
  Boolean(value && value.trim().length > 0);

const isInsumoComplete = (insumo: InsumoSAPItem): boolean =>
  [
    insumo.texto_sap,
    insumo.codigo_sap,
    insumo.unidad_medida,
    insumo.cantidad_estandar,
    insumo.cantidad_real,
    insumo.alcance,
  ].every(filled) && Boolean(insumo.foto_preview);

const isActividadComplete = (actividad: ActividadMOItem): boolean =>
  [actividad.texto_sap, actividad.codigo_sap, actividad.alcance].every(
    filled,
  ) && Boolean(actividad.foto_antes_preview && actividad.foto_despues_preview);

const isFilaSptComplete = (fila: FilaMedidaSPT): boolean =>
  [fila.distancia, fila.medida_ohmio, fila.resistividad].every(filled);

const STEP_CHECKS: Record<string, (data: FormCapexTipologia1Data) => boolean> =
  {
    general: (data) =>
      [
        data.nombre_estacion,
        data.ot,
        data.fecha_inicio,
        data.fecha_fin,
        data.tipo_estacion,
        data.site_owner,
        data.empresa,
        data.coordinador_aliado,
      ].every(filled) && Boolean(data.responsable_ejecuta),

    suministros: (data) =>
      data.insumos.length > 0 && data.insumos.every(isInsumoComplete),

    actividades: (data) =>
      filled(data.descripcion_general_actividades) &&
      data.actividades.length > 0 &&
      data.actividades.every(isActividadComplete),

    transportes: (data) =>
      [
        data.transporte_tipo,
        data.transporte_codigo_sap,
        data.transporte_distancia_km,
        data.transporte_tiempo_desplazamiento,
        data.transporte_descripcion,
      ].every(filled) &&
      Boolean(
        data.transporte_foto_antes &&
        data.transporte_foto_durante &&
        data.transporte_foto_despues,
      ),

    spt: (data) =>
      [data.spt_naturaleza_terreno_desc, data.spt_recomendacion_aliado].every(
        filled,
      ) &&
      Boolean(data.spt_naturaleza_terreno_foto) &&
      data.filas_spt.length > 0 &&
      data.filas_spt.every(isFilaSptComplete),

    plano: (data) =>
      [
        data.foto_panoramica_preview,
        data.foto_plano_preview,
        data.plano_recomendacion_aliado,
      ].every(Boolean),

    fuera_estandar: (data) =>
      filled(data.texto_justificacion_otras_actividades) &&
      data.fotos_justificacion.some((foto) => Boolean(foto.previewUrl)) &&
      [
        data.foto_soporte_matricula_preview,
        data.matricula_nombre,
        data.matricula_numero,
        data.matricula_fecha,
      ].every(Boolean),

    cierre: (data) =>
      [
        data.recomendaciones_finales,
        data.responsable_entrega_nombre,
        data.responsable_entrega_cedula,
        data.responsable_entrega_cargo,
        data.responsable_entrega_fecha,
        data.responsable_entrega_firma,
        data.aprobado_nombre,
        data.aprobado_cedula,
        data.aprobado_cargo,
        data.aprobado_fecha,
        data.aprobado_firma,
      ].every(filled),
  };

export interface StepCompletion {
  id: string;
  title: string;
  complete: boolean;
}

/** Estado de completitud de cada paso, en el orden de STEPS_CONFIG. */
export const evaluateTipologia1Steps = (
  data: FormCapexTipologia1Data,
): StepCompletion[] =>
  STEPS_CONFIG_TIPOLOGIA_1.map((step) => ({
    id: step.id,
    title: step.title,
    // Si un paso no tiene regla se considera pendente (seguro por defecto).
    complete: STEP_CHECKS[step.id]?.(data) ?? false,
  }));

/** true solo cuando los 8 pasos están completos. */
export const isTipologia1FormComplete = (
  data: FormCapexTipologia1Data,
): boolean => evaluateTipologia1Steps(data).every((step) => step.complete);

/** Títulos de los pasos que faltan, para el aviso de consolidación. */
export const getPendingStepTitles = (data: FormCapexTipologia1Data): string[] =>
  evaluateTipologia1Steps(data)
    .filter((step) => !step.complete)
    .map((step) => step.title);
