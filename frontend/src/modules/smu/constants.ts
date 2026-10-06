// src/modules/smu/constants.ts
//
// Strings y claves de negocio del módulo SMU. Única fuente de verdad: los
// formularios y los builders de payload de `services/smu.service.ts` importan
// de aquí, de modo que un valor no puede divergir entre ambos lados.
//
// ⚠️ Este archivo no debe importar nada del módulo (ni del service) para no
// crear ciclos de imports entre sliders y servicio.

/**
 * Origen del material comprado directamente en sitio. Al elegirlo, el builder
 * marca `comprado_operario = true` en `SmuActividadMaterial`.
 */
export const ORIGEN_MATERIAL_OPERARIO = "OPERARIO (COMPRADO EN SITIO)";

/**
 * Claves tri-estado de "Acciones y Mantenimiento Ejecutado" (preventivo AA).
 * Se envían como `SmuPreventivoAaAccion.clave`.
 *
 * Deben coincidir con las que documenta el modelo backend
 * `SmuPreventivoAaAccion.clave` (`backend/apps/smu/models/smu_actividades.py`).
 */
export const CLAVES_ACCIONES_AA = [
  "limpieza_serpentines",
  "ajuste_elementos_control",
  "adicion_refrigerante",
  "estado_drenajes",
  "lubricacion_componentes",
  "cambio_filtros_secado",
  "alineacion_poleas",
  "cambio_componentes_electronicos",
  "cambio_compresor",
  "cambio_correas_filtros",
  "otras_reparaciones",
] as const;

export type ClaveAccionAA = (typeof CLAVES_ACCIONES_AA)[number];
