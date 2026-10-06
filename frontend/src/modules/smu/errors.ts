// src/modules/smu/errors.ts
//
// Manejo de errores de los 6 formularios SMU: `toastErrorActividad` para lo
// que reporta el backend y `manejarErrorGuardado` para todo lo inesperado.

import { toast } from "sonner";
import { getToastErrorMessage, type ApiErrorDetail } from "@/lib/errorHandler";
import { ErrorSubidaFotos } from "@/services/smu.service";

/**
 * `onError` de los 6 submits SMU (`useFormSubmit`).
 *
 * En vez de mostrar `err.message` crudo (que puede ser un texto técnico de
 * axios o el primer mensaje suelto de DRF), lista los errores por campo como
 * `campo: mensaje`; si no hay, cae en el mensaje genérico por tipo de error.
 *
 * Nota: `useFormSubmit` relanza el error después de llamar `onError`; el
 * `catch` del submit lo deriva a `manejarErrorGuardado`, que sabe que aquí ya
 * se avisó y no duplica el toast.
 */
export function toastErrorActividad(err: ApiErrorDetail): void {
  toast.error(getToastErrorMessage(err, "No se pudo guardar la actividad."));
}

/** Shape que devuelve `classifyError`/`useFormSubmit` (ya avisado por `onError`). */
const esErrorApi = (err: unknown): err is ApiErrorDetail =>
  typeof err === "object" &&
  err !== null &&
  "type" in err &&
  "status" in err;

/**
 * `catch` común de los 6 `handleSubmit` SMU.
 *
 * - `ErrorSubidaFotos`: avisa de la subida de fotos (único caso que `onError`
 *   **no** cubre, porque ocurre antes de `useFormSubmit`).
 * - `ApiErrorDetail`: ya lo avisó `onError` vía `toastErrorActividad`; aquí no
 *   se toca nada para no duplicar el toast.
 * - Cualquier otra excepción (un builder lanzando, una guarda inesperada…):
 *   antes caía en un `catch` mudo y el guardado "no pasaba nada"; ahora queda
 *   registrada en consola y se avisa al usuario.
 */
export function manejarErrorGuardado(err: unknown): void {
  if (err instanceof ErrorSubidaFotos) {
    toast.error(err.message);
    return;
  }
  if (esErrorApi(err)) return;

  console.error("[SMU] Error inesperado al guardar la actividad:", err);
  toast.error(
    "No se pudo guardar la actividad. Abre la consola del navegador (F12) para ver el detalle.",
  );
}
