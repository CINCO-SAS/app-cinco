// src/modules/transporte/duenos/duenosView.hooks.ts
//
// Estado de la vista de Dueños de Vehículos: carga de datos, filtros y tabla.

import { useCallback, useEffect, useMemo, useState } from "react";

import { useTableUrlState } from "@/hooks/useTableUrlState";
import { transporteService } from "@/services/transporte.service";
import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import type { DuenoResumen } from "@/types/transporte.types";
import { DUENOS_TABLE_CONFIG } from "./duenosView.utils";

export interface FiltrosDuenos {
  activo: string;
}

const FILTROS_INICIALES: FiltrosDuenos = {
  activo: "",
};

export const useDuenosData = () => {
  const [duenos, setDuenos] = useState<DuenoResumen[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filtros, setFiltros] = useState<FiltrosDuenos>(FILTROS_INICIALES);
  const [visibleRows, setVisibleRows] = useState<DuenoResumen[]>([]);

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
    defaultPageSize: DUENOS_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: DUENOS_TABLE_CONFIG.defaultPageIndex,
  });

  const cargar = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const datos = await transporteService.getDuenos();
      setDuenos(datos);
    } catch (error) {
      const apiError = error as ApiError;
      setLoadError(
        apiError?.message ?? "No fue posible cargar los dueños de vehículos.",
      );
      logDevelopmentError("Error cargando dueños:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const duenosFiltrados = useMemo(() => {
    const texto = (globalFilter ?? "").trim().toLowerCase();

    return duenos.filter((d) => {
      if (filtros.activo !== "") {
        const esperado = filtros.activo === "true";
        if (d.activo !== esperado) return false;
      }

      if (!texto) return true;

      const campos = [
        d.cedula,
        d.nombre,
        d.celular ?? "",
      ];
      return campos.some((campo) => campo.toLowerCase().includes(texto));
    });
  }, [duenos, filtros, globalFilter]);

  const actualizarFiltro = useCallback(
    (clave: keyof FiltrosDuenos, valor: string) => {
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
    duenos: duenosFiltrados,
    totalDuenos: duenos.length,
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
