// src/modules/transporte/flota/components/FlotaKpis.tsx
//
// KPIs del semáforo de la flota. Van JUSTO ENCIMA de la tabla, en su propia
// tira, y no dentro de la barra de filtros: ahí competían visualmente con
// los selects y apretaban la barra hasta hacerla incómoda.
//
// Siguen a los filtros a propósito: al elegir "Solo activos" el contador
// acota ese subconjunto, de modo que el número que se ve coincide con las
// filas de la tabla. Los vehículos históricos siguen visibles por defecto
// porque son el rastro de la flota.

import { PuntoVigencia } from "../../components/SemaforoVigencia";
import type { ResumenFlota } from "../flotaView.hooks";

interface FlotaKpisProps {
  resumen: ResumenFlota;
}

const KPI = ({
  etiqueta,
  valor,
  tono,
}: {
  etiqueta: string;
  valor: number;
  tono?: "error" | "success";
}) => (
  <div className="flex flex-col items-center px-4">
    <span
      className={`text-xl font-semibold tabular-nums ${
        tono === "error"
          ? "text-error-600 dark:text-error-400"
          : tono === "success"
            ? "text-success-600 dark:text-success-400"
            : "text-gray-800 dark:text-white/90"
      }`}
    >
      {valor}
    </span>
    <span className="text-xs text-gray-500 dark:text-gray-400">{etiqueta}</span>
  </div>
);

const ConIndicador = ({
  etiqueta,
  valor,
}: {
  etiqueta: string;
  valor: number;
}) => (
  <div className="flex items-center gap-2">
    <PuntoVigencia estado="VENCIDA" />
    <KPI etiqueta={etiqueta} valor={valor} tono="error" />
  </div>
);

export const FlotaKpis = ({ resumen }: FlotaKpisProps) => (
  <div className="mb-4 flex flex-wrap items-center justify-center divide-x divide-gray-200 rounded-xl border border-gray-200 bg-white py-3 dark:divide-gray-800 dark:border-gray-800 dark:bg-gray-900 sm:justify-start">
    <KPI etiqueta="Total" valor={resumen.total} />
    <KPI etiqueta="Activos" valor={resumen.activos} tono="success" />
    <ConIndicador etiqueta="SOAT vencido" valor={resumen.conSoatVencido} />
    <ConIndicador etiqueta="CDA vencido" valor={resumen.conCdaVencido} />
  </div>
);
