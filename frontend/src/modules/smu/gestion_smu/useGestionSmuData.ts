// src/modules/smu/gestion_smu/useGestionSmuData.ts
//
// Carga del historial SMU (`GET /smu/actividades/`) y estado de la tabla:
// búsqueda global, filtros de cabecera, orden y paginación vía URL.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTableUrlState } from "@/hooks/useTableUrlState";
import { classifyError, getToastErrorMessage } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import {
  listarActividadesSMU,
  type ActividadSmuResumen,
  type FiltrosActividadSmu,
} from "@/services/smu.service";
import { GESTION_SMU_CONFIG } from "./constants";

/** Texto sin tildes ni mayúsculas, para comparar la búsqueda con las filas. */
const normalizar = (valor: string): string =>
  valor
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();

/** Columnas que barre la búsqueda global de la tabla. */
const camposDeBusqueda = (fila: ActividadSmuResumen): Array<string | null> => [
  fila.codigo_ot,
  fila.tipo_formulario_display,
  fila.tipo_estacion,
  fila.nombre_estacion,
  fila.responsable_nombre,
  fila.responsable_cedula,
  fila.categoria_display,
  fila.estado_display,
];

export const useGestionSmuData = () => {
  const [actividades, setActividades] = useState<ActividadSmuResumen[]>([]);
  const [filtros, setFiltros] = useState<FiltrosActividadSmu>({});
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Correlación de respuestas: si el usuario cambia el filtro mientras una
  // petición sigue en vuelo, la respuesta vieja no pisa la nueva.
  const peticionActual = useRef(0);

  const {
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  } = useTableUrlState({ defaultPageSize: GESTION_SMU_CONFIG.defaultPageSize });

  useEffect(() => {
    const peticion = ++peticionActual.current;

    // Los `setState` viven en los callbacks de la promesa, no en el cuerpo
    // del effect: así el render no se encadena y la respuesta vieja (si el
    // usuario cambió el filtro mientras cargaba) queda descartada.
    listarActividadesSMU(filtros).then(
      (filas) => {
        if (peticion !== peticionActual.current) return;
        setActividades(filas);
        setLoadError(null);
        setIsLoading(false);
      },
      (error: unknown) => {
        if (peticion !== peticionActual.current) return;
        logDevelopmentError("Error cargando el historial SMU:", error);
        setActividades([]);
        setLoadError(
          getToastErrorMessage(
            classifyError(error),
            "No se pudo cargar el historial de formularios SMU.",
          ),
        );
        setIsLoading(false);
      },
    );
  }, [filtros]);

  /** Cambia (o limpia) un filtro de cabecera y recarga desde el servidor. */
  const cambiarFiltro = useCallback(
    (campo: keyof FiltrosActividadSmu, valor: string) => {
      setFiltros((previo) => {
        const siguiente: FiltrosActividadSmu = { ...previo };
        if (valor) {
          siguiente[campo] = valor;
        } else {
          delete siguiente[campo];
        }
        return siguiente;
      });
      // El filtro nuevo invalida la página en la que estaba el usuario.
      setPageIndex(0);
      setIsLoading(true);
    },
    [setPageIndex],
  );

  /**
   * Filas que cumplen la búsqueda global. Alimentan la tabla **y** el export,
   * para que el botón descargue lo mismo que se está viendo (no solo la
   * página actual). El filtrado de la tabla sobre este mismo texto es
   * idempotente, así que no duplica trabajo.
   */
  const filasFiltradas = useMemo(() => {
    const busqueda = normalizar(globalFilter);
    if (!busqueda) return actividades;

    return actividades.filter((fila) =>
      camposDeBusqueda(fila).some(
        (campo) => campo && normalizar(campo).includes(busqueda),
      ),
    );
  }, [actividades, globalFilter]);

  return {
    actividades,
    filasFiltradas,
    filtros,
    cambiarFiltro,
    isLoading,
    loadError,
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  };
};
