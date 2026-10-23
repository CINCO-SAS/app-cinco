// src/modules/transporte/informes/components/InformeExportarMes.tsx
//
// Botones de exportación del bloque "Transporte Mes" (decisión de alcance:
// solo este export por ahora; el de "Reporte Área" y el refresco WFM quedan
// para una tanda aparte).
//
// Baja las salidas que componen el bloque vía `GET /salidas/export/`
// (F5-4), mandando el RANGO del mes como los filtros `desde`/`hasta` de B1.
// El archivo tiene las 13 columnas de la sábana, con números reales en XLSX
// y `;` + BOM en CSV para que Excel en español abra los acentos sin tocar
// nada (decisiones del backend).
//
// LÍMITE HONESTO, dicho en la propia interfaz: el export NO entiende el
// interruptor «Solo aprobados» — es el filtro B1 de salidas, que admite UN
// estado, y "aprobado o validado" es un OR. Así que el archivo trae todas
// las salidas del mes excepto las eliminadas, que es lo que hace el
// endpoint sin parámetro `estado`. Preferible decirlo a que el usuario
// descubra la diferencia contando filas.

import { useState } from "react";

import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import { fechaISO, ultimoDiaDelMes } from "../informesView.utils";

type Formato = "xlsx" | "csv";

const ETIQUETA_FORMATO: Record<Formato, string> = {
  xlsx: "Excel",
  csv: "CSV",
};

/**
 * Descarga un blob disparando un `<a download>` sintético.
 *
 * Sin librería: `URL.createObjectURL` + click + `revokeObjectURL` es todo lo
 * que hace falta, y el `revoke` va con retardo para no cortar la descarga
 * mientras el navegador la está iniciando.
 */
const descargarBlob = (blob: Blob, nombre: string): void => {
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

interface InformeExportarMesProps {
  mes: number;
  anio: number;
}

export const InformeExportarMes = ({ mes, anio }: InformeExportarMesProps) => {
  const [formatoEnCurso, setFormatoEnCurso] = useState<Formato | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exportar = async (formato: Formato) => {
    setFormatoEnCurso(formato);
    setError(null);
    try {
      const blob = await transporteService.exportarSalidas({
        desde: fechaISO(anio, mes, 1),
        hasta: fechaISO(anio, mes, ultimoDiaDelMes(anio, mes)),
        formato,
      });
      const periodo = `${anio}-${String(mes).padStart(2, "0")}`;
      descargarBlob(blob, `transporte_${periodo}.${formato}`);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError?.message ?? "No fue posible generar el archivo.");
      logDevelopmentError("Error exportando el informe del mes:", err);
    } finally {
      setFormatoEnCurso(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-end gap-1.5">
      {(Object.keys(ETIQUETA_FORMATO) as Formato[]).map((formato) => (
        <button
          key={formato}
          type="button"
          onClick={() => void exportar(formato)}
          disabled={formatoEnCurso !== null}
          className={BOTON_EXPORT}
          title={
            `Descargar las salidas del mes en ${ETIQUETA_FORMATO[formato]} ` +
            "(todas, excepto las eliminadas)."
          }
        >
          {formatoEnCurso === formato
            ? "Generando…"
            : `↓ ${ETIQUETA_FORMATO[formato]}`}
        </button>
      ))}
      {error && (
        <span className="text-xs text-error-500" role="alert">
          {error}
        </span>
      )}
    </div>
  );
};
