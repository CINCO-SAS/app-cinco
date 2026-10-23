// src/modules/transporte/informes/informeDiaADia.hooks.ts
//
// Estado del bloque "Día a Día" (Paso 5 del plan): el informe mensual F5-3
// (`GET /informes/mensual/`) pintado como listado.
//
// POR QUÉ AQUÍ NO HAY FILTRO EN LA URL: en la pantalla de Salidas los
// filtros viajan en la URL (`useTableUrlState`) porque es la única tabla de
// esa ruta y compartir el enlace ahorra repetir trabajo. Aquí Informes tiene
// VARIOS bloques en la misma ruta: `?page=`/`?q=` serían ambiguos (¿de qué
// bloque?). El estado vive en el hook y se resetea al cambiar de periodo.
//
// QUIÉN FILTRA Y PAGINA: el SERVIDOR. `/informes/mensual/` ordena
// `fecha_salida asc` (día a día) y aplica `estado`, `sede`, `area`,
// `carpeta` y `search` en SQL — con ~150 mil salidas vivas no se puede traer
// el mes y filtrar en el cliente.
//
// La búsqueda se manda con 300 ms de retardo (`useDebounce`) para que no
// haya un `GET` + `COUNT(*)` por cada tecla.

import { useCallback, useEffect, useRef, useState } from "react";

import { useDebounce } from "@/hooks/useDebounce";
import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { Salida } from "@/types/transporte.types";

/** Filas por página (mismo tamaño por defecto que la tabla de Salidas). */
export const DIA_A_DIA_POR_PAGINA = 25;

/**
 * Filtros server-side del bloque. Todos son parámetros de
 * `InformeService.mensual`; vacío = sin filtro.
 */
export interface FiltrosDiaADia {
  /** Vacío = el servidor excluye ELIMINADO (informe = lo vigente). */
  estado: string;
  area: string;
  /** El backend la compara exacta (`iexact`), no por prefijo. */
  carpeta: string;
  /** Igual que carpeta: coincidencia exacta. */
  sede: string;
}

const FILTROS_VACIOS: FiltrosDiaADia = {
  estado: "",
  area: "",
  carpeta: "",
  sede: "",
};

/** Referencia estable para "aún no hay áreas" (ver informesView.tsx). */
const AREAS_VACIAS: string[] = [];

export const useInformeDiaADia = (mes: number, anio: number, tick: number) => {
  const [filas, setFilas] = useState<Salida[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Áreas del periodo para el `<select>` (`GET /informes/areas/`).
  const [areas, setAreas] = useState<string[]>(AREAS_VACIAS);

  const [filtros, setFiltros] = useState<FiltrosDiaADia>(FILTROS_VACIOS);
  const [busqueda, setBusqueda] = useState("");
  const busquedaDiferida = useDebounce(busqueda, 300);

  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(DIA_A_DIA_POR_PAGINA);

  // Lo que el DataTable renderiza (páginas de 25 en 25 que TanStack deja
  // pasar ya cortadas, igual que en Salidas).
  const [visibleRows, setVisibleRows] = useState<Salida[]>([]);

  const peticionFilas = useRef(0);
  const peticionAreas = useRef(0);

  // -------------------------------------------------------------------------
  // Cambio de periodo: los filtros del mes anterior no significan nada en el
  // nuevo (un área que ya no tiene salidas, una carpeta inexistente), así que
  // se limpian en vez de dejar una consulta muerta seleccionada.
  // -------------------------------------------------------------------------
  const periodo = `${anio}-${mes}`;
  const periodoPrevio = useRef(periodo);
  useEffect(() => {
    if (periodoPrevio.current === periodo) return;
    periodoPrevio.current = periodo;
    setFiltros(FILTROS_VACIOS);
    setBusqueda("");
    setPageIndex(0);
  }, [periodo]);

  const cargarFilas = useCallback(async () => {
    const peticion = ++peticionFilas.current;
    const esVigente = () => peticion === peticionFilas.current;

    setIsLoading(true);
    setError(null);
    try {
      const respuesta = await transporteService.getInformeMensual({
        mes,
        anio,
        page: pageIndex + 1,
        page_size: pageSize,
        estado: filtros.estado || undefined,
        area: filtros.area || undefined,
        carpeta: filtros.carpeta || undefined,
        sede: filtros.sede || undefined,
        search: busquedaDiferida.trim() || undefined,
      });

      if (!esVigente()) return;

      // Caseta de seguridad: al afinar un filtro desde una página profunda
      // el servidor puede devolver 0 filas con total > 0. En vez de dejar la
      // tabla en blanco se vuelve a la primera página (auto-healing, mismo
      // criterio que la pantalla de Salidas).
      if (respuesta.results.length === 0 && pageIndex > 0) {
        setPageIndex(0);
        return;
      }

      setFilas(respuesta.results);
      setTotal(respuesta.count);
    } catch (err) {
      if (!esVigente()) return;
      const apiError = err as ApiError;
      setError(apiError?.message ?? "No fue posible cargar el informe día a día.");
      logDevelopmentError("Error cargando el informe mensual:", err);
    } finally {
      if (esVigente()) setIsLoading(false);
    }
  }, [mes, anio, filtros, busquedaDiferida, pageIndex, pageSize]);

  const cargarAreas = useCallback(async () => {
    const peticion = ++peticionAreas.current;
    const esVigente = () => peticion === peticionAreas.current;
    try {
      const respuesta = await transporteService.getInformeAreas({ mes, anio });
      if (!esVigente()) return;
      setAreas(respuesta.areas);
    } catch (err) {
      if (!esVigente()) return;
      // Sin el catálogo de áreas el select queda solo con "Todas": es una
      // degradación aceptable, no un fallo del bloque entero.
      setAreas(AREAS_VACIAS);
      logDevelopmentError("Error cargando las áreas del periodo:", err);
    }
  }, [mes, anio]);

  useEffect(() => {
    void cargarFilas();
  }, [cargarFilas]);

  useEffect(() => {
    void cargarAreas();
  }, [cargarAreas]);

  // ↻ de la barra global: cuando `tick` cambia las dos cargas se repiten
  // sin duplicar sus callbacks. El comparador evita la carga doble del
  // primer montaje (las cargas de arriba ya se encargan de eso).
  const tickPrevio = useRef(tick);
  useEffect(() => {
    if (tickPrevio.current === tick) return;
    tickPrevio.current = tick;
    void cargarFilas();
    void cargarAreas();
  }, [tick, cargarFilas, cargarAreas]);

  const actualizarFiltro = useCallback(
    (clave: keyof FiltrosDiaADia, valor: string) => {
      setFiltros((previo) => ({ ...previo, [clave]: valor }));
      // Un filtro cambia el total: la página actual puede dejar de existir.
      setPageIndex(0);
    },
    [],
  );

  const cambiarBusqueda = useCallback((valor: string) => {
    setBusqueda(valor);
    setPageIndex(0);
  }, []);

  const limpiarFiltros = useCallback(() => {
    setFiltros(FILTROS_VACIOS);
    setBusqueda("");
    setPageIndex(0);
  }, []);

  const hayFiltrosActivos =
    Boolean(busqueda.trim()) ||
    Object.values(filtros).some((valor) => valor !== "");

  return {
    /** SOLO la página actual, tal como la devolvió el servidor. */
    filas,
    /** `count` real del filtro → alimenta el paginador. */
    total,
    isLoading,
    error,
    /** Áreas del periodo para el filtro. */
    areas,
    filtros,
    actualizarFiltro,
    busqueda,
    cambiarBusqueda,
    limpiarFiltros,
    hayFiltrosActivos,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    visibleRows,
    setVisibleRows,
  };
};
