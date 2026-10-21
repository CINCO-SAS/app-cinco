// src/modules/transporte/operacion/reporte-fotografico/reporteFotoView.hooks.ts
//
// Estado de la vista de Reporte Fotográfico (F3/B3).
//
// Misma gramática que Salidas: filtros y paginación SERVER-SIDE. No se sabe
// cuántos reportes va a acumular la tabla (reporte diario × vehículo ×
// técnico), así que quien pagina y filtra es el servidor
// (`ReporteFotograficoService.listar`).
//
// La búsqueda además viaja diferida (300 ms) por la misma razón que en
// Salidas: cada tecla es un `GET` + `COUNT(*)`.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useTableUrlState } from "@/hooks/useTableUrlState";
import { useDebounce } from "@/hooks/useDebounce";
import { transporteService } from "@/services/transporte.service";
import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import type { ReporteFotografico } from "@/types/transporte.types";

export const REPORTES_TABLE_CONFIG = {
  defaultPageSize: 25,
  defaultPageIndex: 0,
} as const;

export interface FiltrosReporteFoto {
  /** `YYYY-MM-DD` o vacío = sin límite. */
  desde: string;
  hasta: string;
  /** Placa o pk del vehículo. */
  vehiculo: string;
}

const FILTROS_INICIALES: FiltrosReporteFoto = {
  desde: "",
  hasta: "",
  vehiculo: "",
};

export const useReporteFotoData = () => {
  const [reportes, setReportes] = useState<ReporteFotografico[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filtros, setFiltros] = useState<FiltrosReporteFoto>(FILTROS_INICIALES);
  const [visibleRows, setVisibleRows] = useState<ReporteFotografico[]>([]);

  const {
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  } = useTableUrlState({
    defaultPageSize: REPORTES_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: REPORTES_TABLE_CONFIG.defaultPageIndex,
  });

  const busqueda = useDebounce(globalFilter, 300);

  // N.º de petición en curso: si una respuesta vieja llega después de un
  // cambio de filtro, se descarta en vez de pintar filas que ya no aplican.
  const solicitudRef = useRef(0);

  const cargar = useCallback(async () => {
    const solicitud = solicitudRef.current + 1;
    solicitudRef.current = solicitud;

    setIsLoading(true);
    setLoadError(null);
    try {
      const respuesta = await transporteService.getReportesPaginado({
        page: pageIndex + 1,
        page_size: pageSize,
        desde: filtros.desde || undefined,
        hasta: filtros.hasta || undefined,
        vehiculo: filtros.vehiculo || undefined,
        search: (busqueda ?? "").trim() || undefined,
      });

      if (solicitud !== solicitudRef.current) return;

      // Auto-healing: al afinar un filtro desde una página profunda el
      // servidor puede devolver 0 filas con total > 0.
      if (respuesta.results.length === 0 && pageIndex > 0) {
        setPageIndex(0);
        return;
      }

      setReportes(respuesta.results);
      setTotal(respuesta.count);
    } catch (error) {
      if (solicitud !== solicitudRef.current) return;
      const apiError = error as ApiError;
      setLoadError(
        apiError?.message ?? "No fue posible cargar los reportes.",
      );
      logDevelopmentError("Error cargando reportes fotográficos:", error);
    } finally {
      if (solicitud === solicitudRef.current) {
        setIsLoading(false);
      }
    }
  }, [pageIndex, pageSize, filtros, busqueda, setPageIndex]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  /** Re-pide la MISMA página — tras guardar un reporte nuevo. */
  const recargar = useCallback(() => {
    void cargar();
  }, [cargar]);

  const actualizarFiltro = useCallback(
    (clave: keyof FiltrosReporteFoto, valor: string) => {
      setFiltros((prev) => ({ ...prev, [clave]: valor }));
      // Un filtro cambia el total: la página actual puede dejar de existir.
      setPageIndex(0);
    },
    [setPageIndex],
  );

  const limpiarFiltros = useCallback(() => {
    setFiltros(FILTROS_INICIALES);
    setGlobalFilter("");
    setPageIndex(0);
  }, [setGlobalFilter, setPageIndex]);

  const hayFiltrosActivos = useMemo(
    () =>
      Boolean((globalFilter ?? "").trim()) ||
      Object.values(filtros).some((valor) => valor !== ""),
    [filtros, globalFilter],
  );

  return {
    reportes,
    /** `count` real del servidor: alimenta el `pageCount`. */
    total,
    isLoading,
    loadError,
    recargar,
    filtros,
    actualizarFiltro,
    limpiarFiltros,
    hayFiltrosActivos,
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    visibleRows,
    setVisibleRows,
  };
};
