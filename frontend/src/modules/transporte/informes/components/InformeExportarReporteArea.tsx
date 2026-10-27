// src/modules/transporte/informes/components/InformeExportarReporteArea.tsx
//
// Botón de exportación del bloque "Reporte Área" (el equivalente al botón
// `extend: 'excelHtml5'` que el legacy ponía en `tb_trans_x_aprobacion`).
//
// QUÉ EXPORTA: los datos que ya están en memoria (`areas`), no hace ninguna
// petición nueva. El mismo array `AreaInforme[]` que pinta la tabla se
// convierte aquí a un CSV y se descarga directamente en el navegador.
// No se usa el endpoint de exportación de salidas porque lo que el legacy
// exportaba era la TABLA DE RESUMEN POR ÁREA (estados y totales), no el
// listado fila a fila de salidas.
//
// FORMATO: CSV con separador `;` y BOM UTF-8 para que Excel en español abra
// los acentos sin configuración adicional — igual que el backend en F5-4.
//
// COLUMNAS (mismo orden que la tabla visible):
//   Área · Cnt/Val Cnt · Cnt/Val Valor · Aprobado Cnt · Aprobado Valor ·
//   Validado Cnt · Validado Valor · Rechazado Cnt · Rechazado Valor ·
//   Pendiente Cnt · Pendiente Valor
//
// Nota: "Pendiente" = estado REPORTADO (etiqueta heredada del legacy).

import { useState } from "react";

import type { AreaInforme, ContadorEstadoInforme } from "@/types/transporte.types";
import { formatoCOP } from "../informesView.utils";

const BOM = "\uFEFF";
const SEP = ";";

const sumar = (
  a: ContadorEstadoInforme,
  b: ContadorEstadoInforme,
): ContadorEstadoInforme => ({ cnt: a.cnt + b.cnt, valor: a.valor + b.valor });

const celdas = (c: ContadorEstadoInforme): string =>
  `${c.cnt}${SEP}${formatoCOP(c.valor)}`;

/** Convierte el array de áreas a CSV (con BOM). */
const aCsv = (areas: AreaInforme[], periodo: string): string => {
  const cabecera = [
    `"Reporte Área — ${periodo}"`,
    "",
    [
      "Área",
      "Cnt/Val Cnt",
      "Cnt/Val Valor",
      "Aprobado Cnt",
      "Aprobado Valor",
      "Validado Cnt",
      "Validado Valor",
      "Rechazado Cnt",
      "Rechazado Valor",
      "Pendiente Cnt",
      "Pendiente Valor",
    ].join(SEP),
  ].join("\n");

  const filas = areas.map((a) => {
    const cntVal = sumar(a.arr_estado.aprobado, a.arr_estado.validado);
    return [
      `"${a.area}"`,
      celdas(cntVal),
      celdas(a.arr_estado.aprobado),
      celdas(a.arr_estado.validado),
      celdas(a.arr_estado.rechazado),
      celdas(a.arr_estado.reportado),
    ].join(SEP);
  });

  // Fila de totales.
  const vacio: ContadorEstadoInforme = { cnt: 0, valor: 0 };
  const tot = areas.reduce(
    (acc, a) => ({
      cntVal: sumar(acc.cntVal, sumar(a.arr_estado.aprobado, a.arr_estado.validado)),
      aprobado: sumar(acc.aprobado, a.arr_estado.aprobado),
      validado: sumar(acc.validado, a.arr_estado.validado),
      rechazado: sumar(acc.rechazado, a.arr_estado.rechazado),
      reportado: sumar(acc.reportado, a.arr_estado.reportado),
    }),
    {
      cntVal: vacio,
      aprobado: vacio,
      validado: vacio,
      rechazado: vacio,
      reportado: vacio,
    },
  );

  const filaTotales = [
    `"TOTALES"`,
    celdas(tot.cntVal),
    celdas(tot.aprobado),
    celdas(tot.validado),
    celdas(tot.rechazado),
    celdas(tot.reportado),
  ].join(SEP);

  return BOM + [cabecera, ...filas, filaTotales].join("\n");
};

const descargarCsv = (contenido: string, nombre: string): void => {
  const blob = new Blob([contenido], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const BOTON_EXPORT =
  "h-8 rounded-lg border border-gray-300 bg-white px-2.5 text-xs font-medium " +
  "text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed " +
  "disabled:opacity-60 focus:border-brand-500 focus:outline-none focus:ring-2 " +
  "focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 " +
  "dark:text-white/90 dark:hover:bg-gray-800";

interface InformeExportarReporteAreaProps {
  areas: AreaInforme[];
  mes: number;
  anio: number;
  /** Etiqueta del período visible ("OCTUBRE 2026"), para el encabezado del CSV. */
  periodo: string;
}

export const InformeExportarReporteArea = ({
  areas,
  mes,
  anio,
  periodo,
}: InformeExportarReporteAreaProps) => {
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const exportar = () => {
    if (areas.length === 0) return;
    setDescargando(true);
    setError(null);
    try {
      const csv = aCsv(areas, periodo);
      const nombre = `reporte_area_${anio}-${String(mes).padStart(2, "0")}.csv`;
      descargarCsv(csv, nombre);
    } catch {
      setError("No fue posible generar el archivo.");
    } finally {
      setDescargando(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-end gap-1.5">
      <button
        id="btn-exportar-reporte-area"
        type="button"
        onClick={exportar}
        disabled={descargando || areas.length === 0}
        className={BOTON_EXPORT}
        title={
          areas.length === 0
            ? "No hay datos para exportar."
            : "Descargar el resumen de estados por área en CSV (abre en Excel)."
        }
      >
        {descargando ? "Generando…" : "↓ Excel"}
      </button>
      {error && (
        <span className="text-xs text-error-500" role="alert">
          {error}
        </span>
      )}
    </div>
  );
};
