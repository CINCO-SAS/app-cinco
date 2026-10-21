// src/modules/transporte/flota/flotaView.hooks.ts
//
// Estado de la vista de Flota: carga del listado, filtros de negocio y
// estado de la tabla (paginado, orden, búsqueda) sincronizado con la URL.

import { useCallback, useEffect, useMemo, useState } from "react";

import { useTableUrlState } from "@/hooks/useTableUrlState";
import { transporteService } from "@/services/transporte.service";
import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import type { VehiculoListado } from "@/types/transporte.types";
import { FLOTA_TABLE_CONFIG } from "./flotaView.utils";

/** Filtros de negocio del toolbar (no de la tabla). */
export interface FiltrosFlota {
  tipo_contrato: string;
  activo: string;
  /** Filtra por semáforo: 'VENCIDA' muestra solo vehículos con doc vencido. */
  vigencia: string;
}

const FILTROS_INICIALES: FiltrosFlota = {
  tipo_contrato: "",
  activo: "",
  vigencia: "",
};

export const useFlotaData = () => {
  const [vehiculos, setVehiculos] = useState<VehiculoListado[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filtros, setFiltros] = useState<FiltrosFlota>(FILTROS_INICIALES);
  const [visibleRows, setVisibleRows] = useState<VehiculoListado[]>([]);

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
    defaultPageSize: FLOTA_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: FLOTA_TABLE_CONFIG.defaultPageIndex,
  });

  // -------------------------------------------------------------------------
  // Carga. Sin dependencias de filtros: el filtrado ocurre en el cliente
  // (el catálogo de flota ~1.300 filas cabe en memoria y evita round-trips).
  // -------------------------------------------------------------------------
  const cargar = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const datos = await transporteService.getVehiculos();
      setVehiculos(datos);
    } catch (error) {
      const apiError = error as ApiError;
      setLoadError(
        apiError?.message ?? "No fue posible cargar la flota vehicular.",
      );
      logDevelopmentError("Error cargando flota:", error);
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
  const vehiculosFiltrados = useMemo(() => {
    const texto = (globalFilter ?? "").trim().toLowerCase();

    return vehiculos.filter((vehiculo) => {
      if (filtros.tipo_contrato && vehiculo.tipo_contrato !== filtros.tipo_contrato) {
        return false;
      }
      if (filtros.activo !== "") {
        const esperado = filtros.activo === "true";
        if (vehiculo.activo !== esperado) return false;
      }
      if (filtros.vigencia) {
        // 'VENCIDA' = al menos un documento (SOAT o CDA) en ese estado.
        const estados = [vehiculo.estado_soat, vehiculo.estado_cda];
        if (filtros.vigencia === "AL_DIA") {
          if (!estados.every((e) => e === "VIGENTE")) return false;
        } else if (!estados.includes(filtros.vigencia as never)) {
          return false;
        }
      }
      if (!texto) return true;

      // Búsqueda global: placa, marca, referencia y conductor habitual.
      const conductor = vehiculo as unknown as {
        conductor_habitual_detalle?: { nombre_completo?: string; cedula?: string };
      };
      const campos = [
        vehiculo.placa,
        vehiculo.marca,
        vehiculo.referencia ?? "",
        String(vehiculo.modelo_anio),
        conductor.conductor_habitual_detalle?.nombre_completo ?? "",
        conductor.conductor_habitual_detalle?.cedula ?? "",
      ];
      return campos.some((campo) => campo.toLowerCase().includes(texto));
    });
  }, [vehiculos, filtros, globalFilter]);

  const actualizarFiltro = useCallback(
    (clave: keyof FiltrosFlota, valor: string) => {
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
    vehiculos: vehiculosFiltrados,
    vehiculosSinFiltrar: vehiculos,
    totalVehiculos: vehiculos.length,
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
