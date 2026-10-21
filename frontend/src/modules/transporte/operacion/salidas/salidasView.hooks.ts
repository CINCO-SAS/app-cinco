// src/modules/transporte/operacion/salidas/salidasView.hooks.ts
//
// Estado de la vista de Salidas: filtros y paginación SERVER-SIDE.
//
// Diferencia clave frente a Conductores/Flota: aquí NO se trae el catálogo
// completo para filtrar en el cliente. `transporte_salida` tiene ~253 mil
// filas, así que quien pagina, filtra y busca es el servidor
// (`SalidaService.listar`) y cada cambio relevante es una petición nueva.
//
// El orden NO se envía: el backend siempre devuelve `fecha_salida desc, id desc`
// y no expone `?ordering=`. Por eso la tabla se renderiza con el ordenamiento
// apagado — ordenar solo la página visible engañaría (el TOTAL no cuadraría).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useTableUrlState } from "@/hooks/useTableUrlState";
import { useDebounce } from "@/hooks/useDebounce";
import { transporteService } from "@/services/transporte.service";
import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import type { Salida } from "@/types/transporte.types";
import { SALIDAS_TABLE_CONFIG } from "./salidasView.utils";

/** Filtros de negocio del toolbar (B1). Todos son parámetros del servidor. */
export interface FiltrosSalidas {
  /** `YYYY-MM-DD` o vacío = sin límite inferior. */
  desde: string;
  /** `YYYY-MM-DD` o vacío = sin límite superior. */
  hasta: string;
  /** Vacío = el servidor excluye ELIMINADO; ver `listar()`. */
  estado: string;
  area: string;
  /** Placa (el backend acepta placa o pk de vehículo). */
  vehiculo: string;
}

const FILTROS_INICIALES: FiltrosSalidas = {
  desde: "",
  hasta: "",
  estado: "",
  area: "",
  vehiculo: "",
};

export const useSalidasData = () => {
  const [salidas, setSalidas] = useState<Salida[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [filtros, setFiltros] = useState<FiltrosSalidas>(FILTROS_INICIALES);
  const [visibleRows, setVisibleRows] = useState<Salida[]>([]);

  // `q` de la URL = la búsqueda `?search=` del servidor (placa, cédula,
  // nombre, área u observación). Así compartir un enlace conserva la búsqueda.
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
    defaultPageSize: SALIDAS_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: SALIDAS_TABLE_CONFIG.defaultPageIndex,
  });

  // `globalFilter` (el texto del input y `?q=` de la URL) se escribe al
  // instante; al SERVIDOR solo viaja cuando hace 300 ms que no se teclea.
  // Así no hay un `GET` + `COUNT(*)` por cada tecla.
  const busqueda = useDebounce(globalFilter, 300);

  // N.º de petición en curso: si llega una respuesta vieja (cambió el filtro
  // a mitad de vuelo) se descarta en vez de pintar filas que ya no aplican.
  const solicitudRef = useRef(0);

  const cargar = useCallback(async () => {
    const solicitud = solicitudRef.current + 1;
    solicitudRef.current = solicitud;

    setIsLoading(true);
    setLoadError(null);
    try {
      const respuesta = await transporteService.getSalidasPaginado({
        page: pageIndex + 1,
        page_size: pageSize,
        desde: filtros.desde || undefined,
        hasta: filtros.hasta || undefined,
        estado: filtros.estado || undefined,
        area: filtros.area || undefined,
        vehiculo: filtros.vehiculo || undefined,
        search: (busqueda ?? "").trim() || undefined,
      });

      // Respuesta obsoleta: otra ya la reemplazó.
      if (solicitud !== solicitudRef.current) return;

      // Caseta de seguridad: al afinar un filtro desde una página profunda el
      // servidor puede devolver 0 filas con total > 0. En vez de dejar la
      // tabla en blanco, se vuelve a la primera página (auto-healing).
      if (respuesta.results.length === 0 && pageIndex > 0) {
        setPageIndex(0);
        return;
      }

      setSalidas(respuesta.results);
      setTotal(respuesta.count);
    } catch (error) {
      if (solicitud !== solicitudRef.current) return;
      const apiError = error as ApiError;
      setLoadError(
        apiError?.message ?? "No fue posible cargar las salidas.",
      );
      logDevelopmentError("Error cargando salidas:", error);
    } finally {
      if (solicitud === solicitudRef.current) {
        setIsLoading(false);
      }
    }
  }, [pageIndex, pageSize, filtros, busqueda, setPageIndex]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  /** Vuelve a pedir la MISMA página/página 1 — tras alta o acción de fila. */
  const recargar = useCallback(() => {
    void cargar();
  }, [cargar]);

  const actualizarFiltro = useCallback(
    (clave: keyof FiltrosSalidas, valor: string) => {
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
    salidas,
    /** `count` real del servidor: alimenta el `pageCount` del DataTable. */
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
