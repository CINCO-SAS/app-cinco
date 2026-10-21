// src/lib/paginas.ts
//
// Utilidades REUTILIZABLES para consumir endpoints paginados de DRF
// (`{count, next, previous, results}`). Cualquier módulo puede importarlas.
//
// Por qué existe: `PaginacionTransporte` (backend) trae 50 filas por página
// por defecto. Los catálogos que el front filtra EN CLIENTE (flota ~1.300
// vehículos, conductores) deben pedir todas las páginas; si no, la tabla
// mostraría "en silencio" solo la primera página con datos reales.

import api from "@/lib/api";

/** Estructura canónica de DRF al usar `pagination_class`. */
export interface RespuestaPaginada<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ParamsConsulta = Record<
  string,
  string | number | boolean | undefined
>;

/**
 * DRF devuelve `[...]` o `{count, results}` según `pagination_class`.
 * Normalizamos para que los consumidores siempre reciban `{results}`.
 */
export const normalizarPagina = <T>(data: unknown): RespuestaPaginada<T> => {
  if (Array.isArray(data)) {
    return {
      count: data.length,
      next: null,
      previous: null,
      results: data as T[],
    };
  }
  const envuelto = data as Partial<RespuestaPaginada<T>>;
  return {
    count: envuelto.count ?? envuelto.results?.length ?? 0,
    next: envuelto.next ?? null,
    previous: envuelto.previous ?? null,
    results: envuelto.results ?? [],
  };
};

/** `page_size` máximo que admite `PaginacionTransporte.max_page_size`. */
const POR_PAGINA = 1000;

/** Cortafuegos: nunca dar más vueltas que esta (ruido de red o API rota). */
const MAXIMO_VUELTAS = 100;

/**
 * Recorre todas las páginas de un listado DRF y devuelve el arreglo COMPLETO.
 *
 * Usa `?page=&page_size=` explícitos en lugar de seguir `next` (URL absoluta):
 * así funciona igual detrás de un proxy o con otro host.
 *
 * Si el endpoint NO está paginado (devuelve `[...]`), se queda en una vuelta.
 */
export const obtenerTodasLasPaginas = async <T>(
  url: string,
  params?: ParamsConsulta,
): Promise<T[]> => {
  const filas: T[] = [];

  for (let page = 1; page <= MAXIMO_VUELTAS; page++) {
    const res = await api.get(url, {
      params: { ...params, page, page_size: POR_PAGINA },
    });
    const pagina = normalizarPagina<T>(res.data);

    if (pagina.results.length === 0) break;
    filas.push(...pagina.results);
    if (filas.length >= pagina.count) break;
  }

  return filas;
};
