// src/modules/smu/evidencias.ts
//
// Utilidades puras del listado de evidencias fotográficas de los formularios
// SMU. Viven fuera del componente a propósito: `node --test` no puede importar
// un .tsx (JSX) y así la baja de una foto queda cubierta por un test de
// regresión.
import type { EvidenciaFotoItem } from "./components/correctivos/FormCorrectivoEmergenciaSlider";

/**
 * Quita la foto de una evidencia (vista previa, `File` y nombre), conservando
 * la fila y su descripción.
 *
 * `FotoSlotCard` avisa la baja con `onUpload(null)` **y** `onRemove`: si solo
 * se borra el `previewUrl`, `buildCorrectivoEmergenciaPayload` sigue leyendo
 * `e.file` y encola la subida, con lo que la foto que el usuario "eliminó"
 * termina guardada.
 *
 * Devuelve una lista nueva (misma filosofía que los builders de payload).
 */
export const quitarFotoEvidencia = (
  evidencias: EvidenciaFotoItem[],
  id: string,
): EvidenciaFotoItem[] =>
  evidencias.map((ev) =>
    ev.id === id
      ? { ...ev, previewUrl: undefined, file: undefined, nombre: undefined }
      : ev,
  );
