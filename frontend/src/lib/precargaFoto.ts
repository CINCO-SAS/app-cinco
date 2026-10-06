// src/lib/precargaFoto.ts
//
// Registro de precarga de fotos. El módulo que quiera subir cada foto en
// cuanto el usuario la elige (SMU: POST /smu/evidencias/) registra aquí su
// subidor; los componentes de foto (FotoSlotCard) solo notifican "elegí una
// foto" y "la quité", sin importar ningún servicio concreto — así el
// componente global sigue siendo neutral y otros módulos que lo usen sin
// registrar nada conservan su flujo actual (subir al guardar, o no subir).
//
// Ventaja para el usuario de SMU: con muchas fotos, el envío final ya no
// espera la subida: solo usa las rutas que casi siempre ya llegaron.

/** Sube la foto ya elegida y devuelve su `ruta_archivo` en el servidor. */
export type PrecargadorFoto = (file: File) => Promise<string>;

let precargador: PrecargadorFoto | null = null;
let olvidador: ((file: File) => void) | null = null;

/**
 * Registra el subidor de un módulo (típicamente al cargar su servicio).
 * El último registro gana; `olvidar` es opcional y se usa cuando el usuario
 * quita o reemplaza la foto elegida.
 */
export const registrarPrecargaFoto = (
  precargar: PrecargadorFoto,
  olvidar?: (file: File) => void,
): void => {
  precargador = precargar;
  olvidador = olvidar ?? null;
};

/**
 * Notifica que el usuario eligió `file`. Devuelve la promesa de la subida en
 * curso (para que el componente pueda mostrar el estado) o `null` si no hay
 * precargador registrado: en ese caso nadie pre-carga y nada cambia.
 *
 * Un fallo rechaza la promesa; el componente lo ignora y el guardado
 * reintenta la subida (la precarga nunca bloquea el formulario).
 */
export const fotoElegida = (file: File): Promise<string> | null =>
  precargador ? precargador(file) : null;

/** El usuario quitó o reemplazó la foto: su precarga deja de interesar. */
export const olvidarFotoElegida = (file: File): void => {
  olvidador?.(file);
};

/** Solo para tests: olvida quién está registrado. */
export const desregistrarPrecargaFoto = (): void => {
  precargador = null;
  olvidador = null;
};
