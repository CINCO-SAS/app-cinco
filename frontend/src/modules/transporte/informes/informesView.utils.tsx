// src/modules/transporte/informes/informesView.utils.tsx
//
// Utilidades de la pantalla de Informes (F5), Tab 2 del legacy.
//
// PASO 2: los bloques "Transporte Día" y "Transporte Mes". Ambos devuelven
// la MISMA forma (`AreaInforme[]`: un área con desglose por carpetas), así
// que comparten tabla, columnas y formato; solo cambia la fuente (una
// fecha concreta vs el mes completo) y que el Mes admite `solo_aprobados`.
//
// NOTA sobre el dinero: en estos bloques los importes llegan como `number`
// (ver el aviso de formato en transporte.types.ts). El formateo se hace
// SIEMPRE aquí, para que un solo sitio decida cómo se ve un COP.

import type {
  BloqueAgregadoInforme,
  DesgloseEstadosInforme,
} from "@/types/transporte.types";

/** Meses en mayúsculas — espejo de `InformeService.MESES`. */
export const MESES = [
  "ENERO",
  "FEBRERO",
  "MARZO",
  "ABRIL",
  "MAYO",
  "JUNIO",
  "JULIO",
  "AGOSTO",
  "SEPTIEMBRE",
  "OCTUBRE",
  "NOVIEMBRE",
  "DICIEMBRE",
] as const;

/**
 * Meses abreviados para ejes de gráfico (`Ene 2024`). Con histórico
 * completo el eje acumula un punto por mes desde 2024, así que usar los
 * nombres completos dejaría las etiquetas ilegibles.
 */
export const MESES_CORTOS = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic",
] as const;

/**
 * `$ 1.234.567` — sin decimales, igual que formateaba la sábana
 * (`toLocaleString('es-CO', {currency:'COP'})`).
 *
 * Recibe `number` porque así llegan los agregados. Las filas de `Salida`
 * llegan como `string`; quien las formatee debe convertirlas antes.
 */
export const formatoCOP = (valor: number): string =>
  new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(valor);

/** `YYYY-MM-DD` desde año/mes(1-12)/día, con relleno de ceros. */
export const fechaISO = (anio: number, mes: number, dia: number): string =>
  `${anio}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;

/** Último día del mes (mes 1-12). `new Date(a, m, 0)` da el día 0 del
 *  mes siguiente, es decir el último del mes pedido. */
export const ultimoDiaDelMes = (anio: number, mes: number): number =>
  new Date(anio, mes, 0).getDate();

/** Etiqueta visible del periodo, p. ej. `ENERO 2026`. */
export const etiquetaPeriodo = (mes: number, anio: number): string =>
  `${MESES[mes - 1]} ${anio}`;

/** Etiqueta visible de una fecha `YYYY-MM-DD`, p. ej. `05/10/2026`. */
export const etiquetaFecha = (fecha: string): string => {
  const [anio, mes, dia] = fecha.split("-");
  if (!anio || !mes || !dia) return fecha;
  return `${dia}/${mes}/${anio}`;
};

// ---------------------------------------------------------------------------
// Semáforo de un bloque
// ---------------------------------------------------------------------------

export type IndicadorEstado = "completo" | "parcial" | "ninguno" | "sin_datos";

export const INDICADORES_ESTADO: Record<
  IndicadorEstado,
  { clase: string; icono: string; titulo: string }
> = {
  completo: {
    clase: "bg-success-500",
    icono: "✓",
    titulo: "Todas las salidas aprobadas o validadas",
  },
  parcial: {
    clase: "bg-warning-500",
    icono: "−",
    titulo: "Algunas salidas aprobadas o validadas",
  },
  ninguno: {
    clase: "bg-error-500",
    icono: "✕",
    titulo: "Ninguna salida aprobada ni validada",
  },
  sin_datos: {
    clase: "bg-gray-300 dark:bg-gray-700",
    icono: "",
    titulo: "Sin salidas",
  },
};

/**
 * Semáforo de un bloque — misma regla que el render de la columna "Aprobado"
 * del legacy (`loadTbInfoSalida`, `columnDefs` targets 8).
 *
 * Compara `aprobado + validado` contra `total` del MISMO `arr_estado`.
 */
export const indicadorEstado = (
  estados: DesgloseEstadosInforme,
): IndicadorEstado => {
  const aprobados = estados.aprobado.cnt + estados.validado.cnt;
  if (estados.total.cnt === 0) return "sin_datos";
  if (aprobados === estados.total.cnt) return "completo";
  if (aprobados > 0) return "parcial";
  return "ninguno";
};

// ---------------------------------------------------------------------------
// Totales
// ---------------------------------------------------------------------------

const CLAVES_ESTADO = [
  "aprobado",
  "validado",
  "reportado",
  "rechazado",
  "total",
] as const;

/**
 * Suma una lista de bloques para la fila de "TOTALES" del pie.
 *
 * Suma TODO, incluido `arr_estado`: el desglose siempre refleja todas las
 * filas aunque `solo_aprobados` haya acotado los contadores y el importe.
 */
export const sumarBloques = (
  bloques: BloqueAgregadoInforme[],
): BloqueAgregadoInforme => {
  const acumulado: BloqueAgregadoInforme = {
    propios: 0,
    renting: 0,
    externos: 0,
    total_vehi: 0,
    total_dia: 0,
    arr_estado: {
      aprobado: { cnt: 0, valor: 0 },
      validado: { cnt: 0, valor: 0 },
      reportado: { cnt: 0, valor: 0 },
      rechazado: { cnt: 0, valor: 0 },
      total: { cnt: 0, valor: 0 },
    },
  };

  for (const bloque of bloques) {
    acumulado.propios += bloque.propios;
    acumulado.renting += bloque.renting;
    acumulado.externos += bloque.externos;
    acumulado.total_vehi += bloque.total_vehi;
    acumulado.total_dia += bloque.total_dia;
    for (const clave of CLAVES_ESTADO) {
      acumulado.arr_estado[clave].cnt += bloque.arr_estado[clave].cnt;
      acumulado.arr_estado[clave].valor += bloque.arr_estado[clave].valor;
    }
  }

  return acumulado;
};
