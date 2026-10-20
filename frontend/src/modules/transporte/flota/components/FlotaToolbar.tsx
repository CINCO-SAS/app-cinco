// src/modules/transporte/flota/components/FlotaToolbar.tsx
//
// Toolbar de Flota: KPIs del semáforo + filtros de negocio (contrato,
// estado, vigencia documental). Sigue el patrón del toolbar de operaciones.

import Badge from "@/components/ui/badge/Badge";
import { PuntoVigencia } from "../../components/SemaforoVigencia";
import { ETIQUETAS_TIPO_CONTRATO } from "../flotaView.utils";
import type { FiltrosFlota } from "../flotaView.hooks";

interface FlotaToolbarProps {
  resumen: {
    total: number;
    activos: number;
    conSoatVencido: number;
    conCdaVencido: number;
  };
  filtros: FiltrosFlota;
  actualizarFiltro: (clave: keyof FiltrosFlota, valor: string) => void;
  limpiarFiltros: () => void;
  hayFiltrosActivos: boolean;
  onExportar?: () => void;
}

const SELECT_CLASES =
  "h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const KPI = ({
  etiqueta,
  valor,
  tono,
}: {
  etiqueta: string;
  valor: number;
  tono?: "error" | "success";
}) => (
  <div className="flex flex-col items-center px-3">
    <span
      className={`text-lg font-semibold tabular-nums ${
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

export const FlotaToolbar = ({
  resumen,
  filtros,
  actualizarFiltro,
  limpiarFiltros,
  hayFiltrosActivos,
  onExportar,
}: FlotaToolbarProps) => (
  <div className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
    {/* KPIs */}
    <div className="flex flex-wrap items-center divide-x divide-gray-200 dark:divide-gray-800">
      <KPI etiqueta="Total" valor={resumen.total} />
      <KPI etiqueta="Activos" valor={resumen.activos} tono="success" />
      <div className="flex items-center gap-2 px-3">
        <PuntoVigencia estado="VENCIDA" />
        <KPI etiqueta="SOAT vencido" valor={resumen.conSoatVencido} tono="error" />
      </div>
      <div className="flex items-center gap-2 px-3">
        <PuntoVigencia estado="VENCIDA" />
        <KPI etiqueta="CDA vencido" valor={resumen.conCdaVencido} tono="error" />
      </div>
    </div>

    {/* Filtros */}
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={filtros.tipo_contrato}
        onChange={(e) => actualizarFiltro("tipo_contrato", e.target.value)}
        className={SELECT_CLASES}
        aria-label="Filtrar por tipo de contrato"
      >
        <option value="">Todos los contratos</option>
        {Object.entries(ETIQUETAS_TIPO_CONTRATO).map(([valor, etiqueta]) => (
          <option key={valor} value={valor}>
            {etiqueta}
          </option>
        ))}
      </select>

      <select
        value={filtros.activo}
        onChange={(e) => actualizarFiltro("activo", e.target.value)}
        className={SELECT_CLASES}
        aria-label="Filtrar por estado"
      >
        <option value="">Activo e inactivos</option>
        <option value="true">Solo activos</option>
        <option value="false">Solo inactivos</option>
      </select>

      <select
        value={filtros.vigencia}
        onChange={(e) => actualizarFiltro("vigencia", e.target.value)}
        className={SELECT_CLASES}
        aria-label="Filtrar por vigencia documental"
      >
        <option value="">Cualquier vigencia</option>
        <option value="AL_DIA">Documentos al día</option>
        <option value="POR_VENCER">Al menos uno por vencer</option>
        <option value="VENCIDA">Al menos uno vencido</option>
        <option value="SIN_REGISTRO">Sin registro</option>
      </select>

      {hayFiltrosActivos && (
        <button
          type="button"
          onClick={limpiarFiltros}
          className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400"
        >
          Limpiar filtros
        </button>
      )}

      <div className="ml-auto flex items-center gap-2">
        {onExportar && (
          <button
            type="button"
            onClick={onExportar}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:hover:bg-gray-800"
          >
            Exportar CSV
          </button>
        )}
        <Badge color="light" size="sm">
          {resumen.total} vehículo{resumen.total === 1 ? "" : "s"}
        </Badge>
      </div>
    </div>
  </div>
);
