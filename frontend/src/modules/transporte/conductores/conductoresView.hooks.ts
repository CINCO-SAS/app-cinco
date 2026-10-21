// src/modules/transporte/conductores/conductoresView.hooks.ts
//
// Estado de la vista de Conductores: carga del catálogo, filtros de negocio y
// estado de la tabla sincronizado con la URL.
//
// El catálogo se trae COMPLETO (`obtenerTodasLasPaginas`) y se filtra en el
// cliente: son cientos de filas, no decenas de miles como en salidas, y así
// los filtros responden al instante sin round-trips.

import { useCallback, useEffect, useMemo, useState } from "react";

import { useTableUrlState } from "@/hooks/useTableUrlState";
import { transporteService } from "@/services/transporte.service";
import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import type { ConductorListado } from "@/types/transporte.types";
import { CONDUCTORES_TABLE_CONFIG } from "./conductoresView.utils";

/** Filtros de negocio del toolbar (no de la tabla). */
export interface FiltrosConductores {
  tipo_vinculacion: string;
  activo: string;
  /** Filtra por semáforo de licencia: 'VENCIDA' muestra solo licencias vencidas. */
  vigencia: string;
}

const FILTROS_INICIALES: FiltrosConductores = {
  tipo_vinculacion: "",
  activo: "",
  vigencia: "",
};

export const useConductoresData = () => {
  const [conductores, setConductores] = useState<ConductorListado[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filtros, setFiltros] = useState<FiltrosConductores>(
    FILTROS_INICIALES,
  );
  const [visibleRows, setVisibleRows] = useState<ConductorListado[]>([]);

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
    defaultPageSize: CONDUCTORES_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: CONDUCTORES_TABLE_CONFIG.defaultPageIndex,
  });

  // -------------------------------------------------------------------------
  // Carga. Sin dependencias de filtros: el filtrado ocurre en el cliente.
  // -------------------------------------------------------------------------
  const cargar = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const datos = await transporteService.getConductores();
      setConductores(datos);
    } catch (error) {
      const apiError = error as ApiError;
      setLoadError(
        apiError?.message ?? "No fue posible cargar el catálogo de conductores.",
      );
      logDevelopmentError("Error cargando conductores:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // -------------------------------------------------------------------------
  // Filtros de negocio + búsqueda global, aplicados al cliente.
  // -------------------------------------------------------------------------
  const conductoresFiltrados = useMemo(() => {
    const texto = (globalFilter ?? "").trim().toLowerCase();

    return conductores.filter((conductor) => {
      if (
        filtros.tipo_vinculacion &&
        conductor.tipo_vinculacion !== filtros.tipo_vinculacion
      ) {
        return false;
      }
      if (filtros.activo !== "") {
        const esperado = filtros.activo === "true";
        if (conductor.activo !== esperado) return false;
      }
      if (filtros.vigencia && conductor.estado_licencia !== filtros.vigencia) {
        return false;
      }
      if (!texto) return true;

      const campos = [conductor.cedula, conductor.nombre_completo, conductor.celular];
      return campos.some((campo) => campo.toLowerCase().includes(texto));
    });
  }, [conductores, filtros, globalFilter]);

  const actualizarFiltro = useCallback(
    (clave: keyof FiltrosConductores, valor: string) => {
      setFiltros((prev) => ({ ...prev, [clave]: valor }));
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
      Boolean(globalFilter) ||
      Object.values(filtros).some((valor) => valor !== ""),
    [filtros, globalFilter],
  );

  return {
    conductores: conductoresFiltrados,
    conductoresSinFiltrar: conductores,
    totalConductores: conductores.length,
    isLoading,
    loadError,
    recargar: cargar,
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
