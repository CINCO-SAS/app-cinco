import { STEPS_CONFIG_TIPOLOGIA_5 } from "./constants";
import {
  ActividadMOItem,
  FormCapexTipologia5Data,
  InsumoSAPItem,
  TransporteItem,
} from "./types";

/**
 * Evaluación de completitud del formulario CAPEX Tipología 5 (MT/BT).
 *
 * Cada paso de STEPS_CONFIG_TIPOLOGIA_5 tiene aquí su regla (indexada por
 * `id`) y alimenta el aviso que se muestra al consolidar el catálogo frecuente
 * (guardar / navegar de paso).
 *
 * ⚠️ Las reglas de "obligatorio" son de negocio: ajústalas aquí si algún campo
 * debe pasar a ser opcional (fotos, comentarios, etc.).
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
  [
    actividad.texto_sap,
    actividad.codigo_sap,
    actividad.alcance,
    actividad.descripcion,
  ].every(filled) &&
  Boolean(actividad.foto_antes_preview && actividad.foto_despues_preview);

const isTransporteComplete = (transporte: TransporteItem): boolean =>
  [
    transporte.tipo,
    transporte.codigo_sap,
    transporte.distancia_km,
    transporte.tiempo,
    transporte.descripcion,
  ].every(filled) &&
  Boolean(
    transporte.foto_antes_preview &&
    transporte.foto_durante_preview &&
    transporte.foto_despues_preview,
  );

const STEP_CHECKS: Record<string, (data: FormCapexTipologia5Data) => boolean> =
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
      data.actividades.length > 0 &&
      data.actividades.every(isActividadComplete),

    transportes: (data) =>
      data.transportes.length > 0 &&
      data.transportes.every(isTransporteComplete),

    plano: (data) =>
      [
        data.foto_panoramica_preview,
        data.foto_plano_preview,
        data.plano_recomendacion_aliado,
      ].every(Boolean),

    fuera_estandar: (data) =>
      filled(data.texto_justificacion) &&
      data.fotos_justificacion.some((foto) => Boolean(foto.previewUrl)),

    recomendaciones: (data) => filled(data.recomendaciones_finales),
  };

export interface StepCompletion {
  id: string;
  title: string;
  complete: boolean;
}

/** Estado de completitud de cada paso, en el orden de STEPS_CONFIG. */
export const evaluateTipologia5Steps = (
  data: FormCapexTipologia5Data,
): StepCompletion[] =>
  STEPS_CONFIG_TIPOLOGIA_5.map((step) => ({
    id: step.id,
    title: step.title,
    // Si un paso no tiene regla se considera pendente (seguro por defecto).
    complete: STEP_CHECKS[step.id]?.(data) ?? false,
  }));

/** true solo cuando todos los pasos están completos. */
export const isTipologia5FormComplete = (
  data: FormCapexTipologia5Data,
): boolean => evaluateTipologia5Steps(data).every((step) => step.complete);

/** Títulos de los pasos que faltan, para el aviso de consolidación. */
export const getPendingStepTitles = (data: FormCapexTipologia5Data): string[] =>
  evaluateTipologia5Steps(data)
    .filter((step) => !step.complete)
    .map((step) => step.title);
