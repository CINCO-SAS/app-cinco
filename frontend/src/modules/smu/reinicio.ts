// src/modules/smu/reinicio.ts
//
// Reinicio del formulario después de un guardado exitoso: el usuario queda en
// el paso 1 con datos vacíos, listo para levantar una actividad nueva. Sin ese
// reinicio el botón "Guardar" seguía activo con los mismos datos y un segundo
// clic creaba la actividad dos veces.
import { liberarPreviewUrl } from "@/lib/fotos";

const esObjetoPlano = (valor: unknown): valor is Record<string, unknown> =>
  typeof valor === "object" &&
  valor !== null &&
  !Array.isArray(valor) &&
  !(valor instanceof Blob) && // File también es Blob
  !(valor instanceof Date);

/**
 * Copia de un estado inicial: dos niveles (el objeto y sus colecciones u
 * objetos anidados). Los formularios actualizan el estado de forma inmutable,
 * pero la copia garantiza que una futura actualización in-place no corrompa la
 * constante `initialFormData` compartida por todos los reinicios.
 */
export const clonarEstadoInicial = <T extends object>(base: T): T => {
  const copia = { ...base } as Record<string, unknown>;

  for (const clave of Object.keys(copia)) {
    const valor = copia[clave];
    if (Array.isArray(valor)) copia[clave] = [...valor];
    else if (esObjetoPlano(valor)) copia[clave] = { ...valor };
  }

  return copia as T;
};

/**
 * Revoca todas las URLs `blob:` del estado (vistas previas de fotos) para que
 * el reinicio no deje objectURL colgados en memoria. Recursivo y protegido
 * contra referencias circulares; ignora File/Blob/Date.
 */
export const liberarPreviews = (
  valor: unknown,
  visitados = new Set<object>(),
): void => {
  if (typeof valor === "string") {
    if (valor.startsWith("blob:")) liberarPreviewUrl(valor);
    return;
  }
  if (!valor || typeof valor !== "object") return;
  if (valor instanceof Blob || valor instanceof Date) return;
  if (visitados.has(valor)) return;
  visitados.add(valor);

  Object.values(valor).forEach((hijo) => liberarPreviews(hijo, visitados));
};
