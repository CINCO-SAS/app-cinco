"use client";

import React, { useMemo, useCallback } from "react";
import { RotateCcw, Filter, CalendarDays } from "lucide-react";
import DatePicker from "@/components/form/date-picker";
import Button from "@/components/ui/button/Button";

export interface DateRangeFilterProps {
  fechaDesde: string;
  fechaHasta: string;
  onFechaDesdeChange: (fecha: string) => void;
  onFechaHastaChange: (fecha: string) => void;
  onLimpiar: () => void;
  totalRegistros?: number;
  registrosFiltrados?: number;
  label?: string;
  placeholderDesde?: string;
  placeholderHasta?: string;
  className?: string;
  showPresets?: boolean;
  showCounts?: boolean;
}

const formatDateToYmd = (date: Date): string => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const toDateOrUndefined = (value?: string | null): Date | undefined => {
  if (!value) return undefined;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (match) {
    const [, year, month, day] = match;
    return new Date(Number(year), Number(month) - 1, Number(day), 12);
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
};

export const DateRangeFilter: React.FC<DateRangeFilterProps> = ({
  fechaDesde,
  fechaHasta,
  onFechaDesdeChange,
  onFechaHastaChange,
  onLimpiar,
  totalRegistros,
  registrosFiltrados,
  label = "Filtrar por Fecha:",
  placeholderDesde = "Desde (Inicio)",
  placeholderHasta = "Hasta (Fin)",
  className = "",
  showPresets = true,
  showCounts = true,
}) => {
  const tieneFiltroActivo = Boolean(fechaDesde || fechaHasta);

  // Fechas de referencia calculadas
  const presets = useMemo(() => {
    const hoy = new Date();
    const hoyStr = formatDateToYmd(hoy);

    // Esta Semana (Lunes a Domingo)
    const diaSemana = hoy.getDay();
    const diffLunes = diaSemana === 0 ? -6 : 1 - diaSemana;
    const lunes = new Date(hoy);
    lunes.setDate(hoy.getDate() + diffLunes);
    const domingo = new Date(lunes);
    domingo.setDate(lunes.getDate() + 6);

    // Este Mes
    const primerDiaMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    const ultimoDiaMes = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0);

    // Mes Anterior
    const primerDiaMesAnt = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
    const ultimoDiaMesAnt = new Date(hoy.getFullYear(), hoy.getMonth(), 0);

    return {
      hoy: { desde: hoyStr, hasta: hoyStr },
      esta_semana: { desde: formatDateToYmd(lunes), hasta: formatDateToYmd(domingo) },
      este_mes: { desde: formatDateToYmd(primerDiaMes), hasta: formatDateToYmd(ultimoDiaMes) },
      mes_anterior: { desde: formatDateToYmd(primerDiaMesAnt), hasta: formatDateToYmd(ultimoDiaMesAnt) },
    };
  }, []);

  // Determinar preset activo
  const activePreset = useMemo(() => {
    if (!fechaDesde && !fechaHasta) return "todas";
    if (fechaDesde === presets.hoy.desde && fechaHasta === presets.hoy.hasta) return "hoy";
    if (fechaDesde === presets.esta_semana.desde && fechaHasta === presets.esta_semana.hasta) return "esta_semana";
    if (fechaDesde === presets.este_mes.desde && fechaHasta === presets.este_mes.hasta) return "este_mes";
    if (fechaDesde === presets.mes_anterior.desde && fechaHasta === presets.mes_anterior.hasta) return "mes_anterior";
    return null;
  }, [fechaDesde, fechaHasta, presets]);

  // Handlers para presets
  const handlePresetTodas = useCallback(() => {
    onLimpiar();
  }, [onLimpiar]);

  const handlePresetHoy = useCallback(() => {
    onFechaDesdeChange(presets.hoy.desde);
    onFechaHastaChange(presets.hoy.hasta);
  }, [onFechaDesdeChange, onFechaHastaChange, presets.hoy]);

  const handlePresetEstaSemana = useCallback(() => {
    onFechaDesdeChange(presets.esta_semana.desde);
    onFechaHastaChange(presets.esta_semana.hasta);
  }, [onFechaDesdeChange, onFechaHastaChange, presets.esta_semana]);

  const handlePresetEsteMes = useCallback(() => {
    onFechaDesdeChange(presets.este_mes.desde);
    onFechaHastaChange(presets.este_mes.hasta);
  }, [onFechaDesdeChange, onFechaHastaChange, presets.este_mes]);

  const handlePresetMesAnterior = useCallback(() => {
    onFechaDesdeChange(presets.mes_anterior.desde);
    onFechaHastaChange(presets.mes_anterior.hasta);
  }, [onFechaDesdeChange, onFechaHastaChange, presets.mes_anterior]);

  return (
    <div
      className={`w-full bg-gray-50/70 dark:bg-gray-800/40 rounded-xl border border-gray-200/80 dark:border-gray-800 p-3.5 mb-5 transition-all ${className}`}
    >
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        {/* Lado Izquierdo: Título y Presets Rápidos con Morado Activo */}
        <div className="flex flex-wrap items-center gap-2">
          {label && (
            <div className="flex items-center space-x-1.5 text-xs font-bold text-gray-700 dark:text-gray-200 mr-1">
              <Filter className="h-3.5 w-3.5 text-brand-500" />
              <span>{label}</span>
            </div>
          )}

          {showPresets && (
            <div className="flex flex-wrap items-center gap-1 bg-white dark:bg-gray-900/70 p-1 rounded-lg border border-gray-200/70 dark:border-gray-700/60 shadow-2xs">
              <button
                type="button"
                onClick={handlePresetTodas}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  activePreset === "todas"
                    ? "bg-brand-600 text-white font-semibold shadow-sm"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
                }`}
              >
                Todas
              </button>
              <button
                type="button"
                onClick={handlePresetHoy}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  activePreset === "hoy"
                    ? "bg-brand-600 text-white font-semibold shadow-sm"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
                }`}
              >
                Hoy
              </button>
              <button
                type="button"
                onClick={handlePresetEstaSemana}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  activePreset === "esta_semana"
                    ? "bg-brand-600 text-white font-semibold shadow-sm"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
                }`}
              >
                Esta Semana
              </button>
              <button
                type="button"
                onClick={handlePresetEsteMes}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  activePreset === "este_mes"
                    ? "bg-brand-600 text-white font-semibold shadow-sm"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
                }`}
              >
                Este Mes
              </button>
              <button
                type="button"
                onClick={handlePresetMesAnterior}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  activePreset === "mes_anterior"
                    ? "bg-brand-600 text-white font-semibold shadow-sm"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
                }`}
              >
                Mes Anterior
              </button>
            </div>
          )}
        </div>

        {/* Lado Derecho: Inputs DatePicker (Desde y Hasta) + Limpiar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Fecha Desde */}
          <div className="w-full sm:w-44">
            <DatePicker
              id="filtro_rango_desde"
              placeholder={placeholderDesde}
              defaultDate={fechaDesde ? toDateOrUndefined(fechaDesde) : undefined}
              onChange={(dates: Date[] | Date) => {
                const selected = Array.isArray(dates) ? dates[0] : dates;
                if (selected instanceof Date && !isNaN(selected.getTime())) {
                  onFechaDesdeChange(formatDateToYmd(selected));
                } else {
                  onFechaDesdeChange("");
                }
              }}
            />
          </div>

          {/* Fecha Hasta */}
          <div className="w-full sm:w-44">
            <DatePicker
              id="filtro_rango_hasta"
              placeholder={placeholderHasta}
              defaultDate={fechaHasta ? toDateOrUndefined(fechaHasta) : undefined}
              onChange={(dates: Date[] | Date) => {
                const selected = Array.isArray(dates) ? dates[0] : dates;
                if (selected instanceof Date && !isNaN(selected.getTime())) {
                  onFechaHastaChange(formatDateToYmd(selected));
                } else {
                  onFechaHastaChange("");
                }
              }}
            />
          </div>

          {/* Botón Limpiar */}
          {tieneFiltroActivo && (
            <Button
              variant="outline"
              size="sm"
              onClick={onLimpiar}
              className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400"
              startIcon={<RotateCcw className="h-3.5 w-3.5" />}
            >
              Limpiar
            </Button>
          )}

          {/* Badge informativo de conteo */}
          {showCounts && totalRegistros !== undefined && (
            <div className="px-2.5 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-900 border border-gray-200/60 dark:border-gray-800 text-[11px] font-medium text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
              <CalendarDays className="h-3.5 w-3.5 text-brand-500" />
              <span>
                {tieneFiltroActivo && registrosFiltrados !== undefined ? (
                  <>
                    <strong className="text-gray-900 dark:text-white">{registrosFiltrados}</strong> de {totalRegistros}
                  </>
                ) : (
                  <>
                    Total: <strong className="text-gray-900 dark:text-white">{totalRegistros}</strong>
                  </>
                )}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
