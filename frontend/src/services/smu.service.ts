// src/services/smu.service.ts
//
// Conecta los formularios SMU (frontend) con POST /smu/actividades/ y con
// POST /smu/evidencias/ (subida de fotos).
// Cada builder traduce la estructura del formulario a las secciones anidadas
// que espera SmuActividadSerializer y, en consecuencia, crear_actividad_smu().
//
// Nota sobre fotos (Fase 3): el builder entrega cada foto como fila de
// `evidencias[]` con `ruta_archivo` "PENDIENTE_SUBIDA" y, si el formulario
// conservó el `File`, registra un *pendiente de subida*. El submit llama a
// `subirPendientes()` **antes** del POST de la actividad (decisión registrada:
// el binario se sube al guardar), pega la ruta que devuelve `POST
// /smu/evidencias/` y solo entonces envía el payload.
//
// Precarga (Fase 3 · A1b): como los formularios llevan muchas fotos, cada foto
// se sube en cuanto el usuario la elige (FotoSlotCard → `preCargarFotoSMU`).
// `subirPendientes()` primero consulta esa caché: en el caso normal solo
// *espera* rutas que ya llegaron y el envío deja de tardar; si una precarga
// falló o no hubo, sube la foto en ese momento (mismo flujo de siempre).
import {
  CLAVES_ACCIONES_AA,
  ORIGEN_MATERIAL_OPERARIO,
} from "@/modules/smu/constants";
import { registrarPrecargaFoto } from "@/lib/precargaFoto";
import type { Empleado } from "@/types/empleado";
import type { PreventivoAAFormData } from "@/modules/smu/components/preventivos/FormPreventivoAASlider";
import type {
  ChecklistPlantaItemConfig,
  FormPreventivoPlantaData,
} from "@/modules/smu/components/preventivos/FormPreventivoPlantaSlider";
import type { FormCorrectivoEmergenciaData } from "@/modules/smu/components/correctivos/FormCorrectivoEmergenciaSlider";
import type { FormCapexTipologia1Data } from "@/modules/smu/components/capex/tipologia1/types";
import type { FormCapexTipologia3Data } from "@/modules/smu/components/capex/tipologia3/types";
import type { FormCapexTipologia5Data } from "@/modules/smu/components/capex/tipologia5/types";

export const SMU_ACTIVIDADES_ENDPOINT = "/smu/actividades/";
export const SMU_EVIDENCIAS_ENDPOINT = "/smu/evidencias/";

export type SmuPayload = Record<string, unknown>;

type Dict = Record<string, unknown>;

// ─── Helpers de normalización ────────────────────────────────────────────────

/** Recorta; devuelve `undefined` cuando queda vacío (el campo no se envía). */
const txt = (v?: string | null, max?: number): string | undefined => {
  if (v === undefined || v === null) return undefined;
  const s = String(v).trim();
  if (!s) return undefined;
  return max ? s.slice(0, max) : s;
};

/**
 * Igual que `txt` pero además alinea las opciones del formulario con los
 * `choices` del modelo: 'SÍ' → 'SI' y 'N/A' → 'NA'.
 * Ojo: NO usar en campos cuyo choice conserva la tilde (ej. filtración 'SÍ').
 */
const opcion = (v?: string | null, max?: number): string | undefined => {
  const s = txt(v, max);
  if (!s) return undefined;
  if (s === "SÍ") return "SI";
  if (s === "N/A") return "NA";
  return s;
};

/**
 * Convierte un valor digitado a número.
 * Acepta coma decimal ("12,5") y separador de miles español ("1.800" → 1800).
 */
const num = (v?: string | null): number | undefined => {
  if (v === undefined || v === null) return undefined;
  let s = String(v).trim().replace(/\s/g, "");
  if (!s) return undefined;

  if (/^-?\d{1,3}(\.\d{3})+$/.test(s)) {
    s = s.replace(/\./g, "");
  } else {
    s = s.replace(/,/g, ".");
  }

  if (!/^-?\d+(\.\d+)?$/.test(s)) return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
};

/** Entero positivo (campos `PositiveIntegerField`/`PositiveSmallIntegerField`). */
const entero = (v?: string | null): number | undefined => {
  const n = num(v);
  if (n === undefined) return undefined;
  return Math.max(0, Math.round(n));
};

// ─── Fechas ──────────────────────────────────────────────────────────────────
//
// DRF es estricto: `fecha_inicio`/`fecha_fin` son `DateTimeField` y
// `firmas_cierre[].fecha`, `fecha_elaboracion_informe` y `matricula_fecha` son
// `DateField`. Un valor que no sea ISO (`""`, `01/10/2026`, el `toString()` de
// un `Date`…) tumba **todo** el guardado con
// «Fecha/hora con formato erróneo». Estos helpers convierten lo que produzcan
// los inputs del navegador y descartan lo que no se pueda interpretar, para
// que nunca se envíe una fecha inválida.

const ISO_HORA =
  /^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:?\d{2})?)?$/;
const ISO_DIA = /^\d{4}-\d{2}-\d{2}$/;
const LOCAL = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$/;

// Rango de años creíble: una digitación como "12/12/1212" producía
// `1212-12-12…`, que el backend aceptaba y la tabla no podía formatear
// (columna "INICIO" en "-"). Fuera de este rango, la fecha se considera basura.
const ANIO_MINIMO = 1900;
const ANIO_MAXIMO = 2100;

const anioPlausible = (anio: number): boolean =>
  anio >= ANIO_MINIMO && anio <= ANIO_MAXIMO;

const rellena = (n: number): string => String(n).padStart(2, "0");

/** Fecha en hora local (lo que el usuario digitó) a objeto `Date`. */
const aFecha = (v: unknown): Date | null => {
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v;
  if (typeof v === "number") {
    return Number.isFinite(v) ? new Date(v) : null;
  }
  const s = String(v).trim();
  if (!s) return null;

  const local = LOCAL.exec(s);
  if (local) {
    const [, dia, mes, anio, hora, minuto, segundo] = local;
    const d = new Date(
      Number(anio),
      Number(mes) - 1,
      Number(dia),
      Number(hora ?? 0),
      Number(minuto ?? 0),
      Number(segundo ?? 0),
    );
    // 32/13/2026 "se resuelve" rodando al año siguiente: mejor descartarlo.
    const real =
      d.getFullYear() === Number(anio) &&
      d.getMonth() === Number(mes) - 1 &&
      d.getDate() === Number(dia);
    // 12/12/1212 "se resuelve" perfectamente: hay que mirar el año a mano.
    return real && anioPlausible(Number(anio)) ? d : null;
  }

  // `Date.parse` es muy permisivo (con "ayer a las 8" devuelve una fecha
  // inventada), así que solo se confía en él si el texto trae un año de 4
  // dígitos: ISO con zona o el `toString()` clásico de `Date`.
  const posibleAnio = /\d{4}/.exec(s)?.[0];
  if (!posibleAnio || !anioPlausible(Number(posibleAnio))) return null;
  const marca = Date.parse(s);
  return Number.isNaN(marca) ? null : new Date(marca);
};

/** El `YYYY-MM-DD[Thh:mm]` inicial corresponde a una fecha/hora reales. */
const esFechaISOValida = (s: string): boolean => {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/.exec(
    s,
  );
  if (!m) return false;
  const [, anio, mes, dia, hora, minuto, segundo] = m;
  if (!anioPlausible(Number(anio))) return false;
  const d = new Date(Number(anio), Number(mes) - 1, Number(dia));
  if (
    d.getFullYear() !== Number(anio) ||
    d.getMonth() !== Number(mes) - 1 ||
    d.getDate() !== Number(dia)
  ) {
    return false;
  }
  if (hora !== undefined && Number(hora) > 23) return false;
  if (minuto !== undefined && Number(minuto) > 59) return false;
  if (segundo !== undefined && Number(segundo) > 60) return false;
  return true;
};

const aISO = (d: Date, conHora: boolean): string => {
  const dia = `${d.getFullYear()}-${rellena(d.getMonth() + 1)}-${rellena(d.getDate())}`;
  if (!conHora) return dia;
  return `${dia}T${rellena(d.getHours())}:${rellena(d.getMinutes())}:${rellena(d.getSeconds())}`;
};

/**
 * Valor aceptado por un `DateTimeField` de DRF (`YYYY-MM-DDThh:mm[:ss]`).
 * `undefined` si está vacío o es ilegible (el campo simplemente no viaja).
 */
const fechaHora = (v?: string | number | Date | null): string | undefined => {
  if (v === undefined || v === null) return undefined;
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? undefined : aISO(v, true);

  const s = String(v).trim();
  if (!s) return undefined;
  if (ISO_HORA.test(s) && esFechaISOValida(s)) return s.replace(" ", "T");

  const d = aFecha(s);
  return d ? aISO(d, true) : undefined;
};

/** Valor aceptado por un `DateField` de DRF (`YYYY-MM-DD`). */
const fechaDia = (v?: string | number | Date | null): string | undefined => {
  if (v === undefined || v === null) return undefined;
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? undefined : aISO(v, false);

  const s = String(v).trim();
  if (!s) return undefined;
  if (ISO_DIA.test(s) && esFechaISOValida(s)) return s;

  const d = aFecha(s);
  return d ? aISO(d, false) : undefined;
};

/**
 * Valida las fechas del encabezado **antes** de enviar, para `toast.error` +
 * `return` en cada `handleSubmit`. Devuelve el mensaje o `null` si están bien.
 *
 * - `fecha_inicio` es obligatoria: sin ella el registro queda con `null` y la
 *   columna "INICIO" del historial muestra "-" (decisión: bloquear, no
 *   guardar a medias).
 * - `fecha_fin` es opcional, pero si viene no puede ser ilegible (p. ej.
 *   "12/12/1212") ni anterior al inicio (el backend también lo rechaza, pero
 *   con un mensaje genérico).
 */
export const validarFechasEncabezado = (
  fechaInicio?: string | null,
  fechaFin?: string | null,
): string | null => {
  const inicio = (fechaInicio ?? "").trim();
  const fin = (fechaFin ?? "").trim();

  if (!inicio) {
    return "La Fecha de Inicio es obligatoria: selecciona la fecha y hora del inicio de la actividad.";
  }
  if (!fechaHora(inicio)) {
    return `La Fecha de Inicio no es válida (debe estar entre ${ANIO_MINIMO} y ${ANIO_MAXIMO}): usa el selector de fecha y hora.`;
  }
  if (fin && !fechaHora(fin)) {
    return `La Fecha de Fin no es válida (debe estar entre ${ANIO_MINIMO} y ${ANIO_MAXIMO}): usa el selector de fecha y hora.`;
  }
  if (fin) {
    const dInicio = aFecha(inicio);
    const dFin = aFecha(fin);
    if (dInicio && dFin && dFin.getTime() < dInicio.getTime()) {
      return "La Fecha de Fin no puede ser anterior a la Fecha de Inicio.";
    }
  }
  return null;
};

/** Elimina vacíos/undefined/null y colecciones vacías de un objeto plano. */
const limpio = (obj: Dict): Dict =>
  Object.fromEntries(
    Object.entries(obj).filter(([, v]) => {
      if (v === undefined || v === null) return false;
      if (typeof v === "string" && !v.trim()) return false;
      if (Array.isArray(v) && v.length === 0) return false;
      if (typeof v === "object" && Object.keys(v as Dict).length === 0)
        return false;
      return true;
    }),
  );

const soloOrden = (obj: Dict): boolean => Object.keys(obj).length <= 1;

const nombreCompleto = (e: Empleado): string =>
  `${e.nombre ?? ""} ${e.apellido ?? ""}`.trim();

/** Filtra los `undefined` que devuelven builders opcionales. */
const definidos = <T>(items: Array<T | undefined>): T[] =>
  items.filter((item): item is T => item !== undefined);

// ─── Builders de secciones anidadas ──────────────────────────────────────────

const tecnicos = (principal: Empleado | null, apoyo: Empleado | null): Dict[] =>
  definidos([
    principal?.cedula
      ? {
          cedula: txt(principal.cedula, 30),
          nombre: txt(nombreCompleto(principal), 150),
          es_principal: true,
        }
      : undefined,
    apoyo?.cedula
      ? {
          cedula: txt(apoyo.cedula, 30),
          nombre: txt(nombreCompleto(apoyo), 150),
          es_principal: false,
        }
      : undefined,
  ]);

interface EspecificacionFirma {
  rol: string;
  nombre?: string;
  cedula?: string;
  cargo?: string;
  fecha?: string;
  ruta_firma?: string;
}

const firmas = (items: EspecificacionFirma[]): Dict[] =>
  definidos(
    items.map((item, index) => {
      const nombre = txt(item.nombre, 150);
      if (!nombre) return undefined;
      return {
        rol: txt(item.rol, 30),
        nombre,
        cedula: txt(item.cedula, 30),
        cargo: txt(item.cargo, 120),
        // DateField: 'YYYY-MM-DD'
        fecha: fechaDia(item.fecha),
        ruta_firma: txt(item.ruta_firma, 350),
        orden: index + 1,
      };
    }),
  );

interface EspecificacionCertificado {
  tipo?: string;
  categoria?: string;
  ruta_certificado?: string;
  ruta_foto_sitio?: string;
  /** Fase 3: binario conservado por el formulario (si lo hay). */
  file_certificado?: File | null;
  file_sitio?: File | null;
}

const certificados = (
  items: EspecificacionCertificado[],
  pendientes?: PendienteSubida[],
): Dict[] =>
  definidos(
    items.map((item, index) => {
      const tipo = txt(item.tipo, 120);
      const categoria = txt(item.categoria, 120);
      const rutaCertificado = txt(item.ruta_certificado, 350);
      const rutaFotoSitio = txt(item.ruta_foto_sitio, 350);
      if (!tipo && !categoria && !rutaCertificado && !rutaFotoSitio)
        return undefined;
      const fila: Dict = {
        tipo,
        categoria,
        ruta_certificado: rutaCertificado,
        ruta_foto_sitio: rutaFotoSitio,
        orden: index + 1,
      };
      pendiente(
        pendientes,
        item.file_certificado,
        "certificados",
        `certificado_${index + 1}_foto_certificado`,
        (ruta) => {
          fila.ruta_certificado = ruta;
        },
      );
      pendiente(
        pendientes,
        item.file_sitio,
        "certificados",
        `certificado_${index + 1}_foto_sitio`,
        (ruta) => {
          fila.ruta_foto_sitio = ruta;
        },
      );
      return fila;
    }),
  );

/**
 * Metadatos de una foto. Solo acepta rutas persistidas reales del servidor
 * (URLs http/https o rutas que apunten a directorios de medios del backend).
 * Cualquier URL efímera (blob:, data:), identificador local o valor no persistido
 * se normaliza positivamente a "PENDIENTE_SUBIDA".
 */
const sanitizeRuta = (ruta?: string): string => {
  if (!ruta) return "PENDIENTE_SUBIDA";
  const s = ruta.trim();
  if (/^(https?:\/\/|\/?media\/|\/?media-fotos\/)/i.test(s)) {
    return txt(s, 350) ?? "PENDIENTE_SUBIDA";
  }
  return "PENDIENTE_SUBIDA";
};

const evidencia = (
  seccion: string,
  campo_origen: string,
  ruta?: string,
  extra: { nombre_original?: string; descripcion?: string } = {},
): Dict => ({
  seccion: txt(seccion, 60) ?? "general",
  campo_origen: txt(campo_origen, 80) ?? "campo",
  ruta_archivo: sanitizeRuta(ruta),
  nombre_original: txt(extra.nombre_original, 255),
  descripcion: txt(extra.descripcion),
});

/**
 * Numeración explícita para colecciones con `ordering` por `orden`.
 *
 * Devuelve los **mismos** objetos (no copias): los pendientes de subida de
 * fotos apuntan a estas filas y tienen que poder escribir la ruta real
 * (`aplicar`) *después* de que el builder ya armo el payload.
 */
const conOrden = (items: Dict[]): Dict[] =>
  items.map((item, index) => {
    item.orden = index + 1;
    return item;
  });

// ─── Subida de fotos (Fase 3 · A1) ───────────────────────────────────────────

/**
 * Foto elegida en el formulario que todavía no está en el servidor.
 * `aplicar` pega la ruta devuelta por el backend en la fila exacta del payload.
 */
export interface PendienteSubida {
  file: File;
  seccion: string;
  campo_origen: string;
  aplicar: (ruta: string) => void;
}

/** Falla de la subida de fotos; la muestran los submits con `manejarErrorGuardado`. */
export class ErrorSubidaFotos extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ErrorSubidaFotos";
  }
}

type RespuestaSubida = { ruta_archivo: string; url?: string };

type MetaSubida = {
  seccion: string;
  campo_origen: string;
  actividad_id?: number;
};

type Subidor = (file: File, meta: MetaSubida) => Promise<RespuestaSubida>;

/**
 * Fotografía hasta 5 MB (valida el backend); margen amplio para enlaces lentos.
 * A4 subió además el timeout normal de las peticiones a 30 s.
 */
const TIMEOUT_SUBIDA_MS = 120000;

/**
 * `POST /smu/evidencias/` (multipart). Devuelve `ruta_archivo`, la ruta que
 * viaja dentro de `evidencias[].ruta_archivo` al crear la actividad.
 */
export const subirEvidenciaSMU: Subidor = async (file, meta) => {
  const form = new FormData();
  form.append("archivo", file, file.name);
  form.append("seccion", meta.seccion);
  form.append("campo_origen", meta.campo_origen);
  if (meta.actividad_id !== undefined) {
    form.append("actividad_id", String(meta.actividad_id));
  }
  // Import dinámico a propósito: los tests unitarios cargan este módulo para
  // ejercitar los builders y no deben arrastrar axios ni errorHandler (que usa
  // `enum`, ilegible para el strip-only de Node).
  const { default: api } = await import("@/lib/api");
  // Con body FormData, axios deja que el navegador escriba el Content-Type con
  // su boundary; aquí solo alargamos el timeout (10 s no alcanzaba para fotos).
  const { data } = await api.post<RespuestaSubida>(SMU_EVIDENCIAS_ENDPOINT, form, {
    timeout: TIMEOUT_SUBIDA_MS,
  });
  return data;
};

// ─── Precarga al elegir la foto ──────────────────────────────────────────────

/**
 * `File` ya elegido → promesa de su `ruta_archivo`. La clave es la identidad
 * del `File`: elegir otra foto crea un objeto nuevo (otra clave) y re-elegir
 * la misma no vuelve a subir nada.
 */
const precargas = new Map<File, Promise<string>>();

/** Colchón de evicción por orden de inserción (sesiones con muchas re-elecciones). */
const TOPE_PRECARGAS = 60;

/** `seccion` de la carpeta donde quedan las fotos precargadas (`borrador/…`); es
 *  solo cosmética: la fila `evidencia` real toma su `seccion` del builder. */
const SECCION_PRECARGA = "precarga";

/**
 * Sube `file` en cuanto el usuario la elige y devuelve su `ruta_archivo`.
 *
 * - dos llamadas con el mismo `File` comparten la misma subida;
 * - un fallo **no** queda cacheado: se elimina para que el guardado reintente
 *   con el `seccion`/`campo_origen` reales del pendiente.
 *
 * `subir` es inyectable solo para tests.
 */
export const preCargarFotoSMU = (
  file: File,
  subir: Subidor = subirEvidenciaSMU,
): Promise<string> => {
  const existente = precargas.get(file);
  if (existente) return existente;

  const promesa = subir(file, {
    seccion: SECCION_PRECARGA,
    campo_origen: SECCION_PRECARGA,
  })
    .then((respuesta) => respuesta.ruta_archivo)
    .catch((err) => {
      precargas.delete(file);
      throw err;
    });

  precargas.set(file, promesa);
  if (precargas.size > TOPE_PRECARGAS) {
    const masAntigua = precargas.keys().next().value;
    if (masAntigua !== undefined) precargas.delete(masAntigua);
  }
  return promesa;
};

/** El usuario quitó o reemplazó la foto: su precarga deja de interesar. */
export const olvidarPrecargaSMU = (file: File): void => {
  precargas.delete(file);
};

/** Solo para tests: vacía la caché de precargas. */
export const limpiarPrecargasSMU = (): void => {
  precargas.clear();
};

const mensajeDeError = (err: unknown): string => {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === "object" && err !== null) {
    const detalle = err as { message?: unknown; detail?: unknown };
    if (typeof detalle.message === "string" && detalle.message) {
      return detalle.message;
    }
    if (typeof detalle.detail === "string" && detalle.detail) {
      return detalle.detail;
    }
  }
  return "error desconocido";
};

/**
 * Escribe la ruta real en cada fila del payload.
 *
 * Si la foto ya se subió al elegirla (precarga), aquí solo **se espera** su
 * promesa — normalmente resuelta, así que el envío es inmediato. Si la precarga
 * falló o no hubo, sube la foto ahora, con el `seccion`/`campo_origen` reales
 * del pendiente.
 *
 * Se sube **en orden** (memoria plana y sin pisar el throttle del backend).
 * Lanza `ErrorSubidaFotos` al primer fallo: mejor abortar el guardado que
 * crear una actividad con las fotos perdidas.
 */
export const subirPendientes = async (
  pendientes: PendienteSubida[],
  subir: Subidor = subirEvidenciaSMU,
): Promise<void> => {
  for (const pendiente_ of pendientes) {
    try {
      let ruta: string | undefined;
      const precargada = precargas.get(pendiente_.file);
      if (precargada) {
        try {
          ruta = await precargada;
        } catch {
          ruta = undefined; // falló la precarga: se sube ahora
        }
      }
      if (!ruta) {
        const respuesta = await subir(pendiente_.file, {
          seccion: pendiente_.seccion,
          campo_origen: pendiente_.campo_origen,
        });
        ruta = respuesta.ruta_archivo;
      }
      pendiente_.aplicar(ruta);
    } catch (err) {
      throw new ErrorSubidaFotos(
        `No se pudo subir la foto "${pendiente_.file.name}" ` +
          `(${pendiente_.seccion}/${pendiente_.campo_origen}): ` +
          mensajeDeError(err),
      );
    }
  }
};

// Registro al cargar el módulo: los formularios SMU importan este servicio,
// así que cuando FotoSlotCard pregunta "¿alguien pre-carga?" ya hay respuesta.
registrarPrecargaFoto(preCargarFotoSMU, olvidarPrecargaSMU);

/** Registra una foto (si el formulario conservó el `File`) para subirla. */
const pendiente = (
  colector: PendienteSubida[] | undefined,
  file: File | undefined | null,
  seccion: string,
  campo_origen: string,
  aplicar: (ruta: string) => void,
): void => {
  if (!colector || !file) return;
  colector.push({ file, seccion, campo_origen, aplicar });
};

// ─── Preventivo Aire Acondicionado ───────────────────────────────────────────

// 'Si' | 'No' | 'No Aplica' → valores almacenados normalizados
const ESTADOS_CHECKLIST_AA: Record<string, string> = {
  Si: "SI",
  No: "NO",
  "No Aplica": "NA",
};

export const buildPreventivoAAPayload = (
  d: PreventivoAAFormData,
  pendientes?: PendienteSubida[],
): SmuPayload => {
  const evidencias: Dict[] = [];

  Object.entries(d.fotos).forEach(([slot, foto]) => {
    if (!foto?.previewUrl && !foto?.nombre) return;
    const fila = evidencia("anexos_fotograficos", slot, foto.previewUrl, {
      nombre_original: foto.nombre,
      descripcion: d.fotos_descripciones?.[slot],
    });
    evidencias.push(fila);
    pendiente(pendientes, foto.file, "anexos_fotograficos", slot, (ruta) => {
      fila.ruta_archivo = ruta;
    });
  });

  const acciones = d.acciones_mantenimiento
    .flatMap((fila, filaIndex) =>
      CLAVES_ACCIONES_AA.map((clave): Dict | undefined => {
        const valor = opcion(String(fila[clave] ?? ""));
        if (!valor) return undefined;
        return { clave, valor, orden: filaIndex + 1 };
      }),
    )
    .filter((accion) => accion !== undefined);

  const detalle = limpio({
    marca: txt(d.marca, 100),
    modelo: txt(d.modelo, 100),
    serial: txt(d.serial, 100),
    id_activo: txt(d.id_activo, 80),
    tipo_aire: txt(d.tipo_aire, 80),
    alimentacion_ac: txt(d.alimentacion_ac, 50),
    voltaje_entrada: num(d.voltaje_entrada),
    corriente: num(d.corriente),
    capacidad_btu: entero(d.capacidad_btu),
    gestion_remota_ip: txt(d.gestion_remota_ip, 60),
    cantidad_compresores: entero(d.cantidad_compresores),
    temp_cuarto: num(d.temp_cuarto),
    temp_entrada: num(d.temp_entrada),
    temp_salida: num(d.temp_salida),
    temp_display: num(d.temp_display),
    ajuste_termostato: txt(d.ajuste_termostato, 100),
    // El formulario sólo expone la temperatura post-ajuste.
    mp_termostato_post: txt(d.temp_termostato_pos_ajuste, 100),
    acciones_observaciones: txt(d.acciones_observaciones),
    plan_mejora: txt(d.plan_mejora),
  });

  return limpio({
    categoria: "preventivos",
    tipo_formulario: "aire_acondicionado",
    nombre_estacion: txt(d.nombre_estacion, 150),
    departamento: txt(d.departamento, 80),
    direccion: txt(d.direccion, 255),
    tipo_estacion: txt(d.tipo_estacion, 80),
    site_owner: txt(d.site_owner, 100),
    codigo_ot: txt(d.codigo_ot, 60),
    fecha_inicio: fechaHora(d.fecha_inicio),
    fecha_fin: fechaHora(d.fecha_fin),
    responsable_cedula: txt(d.responsable_1?.cedula, 30),
    responsable_nombre: d.responsable_1
      ? txt(nombreCompleto(d.responsable_1), 150)
      : txt(d.tecnico_nombre, 150),
    empresa: txt(d.empresa, 150),

    tecnicos: tecnicos(d.responsable_1, d.responsable_2),
    evidencias: conOrden(evidencias),
    firmas_cierre: firmas([
      { rol: "tecnico", nombre: d.tecnico_nombre, ruta_firma: d.tecnico_firma },
      { rol: "revisor", nombre: d.reviso_nombre, ruta_firma: d.reviso_firma },
    ]),
    certificados: certificados(
      [
        {
          tipo: d.certificado.tipo_certificado,
          categoria: d.certificado.categoria_certificado,
          // Antes iba el marcador literal "foto_certificado"; ahora la ruta
          // real (o PENDIENTE_SUBIDA si aún es un blob:), que la subida pega.
          ruta_certificado: d.certificado.foto_certificado_preview
            ? sanitizeRuta(d.certificado.foto_certificado_preview)
            : undefined,
          ruta_foto_sitio: d.certificado.foto_sitio_preview
            ? sanitizeRuta(d.certificado.foto_sitio_preview)
            : undefined,
          file_certificado: d.certificado.foto_certificado_file,
          file_sitio: d.certificado.foto_sitio_file,
        },
      ],
      pendientes,
    ),

    detalle_preventivo_aa: detalle,
    checklist_aa: definidos(
      Object.entries(d.checklist).map(([numero, estado]): Dict | undefined => {
        const item_numero = Number(numero);
        if (!Number.isInteger(item_numero)) return undefined;
        return {
          item_numero,
          estado: ESTADOS_CHECKLIST_AA[estado] ?? estado,
        };
      }),
    ),
    aa_compresores: d.compresores
      .map((c, index) =>
        limpio({
          orden: index + 1,
          marca: txt(c.marca, 100),
          serial: txt(c.serial, 100),
          tipo: txt(c.tipo, 80),
          refrigerante: txt(c.refrigerante, 50),
          modelo: txt(c.modelo, 100),
          aislamiento_electrico: txt(c.aislamiento_electrico, 50),
          presion_succion: num(c.presion_succion),
          presion_descarga: num(c.presion_descarga),
          nivel_aceite: txt(c.nivel_aceite, 50),
          vl1: num(c.vl1),
          vl2: num(c.vl2),
          vl3: num(c.vl3),
          amp_l1: num(c.ampl1),
          amp_l2: num(c.ampl2),
          amp_l3: num(c.ampl3),
        }),
      )
      .filter((c) => !soloOrden(c)),
    aa_condensadoras: d.condensadoras
      .map((c, index) =>
        limpio({
          orden: index + 1,
          marca: txt(c.marca, 100),
          modelo: txt(c.modelo, 100),
          serial: txt(c.serial, 100),
          temperatura_entrada: num(c.temperatura_entrada),
          temperatura_salida: num(c.temperatura_salida),
          diametro_eje: txt(c.diametro_eje, 50),
          diametro_aspas: txt(c.diametro_aspas, 50),
        }),
      )
      .filter((c) => !soloOrden(c)),
    aa_manejadoras: d.manejadoras
      .map((m, index) =>
        limpio({
          orden: index + 1,
          marca: txt(m.marca, 100),
          modelo: txt(m.modelo, 100),
          tipo: txt(m.tipo, 80),
          tipo_filtro: txt(m.tipo_filtro, 80),
          tipo_correa: txt(m.tipo_correa, 80),
          marca_motor: txt(m.marca_motor, 100),
          alimentacion_ac: txt(m.alimentacion_ac, 50),
          voltaje: num(m.voltaje_motor),
          corriente: num(m.corriente_motor),
          aislamiento: num(m.aislamiento),
          serial_motor: txt(m.serial_motor, 100),
          dimensiones_blower: txt(m.dimensiones_blower, 80),
        }),
      )
      .filter((m) => !soloOrden(m)),
    aa_acciones: acciones,
  });
};

// ─── Preventivo Planta Eléctrica ─────────────────────────────────────────────

/**
 * @param checklistItems Catálogo de los 105 ítems (se inyecta desde el
 * componente para evitar una importación circular con el formulario).
 */
export const buildPreventivoPlantaPayload = (
  d: FormPreventivoPlantaData,
  checklistItems: ChecklistPlantaItemConfig[],
  pendientes?: PendienteSubida[],
): SmuPayload => {
  const pruebas = d.pruebas_filtracion;
  const evidencias: Dict[] = [];

  Object.entries(d.fotos).forEach(([slot, foto]) => {
    if (!foto?.previewUrl && !foto?.nombre) return;
    const fila = evidencia("anexos_planta", slot, foto.previewUrl, {
      nombre_original: foto.nombre,
      descripcion: d.fotos_descripciones?.[slot],
    });
    evidencias.push(fila);
    pendiente(pendientes, foto.file, "anexos_planta", slot, (ruta) => {
      fila.ruta_archivo = ruta;
    });
  });

  const hallazgos = d.hallazgos.filter((h) => txt(h.descripcion));

  hallazgos.forEach((hallazgo, index) => {
    (["evidencia_1", "evidencia_2", "evidencia_3"] as const).forEach(
      (campo) => {
        const previewUrl = hallazgo[campo];
        if (!previewUrl) return;
        const fileObj = hallazgo[`${campo}_file` as const];
        const campoOrigen = `hallazgo_${index + 1}_${campo}`;
        const fila = evidencia("hallazgos_planta", campoOrigen, previewUrl, {
          nombre_original: fileObj?.name,
          // El título de la caja: lo que escribieron para esta foto y, si no,
          // la descripción del hallazgo (que comparten sus 3 evidencias).
          descripcion:
            hallazgo[`${campo}_descripcion` as const] || hallazgo.descripcion,
        });
        evidencias.push(fila);
        pendiente(
          pendientes,
          fileObj,
          "hallazgos_planta",
          campoOrigen,
          (ruta) => {
            fila.ruta_archivo = ruta;
          },
        );
      },
    );
  });

  const detalle = limpio({
    jefatura: txt(d.jefatura, 80),
    zona_om: txt(d.zona_om, 80),
    modalidad: txt(d.modalidad, 80),
    cantidad_plantas: entero(d.cantidad_plantas),
    estructura: txt(d.estructura, 120),
    orden_trabajo_tas: txt(d.orden_trabajo_tas, 60),
    plan_mejora_estado: txt(d.plan_mejora_estado),
    fecha_elaboracion_informe: fechaDia(d.fecha_elaboracion_informe),

    // 4. Resultado de pruebas (choices 'OK' | 'NO OK' | 'N/A')
    prueba_vacio: txt(pruebas.prueba_vacio, 20),
    prueba_con_carga: txt(pruebas.prueba_con_carga, 20),
    prueba_transferencia_automatica: txt(
      pruebas.prueba_transferencia_automatica,
      20,
    ),
    prueba_planta_forzada: txt(pruebas.prueba_planta_forzada, 20),
    observaciones_pruebas: txt(pruebas.observaciones_pruebas),

    // 5. Servicio de filtración (choices 'SÍ' | 'NO' | 'N/A' → se conservan)
    cambio_aceite: txt(pruebas.cambio_aceite, 20),
    cambio_filtros_aire: txt(pruebas.cambio_filtros_aire, 20),
    cambio_filtros_combustible: txt(pruebas.cambio_filtros_combustible, 20),
    cambio_filtros_aceite: txt(pruebas.cambio_filtros_aceite, 20),
    cambio_mangueras_precalentador: txt(
      pruebas.cambio_mangueras_precalentador,
      20,
    ),
    cambio_refrigerante: txt(pruebas.cambio_refrigerante, 20),
    cambio_baterias: txt(pruebas.cambio_baterias, 20),
    observaciones_filtracion: txt(pruebas.observaciones_filtracion),
  });

  return limpio({
    categoria: "preventivos",
    tipo_formulario: "planta",
    nombre_estacion: txt(d.nombre_estacion, 150),
    direccion: txt(d.direccion, 255),
    site_owner: txt(d.site_owner, 100),
    regional: txt(d.region, 80),
    fecha_inicio: fechaHora(d.fecha_inicio),
    fecha_fin: fechaHora(d.fecha_fin),
    responsable_cedula: txt(d.responsable_1?.cedula, 30),
    responsable_nombre: d.responsable_1
      ? txt(nombreCompleto(d.responsable_1), 150)
      : txt(d.tecnico_nombre, 150),
    coordinador_aliado: txt(d.coordinador_aliado, 150),
    empresa: txt(d.empresa, 150),

    tecnicos: tecnicos(d.responsable_1, d.responsable_2),
    evidencias: conOrden(evidencias),
    firmas_cierre: firmas([
      { rol: "tecnico", nombre: d.tecnico_nombre, ruta_firma: d.tecnico_firma },
      { rol: "revisor", nombre: d.reviso_nombre, ruta_firma: d.reviso_firma },
    ]),
    certificados: certificados(
      [
        {
          tipo: d.certificado_tipo,
          categoria: d.certificado_categoria,
          ruta_certificado: d.foto_certificado_preview
            ? sanitizeRuta(d.foto_certificado_preview)
            : undefined,
          ruta_foto_sitio: d.foto_sitio_preview
            ? sanitizeRuta(d.foto_sitio_preview)
            : undefined,
          file_certificado: d.foto_certificado_file,
          file_sitio: d.foto_sitio_file,
        },
      ],
      pendientes,
    ),

    detalle_preventivo_planta: detalle,
    checklist_planta: definidos(
      checklistItems.map((item) => {
        const estado = d.checklist[item.id];
        if (!estado) return undefined;
        const fila = limpio({
          sistema: txt(item.sistema, 50),
          componente: txt(item.componente, 255),
          estado: txt(estado.estado, 50),
          causa: txt(estado.causa),
          detectar: txt(estado.detectar),
          corregir: txt(estado.corregir),
        });
        // Sin sistema/componente no se puede respetar la unique constraint.
        return fila.sistema && fila.componente ? fila : undefined;
      }),
    ),
    plantas: d.plantas.map((p, index) =>
      limpio({
        orden: index + 1,
        nombre_unidad: txt(p.nombre_unidad, 120),
        equipo_marca: txt(p.equipo_marca, 100),
        equipo_modelo: txt(p.equipo_modelo, 100),
        equipo_serial: txt(p.equipo_serial, 100),
        equipo_velocidad_motor: txt(p.equipo_velocidad_motor, 80),
        equipo_admision_aire: txt(p.equipo_admision_aire, 80),
        equipo_rpm: entero(p.equipo_rpm),
        equipo_horas_trabajo: num(p.equipo_horas_trabajo),
        equipo_frecuencia_hz: num(p.equipo_frecuencia_hz),
        equipo_capacidad_kva: num(p.equipo_capacidad_kva),
        equipo_capacidad_kw: num(p.equipo_capacidad_kw),
        equipo_derrateo: txt(p.equipo_derrateo, 80),
        equipo_capacidad_derrateo: txt(p.equipo_capacidad_derrateo, 80),
        motor_marca: txt(p.motor_marca, 100),
        motor_modelo: txt(p.motor_modelo, 100),
        motor_serial: txt(p.motor_serial, 100),
        motor_presion_aceite: num(p.motor_presion_aceite),
        motor_temp_aceite: num(p.motor_temp_aceite),
        motor_temp_refrigerante: num(p.motor_temp_refrigerante),
        generador_marca: txt(p.generador_marca, 100),
        generador_modelo: txt(p.generador_modelo, 100),
        generador_serial: txt(p.generador_serial, 100),
        generador_temp_ambiente: num(p.generador_temp_ambiente),
        bateria_voltaje: num(p.bateria_voltaje),
        bateria_capacidad: txt(p.bateria_capacidad, 50),
        bateria_tipo: txt(p.bateria_tipo, 80),
        bateria_cantidad: entero(p.bateria_cantidad),
        bateria_estado: txt(p.bateria_estado, 50),
        bateria_estado_cargador: txt(p.bateria_estado_cargador, 50),
        param_vac_l1_l2: num(p.param_vac_l1_l2),
        param_vac_l1_l3: num(p.param_vac_l1_l3),
        param_vac_l2_l3: num(p.param_vac_l2_l3),
        param_amp_l1: num(p.param_amp_l1),
        param_amp_l2: num(p.param_amp_l2),
        param_amp_l3: num(p.param_amp_l3),
        dimensionamiento_capacidad_amp: num(p.dimensionamiento_capacidad_amp),
        dimensionamiento_carga_demanda: num(p.dimensionamiento_carga_demanda),
        dimensionamiento_porc_carga: num(p.dimensionamiento_porc_carga),
      }),
    ),
    hallazgos_planta: hallazgos.map((h, index) => ({
      orden: index + 1,
      descripcion: txt(h.descripcion),
    })),
  });
};

// ─── Correctivo / Emergencia (formulario estándar) ───────────────────────────

export const buildCorrectivoEmergenciaPayload = (
  d: FormCorrectivoEmergenciaData,
  categoria: "correctivos" | "emergencias",
  pendientes?: PendienteSubida[],
): SmuPayload => {
  const evidencias = d.evidencias
    .filter((e) => e.previewUrl || e.nombre || txt(e.descripcion))
    .map((e) => {
      const fila = evidencia("evidencias", e.id, e.previewUrl, {
        nombre_original: e.nombre || e.file?.name,
        descripcion: e.descripcion,
      });
      pendiente(pendientes, e.file, "evidencias", e.id, (ruta) => {
        fila.ruta_archivo = ruta;
      });
      return fila;
    });

  // Filrado único de materiales: lo comparten el payload y la numeración de
  // las fotos, para que `material_<n>_foto_*` coincida con el
  // `enumerate(materiales, start=1)` del exporte (una fila sin descripción
  // se cae del payload y no debe numerar).
  const materiales = d.materiales.filter((m) => txt(m.descripcion));

  // Fotos de cada material → columnas FOTO ANTES y FOTO DESPUÉS de su fila en
  // el bloque 4 del Excel. Sin foto no se emite fila: el exporte tolera filas
  // de material sin foto, pero no fotos huérfanas.
  const fotosMateriales: Dict[] = [];
  materiales.forEach((m, index) => {
    const fotos = [
      ["antes", m.foto_antes_preview, m.foto_antes_file],
      ["despues", m.foto_despues_preview, m.foto_despues_file],
    ] as const;
    fotos.forEach(([parte, preview, file]) => {
      if (!preview && !file) return;
      const campo_origen = `material_${index + 1}_foto_${parte}`;
      const fila = evidencia("materiales", campo_origen, preview, {
        nombre_original: file?.name,
      });
      pendiente(pendientes, file, "materiales", campo_origen, (ruta) => {
        fila.ruta_archivo = ruta;
      });
      fotosMateriales.push(fila);
    });
  });

  const transporte = limpio({
    tipo_transporte: txt(d.tipo_transporte, 80),
    distancia_km: num(d.distancia_km),
    tiempo_traslado: txt(d.tiempo_desplazamiento, 50),
    observacion: txt(d.observacion_transporte),
  });

  const tieneTransporte = Boolean(
    transporte.distancia_km ||
    transporte.tiempo_traslado ||
    transporte.observacion,
  );

  return limpio({
    categoria,
    tipo_formulario: "estandar",
    nombre_estacion: txt(d.nombre_estacion, 150),
    regional: txt(d.regional, 80),
    departamento: txt(d.departamento, 80),
    direccion: txt(d.direccion, 255),
    tipo_estacion: txt(d.tipo_estacion, 80),
    tipo_sitio: txt(d.tipo_sitio, 80),
    site_owner: txt(d.site_owner, 100),
    categoria_criticidad: txt(d.categoria_criticidad, 50),
    fecha_inicio: fechaHora(d.fecha_inicio),
    fecha_fin: fechaHora(d.fecha_fin),
    responsable_cedula: txt(d.responsable_1?.cedula, 30),
    responsable_nombre: d.responsable_1
      ? txt(nombreCompleto(d.responsable_1), 150)
      : undefined,
    empresa: txt(d.empresa_ejecuta, 150),
    numero_inc: txt(d.numero_inc, 60),
    numero_tas: txt(d.numero_tas, 60),
    implica_exclusion: d.implica_exclusion === "SI",
    observaciones: txt(d.observaciones),

    tecnicos: tecnicos(d.responsable_1, d.responsable_2),
    evidencias: conOrden([...evidencias, ...fotosMateriales]),
    transportes: tieneTransporte ? [transporte] : [],
    firmas_cierre: firmas([
      { rol: "tecnico", nombre: d.tecnico_nombre, ruta_firma: d.tecnico_firma },
      { rol: "revisor", nombre: d.revisa_nombre, ruta_firma: d.revisa_firma },
    ]),
    certificados: certificados([
      { tipo: d.certificado_tipo, categoria: d.certificado_categoria },
    ]),

    materiales: materiales.map((m) =>
      limpio({
        tipo_registro:
          categoria === "emergencias"
            ? "material_emergencia"
            : "material_correctivo",
        origen_material: txt(m.origen_material, 120),
        descripcion: txt(m.descripcion),
        cantidad_real: num(m.cantidad),
        unidad_medida: txt(m.tipo_unidad, 30),
        comprado_operario: m.origen_material === ORIGEN_MATERIAL_OPERARIO,
      }),
    ),

    detalle_falla_intervencion: limpio({
      tipo_actividad: txt(d.tipo_actividad, 100),
      tipo_equipo_falla: txt(d.tipo_equipo_falla, 100),
      marca: txt(d.marca, 100),
      modelo: txt(d.modelo, 100),
      afectacion_servicios: txt(d.presenta_afectacion_servicios, 100),
      reinstalacion: txt(d.reinstalacion, 20),
      cambio: txt(d.cambio, 20),
      reparacion: txt(d.reparacion, 20),
      descripcion_falla: txt(d.descripcion_falla),
      descripcion_solucion: txt(d.descripcion_solucion),
      descripcion_fallas_componentes: txt(d.descripcion_fallas_componentes),
      detalles_plano: txt(d.detalles_plano),
      // 'tipo_intervencion' queda como resumen: decisión pendiente (Tarea D).
    }),
  });
};

// ─── CAPEX (compartido entre tipologías) ─────────────────────────────────────

interface CabeceraCapex {
  nombre_estacion: string;
  ot: string;
  fecha_inicio: string;
  fecha_fin: string;
  tipo_estacion: string;
  site_owner: string;
  responsable_ejecuta: Empleado | null;
  empresa: string;
  coordinador_aliado: string;
}

const cabeceraCapex = (
  d: CabeceraCapex,
  tipo_formulario: "tipologia1" | "tipologia3" | "tipologia5",
): Dict => ({
  categoria: "correctivos_capex",
  tipo_formulario,
  nombre_estacion: txt(d.nombre_estacion, 150),
  codigo_ot: txt(d.ot, 60),
  fecha_inicio: fechaHora(d.fecha_inicio),
  fecha_fin: fechaHora(d.fecha_fin),
  tipo_estacion: txt(d.tipo_estacion, 80),
  site_owner: txt(d.site_owner, 100),
  responsable_cedula: txt(d.responsable_ejecuta?.cedula, 30),
  responsable_nombre: d.responsable_ejecuta
    ? txt(nombreCompleto(d.responsable_ejecuta), 150)
    : undefined,
  coordinador_aliado: txt(d.coordinador_aliado, 150),
  empresa: txt(d.empresa, 150),
  tecnicos: tecnicos(d.responsable_ejecuta, null),
});

interface InsumoCapex {
  id: string;
  texto_sap: string;
  codigo_sap: string;
  alcance: string;
  comentarios: string;
  cantidad_estandar?: string;
  cantidad_real?: string;
  unidad_medida?: string;
  foto_preview?: string;
}

const materialesInsumosCapex = (insumos: InsumoCapex[]): Dict[] =>
  insumos
    .filter((i) => txt(i.texto_sap) || txt(i.codigo_sap))
    .map((i) =>
      limpio({
        tipo_registro: "inventario_capex",
        codigo_sap: txt(i.codigo_sap, 50),
        texto_sap: txt(i.texto_sap, 255),
        alcance: txt(i.alcance),
        comentarios: txt(i.comentarios),
        cantidad_estandar: num(i.cantidad_estandar),
        cantidad_real: num(i.cantidad_real),
        unidad_medida: txt(i.unidad_medida, 30),
      }),
    );

interface ActividadMoCapex {
  id: string;
  texto_sap: string;
  codigo_sap: string;
  alcance: string;
  comentarios: string;
  descripcion?: string;
  foto_antes_preview?: string;
  foto_despues_preview?: string;
}

const materialesManoObraCapex = (actividades: ActividadMoCapex[]): Dict[] =>
  actividades
    .filter((a) => txt(a.texto_sap) || txt(a.codigo_sap))
    .map((a) =>
      limpio({
        tipo_registro: "mano_obra_capex",
        codigo_sap: txt(a.codigo_sap, 50),
        texto_sap: txt(a.texto_sap, 255),
        alcance: txt(a.alcance),
        comentarios: txt(a.comentarios),
        descripcion: txt(a.descripcion),
      }),
    );

const evidenciasFotosCapex = (
  fotos: Array<{
    campo: string;
    ruta?: string;
    nombre_original?: string;
    descripcion?: string;
    seccion: string;
    /** Fase 3: binario conservado por el formulario (si lo hay). */
    file?: File;
  }>,
  pendientes?: PendienteSubida[],
): Dict[] =>
  conOrden(
    fotos
      .filter((f) => Boolean(f.ruta || f.nombre_original || f.file))
      .map((f) => {
        const fila = evidencia(f.seccion, f.campo, f.ruta, {
          nombre_original: f.nombre_original ?? f.file?.name,
          descripcion: f.descripcion,
        });
        pendiente(pendientes, f.file, f.seccion, f.campo, (ruta) => {
          fila.ruta_archivo = ruta;
          if (!fila.nombre_original) fila.nombre_original = f.file?.name;
        });
        return fila;
      }),
  );

// ─── CAPEX Tipología 1 (Reforma SPT / Pararrayos) ────────────────────────────

export const buildCapexTipologia1Payload = (
  d: FormCapexTipologia1Data,
  pendientes?: PendienteSubida[],
): SmuPayload => {
  const evidencias = evidenciasFotosCapex(
    [
      ...d.insumos.flatMap((insumo, index) => [
        {
          seccion: "inventario",
          campo: `insumo_${index + 1}_foto`,
          ruta: insumo.foto_preview,
          nombre_original: insumo.foto_nombre || insumo.foto_file?.name,
          descripcion: insumo.foto_descripcion,
          file: insumo.foto_file,
        },
      ]),
      ...d.actividades.flatMap((actividad, index) => [
        {
          seccion: "mano_obra",
          campo: `mo_${index + 1}_foto_antes`,
          ruta: actividad.foto_antes_preview,
          nombre_original:
            actividad.foto_antes_nombre || actividad.foto_antes_file?.name,
          descripcion: actividad.foto_antes_descripcion,
          file: actividad.foto_antes_file,
        },
        {
          seccion: "mano_obra",
          campo: `mo_${index + 1}_foto_despues`,
          ruta: actividad.foto_despues_preview,
          nombre_original:
            actividad.foto_despues_nombre || actividad.foto_despues_file?.name,
          descripcion: actividad.foto_despues_descripcion,
          file: actividad.foto_despues_file,
        },
      ]),
      {
        seccion: "transporte",
        campo: "transporte_foto_antes",
        ruta: d.transporte_foto_antes,
        nombre_original: d.transporte_foto_antes_file?.name,
        descripcion: d.transporte_foto_antes_descripcion,
        file: d.transporte_foto_antes_file,
      },
      {
        seccion: "transporte",
        campo: "transporte_foto_durante",
        ruta: d.transporte_foto_durante,
        nombre_original: d.transporte_foto_durante_file?.name,
        descripcion: d.transporte_foto_durante_descripcion,
        file: d.transporte_foto_durante_file,
      },
      {
        seccion: "transporte",
        campo: "transporte_foto_despues",
        ruta: d.transporte_foto_despues,
        nombre_original: d.transporte_foto_despues_file?.name,
        descripcion: d.transporte_foto_despues_descripcion,
        file: d.transporte_foto_despues_file,
      },
      {
        seccion: "spt",
        campo: "spt_naturaleza_terreno_foto",
        ruta: d.spt_naturaleza_terreno_foto,
        nombre_original: d.spt_naturaleza_terreno_foto_file?.name,
        descripcion: d.spt_naturaleza_terreno_foto_descripcion,
        file: d.spt_naturaleza_terreno_foto_file,
      },
      {
        seccion: "panoramica",
        campo: "foto_panoramica_preview",
        ruta: d.foto_panoramica_preview,
        nombre_original: d.foto_panoramica_file?.name,
        descripcion: d.foto_panoramica_descripcion,
        file: d.foto_panoramica_file,
      },
      {
        seccion: "panoramica",
        campo: "foto_plano_preview",
        ruta: d.foto_plano_preview,
        nombre_original: d.foto_plano_file?.name,
        descripcion: d.foto_plano_descripcion,
        file: d.foto_plano_file,
      },
      {
        seccion: "matricula",
        campo: "foto_soporte_matricula_preview",
        ruta: d.foto_soporte_matricula_preview,
        nombre_original: d.foto_soporte_matricula_file?.name,
        descripcion: d.foto_soporte_matricula_descripcion,
        file: d.foto_soporte_matricula_file,
      },
      ...d.fotos_justificacion.map((foto, index) => ({
        seccion: "justificacion",
        campo: `fotos_justificacion_${index + 1}`,
        ruta: foto.previewUrl,
        nombre_original: foto.nombre || foto.file?.name,
        descripcion: foto.descripcion,
        file: foto.file,
      })),
    ],
    pendientes,
  );

  const transporte = limpio({
    codigo_sap: txt(d.transporte_codigo_sap, 50),
    tipo_transporte: txt(d.transporte_tipo, 80),
    distancia_km: num(d.transporte_distancia_km),
    tiempo_traslado: txt(d.transporte_tiempo_desplazamiento, 50),
    descripcion: txt(d.transporte_descripcion),
  });

  return limpio({
    ...cabeceraCapex(d, "tipologia1"),

    evidencias,
    transportes: Object.keys(transporte).length > 0 ? [transporte] : [],
    materiales: [
      ...materialesInsumosCapex(d.insumos),
      ...materialesManoObraCapex(d.actividades),
    ],
    firmas_cierre: firmas([
      {
        rol: "entrega",
        nombre: d.responsable_entrega_nombre,
        cedula: d.responsable_entrega_cedula,
        cargo: d.responsable_entrega_cargo,
        fecha: d.responsable_entrega_fecha,
        ruta_firma: d.responsable_entrega_firma,
      },
      {
        rol: "aprobador",
        nombre: d.aprobado_nombre,
        cedula: d.aprobado_cedula,
        cargo: d.aprobado_cargo,
        fecha: d.aprobado_fecha,
        ruta_firma: d.aprobado_firma,
      },
    ]),

    observaciones: txt(d.observaciones_cierre),
    detalle_capex: limpio({
      tipologia: "tipologia1",
      descripcion_general_actividades: txt(d.descripcion_general_actividades),
      spt_naturaleza: txt(d.spt_naturaleza_terreno_desc, 150),
      spt_recomendacion: txt(d.spt_recomendacion_aliado),
      panoramica_recomendacion: txt(d.plano_recomendacion_aliado),
      otras_actividades_1: txt(d.otras_actividades_1, 255),
      otras_actividades_2: txt(d.otras_actividades_2, 255),
      otras_actividades_3: txt(d.otras_actividades_3, 255),
      texto_justificacion_otras_actividades: txt(
        d.texto_justificacion_otras_actividades,
      ),
      matricula_nombre: txt(d.matricula_nombre, 150),
      matricula_numero: txt(d.matricula_numero, 60),
      matricula_fecha: fechaDia(d.matricula_fecha),
      recomendacion_final: txt(d.recomendaciones_finales),
    }),
    spt_filas: d.filas_spt
      .filter(
        (fila) =>
          txt(fila.distancia) ||
          txt(fila.medida_ohmio) ||
          txt(fila.resistividad),
      )
      .map((fila, index) => ({
        orden: index + 1,
        distancia: txt(fila.distancia, 60),
        medida_ohmio: txt(fila.medida_ohmio, 60),
        resistividad: txt(fila.resistividad, 60),
      })),
  });
};

// ─── CAPEX Tipología 3 (Climatización) ───────────────────────────────────────

export const buildCapexTipologia3Payload = (
  d: FormCapexTipologia3Data,
  pendientes?: PendienteSubida[],
): SmuPayload => {
  const evidencias = evidenciasFotosCapex(
    [
      ...d.insumos.map((insumo, index) => ({
        seccion: "inventario",
        campo: `insumo_${index + 1}_foto`,
        ruta: insumo.foto_preview,
        nombre_original: insumo.foto_nombre || insumo.foto_file?.name,
        descripcion: insumo.foto_descripcion,
        file: insumo.foto_file,
      })),
      ...d.actividades.flatMap((actividad, index) => [
        {
          seccion: "mano_obra",
          campo: `mo_${index + 1}_foto_antes`,
          ruta: actividad.foto_antes_preview,
          nombre_original:
            actividad.foto_antes_nombre || actividad.foto_antes_file?.name,
          descripcion: actividad.foto_antes_descripcion,
          file: actividad.foto_antes_file,
        },
        {
          seccion: "mano_obra",
          campo: `mo_${index + 1}_foto_despues`,
          ruta: actividad.foto_despues_preview,
          nombre_original:
            actividad.foto_despues_nombre || actividad.foto_despues_file?.name,
          descripcion: actividad.foto_despues_descripcion,
          file: actividad.foto_despues_file,
        },
      ]),
      ...d.transportes.flatMap((transporte, index) => [
        {
          seccion: "transporte",
          campo: `transporte_${index + 1}_foto_antes`,
          ruta: transporte.foto_antes_preview,
          nombre_original:
            transporte.foto_antes_nombre || transporte.foto_antes_file?.name,
          descripcion: transporte.foto_antes_descripcion,
          file: transporte.foto_antes_file,
        },
        {
          seccion: "transporte",
          campo: `transporte_${index + 1}_foto_durante`,
          ruta: transporte.foto_durante_preview,
          nombre_original:
            transporte.foto_durante_nombre || transporte.foto_durante_file?.name,
          descripcion: transporte.foto_durante_descripcion,
          file: transporte.foto_durante_file,
        },
        {
          seccion: "transporte",
          campo: `transporte_${index + 1}_foto_despues`,
          ruta: transporte.foto_despues_preview,
          nombre_original:
            transporte.foto_despues_nombre ||
            transporte.foto_despues_file?.name,
          descripcion: transporte.foto_despues_descripcion,
          file: transporte.foto_despues_file,
        },
      ]),
    ],
    pendientes,
  );

  return limpio({
    ...cabeceraCapex(d, "tipologia3"),

    evidencias,
    materiales: [
      ...materialesInsumosCapex(d.insumos),
      ...materialesManoObraCapex(d.actividades),
    ],
    transportes: d.transportes
      .filter((t) => txt(t.tipo) || txt(t.codigo_sap) || txt(t.descripcion))
      .map((t) =>
        limpio({
          codigo_sap: txt(t.codigo_sap, 50),
          tipo_transporte: txt(t.tipo, 80),
          descripcion: txt(t.descripcion),
        }),
      ),

    detalle_capex: limpio({
      tipologia: "tipologia3",
      recomendacion_final: txt(d.recomendaciones_finales),
    }),
  });
};

// ─── CAPEX Tipología 5 (Sistema Eléctrico MT/BT) ─────────────────────────────

export const buildCapexTipologia5Payload = (
  d: FormCapexTipologia5Data,
  pendientes?: PendienteSubida[],
): SmuPayload => {
  const evidencias = evidenciasFotosCapex(
    [
      ...d.insumos.map((insumo, index) => ({
        seccion: "inventario",
        campo: `insumo_${index + 1}_foto`,
        ruta: insumo.foto_preview,
        nombre_original: insumo.foto_nombre || insumo.foto_file?.name,
        descripcion: insumo.foto_descripcion,
        file: insumo.foto_file,
      })),
      ...d.actividades.flatMap((actividad, index) => [
        {
          seccion: "mano_obra",
          campo: `mo_${index + 1}_foto_antes`,
          ruta: actividad.foto_antes_preview,
          nombre_original:
            actividad.foto_antes_nombre || actividad.foto_antes_file?.name,
          descripcion: actividad.foto_antes_descripcion,
          file: actividad.foto_antes_file,
        },
        {
          seccion: "mano_obra",
          campo: `mo_${index + 1}_foto_despues`,
          ruta: actividad.foto_despues_preview,
          nombre_original:
            actividad.foto_despues_nombre || actividad.foto_despues_file?.name,
          descripcion: actividad.foto_despues_descripcion,
          file: actividad.foto_despues_file,
        },
      ]),
      ...d.transportes.flatMap((transporte, index) => [
        {
          seccion: "transporte",
          campo: `transporte_${index + 1}_foto_antes`,
          ruta: transporte.foto_antes_preview,
          nombre_original:
            transporte.foto_antes_nombre || transporte.foto_antes_file?.name,
          descripcion: transporte.foto_antes_descripcion,
          file: transporte.foto_antes_file,
        },
        {
          seccion: "transporte",
          campo: `transporte_${index + 1}_foto_durante`,
          ruta: transporte.foto_durante_preview,
          nombre_original:
            transporte.foto_durante_nombre || transporte.foto_durante_file?.name,
          descripcion: transporte.foto_durante_descripcion,
          file: transporte.foto_durante_file,
        },
        {
          seccion: "transporte",
          campo: `transporte_${index + 1}_foto_despues`,
          ruta: transporte.foto_despues_preview,
          nombre_original:
            transporte.foto_despues_nombre ||
            transporte.foto_despues_file?.name,
          descripcion: transporte.foto_despues_descripcion,
          file: transporte.foto_despues_file,
        },
      ]),
      {
        seccion: "panoramica",
        campo: "foto_panoramica_preview",
        ruta: d.foto_panoramica_preview,
        nombre_original: d.foto_panoramica_file?.name,
        descripcion: d.foto_panoramica_descripcion,
        file: d.foto_panoramica_file,
      },
      {
        seccion: "panoramica",
        campo: "foto_plano_preview",
        ruta: d.foto_plano_preview,
        nombre_original: d.foto_plano_file?.name,
        descripcion: d.foto_plano_descripcion,
        file: d.foto_plano_file,
      },
      ...d.fotos_justificacion.map((foto, index) => ({
        seccion: "justificacion",
        campo: `fotos_justificacion_${index + 1}`,
        ruta: foto.previewUrl,
        nombre_original: foto.nombre || foto.file?.name,
        descripcion: foto.descripcion,
        file: foto.file,
      })),
    ],
    pendientes,
  );

  return limpio({
    ...cabeceraCapex(d, "tipologia5"),

    evidencias,
    materiales: [
      ...materialesInsumosCapex(d.insumos),
      ...materialesManoObraCapex(d.actividades),
    ],
    transportes: d.transportes
      .filter(
        (t) =>
          txt(t.tipo) ||
          txt(t.codigo_sap) ||
          txt(t.descripcion) ||
          num(t.distancia_km),
      )
      .map((t) =>
        limpio({
          codigo_sap: txt(t.codigo_sap, 50),
          tipo_transporte: txt(t.tipo, 80),
          distancia_km: num(t.distancia_km),
          tiempo_traslado: txt(t.tiempo, 50),
          descripcion: txt(t.descripcion),
        }),
      ),

    detalle_capex: limpio({
      tipologia: "tipologia5",
      panoramica_recomendacion: txt(d.plano_recomendacion_aliado),
      texto_justificacion_otras_actividades: txt(d.texto_justificacion),
      recomendacion_final: txt(d.recomendaciones_finales),
    }),
  });
};

// ─── Petición ────────────────────────────────────────────────────────────────
// Los formularios envían con `useFormSubmit` (aplica CSRF, manejo de errores
// y loading) usando `SMU_ACTIVIDADES_ENDPOINT`; no hay wrapper POST extra.

// ─── Historial (GET /smu/actividades/) · módulo Gestión SMU ─────────────────

/**
 * Fila del listado: lo que devuelve `SmuActividadListSerializer` y lo que
 * muestra la tabla de `/smu/gestion_smu`.
 */
export interface ActividadSmuResumen {
  id: number;
  categoria: string;
  categoria_display: string;
  tipo_formulario: string;
  tipo_formulario_display: string;
  /** Tipo de planta/estación; vacío en los formularios de planta. */
  tipo_estacion: string | null;
  nombre_estacion: string;
  codigo_ot: string | null;
  responsable_cedula: string | null;
  responsable_nombre: string | null;
  estado: string;
  estado_display: string;
  fecha_inicio: string | null;
  created_at: string;
}

/** Filtros exactos que soporta `GET /smu/actividades/`. */
export interface FiltrosActividadSmu {
  categoria?: string;
  tipo_formulario?: string;
  estado?: string;
}

interface RespuestaListadoSmu {
  count: number;
  next: string | null;
  previous: string | null;
  results: ActividadSmuResumen[];
}

/** Máximo del backend (`SmuActividadPagination.page_size_query_param`). */
const TAMANO_PAGINA_LISTADO = 100;
/** Red de seguridad: 20 páginas × 100 = 20 000 formularios por llamada. */
const TOPE_PAGINAS_LISTADO = 20;

/**
 * Descarga el historial de actividades, recorriendo la paginación de DRF
 * (`{count, next, results}`) hasta agotar las páginas.
 *
 * Devuelve las filas "plana" para que la tabla de gestión filtre, ordene y
 * exporte en memoria; los filtros viajan al servidor para no bajar de más.
 */
export const listarActividadesSMU = async (
  filtros: FiltrosActividadSmu = {},
): Promise<ActividadSmuResumen[]> => {
  // Mismo motivo que `subirEvidenciaSMU`: no arrastrar axios a los tests.
  const { default: api } = await import("@/lib/api");

  const base: Dict = {
    ...limpio(filtros as Dict),
    page_size: TAMANO_PAGINA_LISTADO,
    ordering: "-id",
  };
  const resultados: ActividadSmuResumen[] = [];
  let pagina = 1;
  let total = Number.POSITIVE_INFINITY;

  while (resultados.length < total && pagina <= TOPE_PAGINAS_LISTADO) {
    const { data } = await api.get<RespuestaListadoSmu>(SMU_ACTIVIDADES_ENDPOINT, {
      params: { ...base, page: pagina },
    });
    const filas = Array.isArray(data.results) ? data.results : [];
    resultados.push(...filas);
    total = typeof data.count === "number" ? data.count : resultados.length;
    if (!data.next || filas.length === 0) break;
    pagina += 1;
  }

  return resultados;
};

// ─── Exporte por fila (GET /smu/actividades/<id>/export/) ─────────────────────

/**
 * Parejas `categoria|tipo_formulario` que ya tienen plantilla en el backend.
 * Debe viajar al mismo registro que `apps.smu.export`: si se suma una
 * plantilla allá, se agrega aquí para habilitar el botón.
 */
const TIPOS_CON_PLANCHA_DE_EXPORT = [
  "emergencias|estandar",
  "correctivos|estandar",
  "preventivos|aire_acondicionado",
  "preventivos|planta",
  "correctivos_capex|tipologia1",
  "correctivos_capex|tipologia3",
  "correctivos_capex|tipologia5",
];

/** ¿Este formulario ya puede exportarse a Excel? Evita el 400 del backend. */
export const tienePlantillaExporte = (actividad: {
  categoria: string;
  tipo_formulario: string;
}): boolean =>
  TIPOS_CON_PLANCHA_DE_EXPORT.includes(
    `${actividad.categoria}|${actividad.tipo_formulario}`,
  );

const nombreDesdeContentDisposition = (header?: string): string | null => {
  if (!header) return null;
  const coincide = /filename="?([^";]+)"?/i.exec(header);
  return coincide?.[1]?.trim() || null;
};

/**
 * Los errores del backend viajan como JSON, pero `responseType: "blob"` los
 * entrega como Blob: hay que leerlos para mostrar el motivo real (p. ej.
 * "aún no tiene plantilla de exporte").
 */
const detalleDesdeBlob = async (error: unknown): Promise<string | null> => {
  const data = (error as { response?: { data?: unknown } })?.response?.data;
  if (!(data instanceof Blob)) return null;

  try {
    const json = JSON.parse(await data.text()) as { detail?: string };
    return typeof json.detail === "string" ? json.detail : null;
  } catch {
    return null;
  }
};

/**
 * Descarga el Excel del formulario en el **formato de su tipo de formulario**
 * (el backend arma el archivo con openpyxl según la plantilla que le toca).
 *
 * Devuelve el nombre con el que se descargó. Si el backend rechaza la
 * exportación, lanza un `Error` con su `detail` en español.
 */
export const descargarExcelActividadSMU = async (actividad: {
  id: number;
  categoria: string;
  tipo_formulario: string;
}): Promise<string> => {
  // Mismo motivo que `subirEvidenciaSMU`: no arrastrar axios a los tests.
  const { default: api } = await import("@/lib/api");

  try {
    const response = await api.get(
      `${SMU_ACTIVIDADES_ENDPOINT}${actividad.id}/export/`,
      { responseType: "blob" },
    );

    const nombre =
      nombreDesdeContentDisposition(
        response.headers["content-disposition"] as string | undefined,
      ) ?? `smu_${actividad.id}.xlsx`;

    const blob = response.data as Blob;
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);

    return nombre;
  } catch (error) {
    const detalle = await detalleDesdeBlob(error);
    if (detalle) throw new Error(detalle);
    throw error;
  }
};
