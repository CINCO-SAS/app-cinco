// src/modules/transporte/informes/components/InformeDiaADia.tsx
//
// Bloque "Día a Día" (Paso 5 del plan): el informe mensual F5-3
// (`GET /informes/mensual/`) como listado de salidas ordenado día a día.
//
// Es una tabla de DETALLE, no un agregado: cada fila es una salida con las
// columnas de la sábana — las mismas del export F5-4, con quién sale
// (nombre + cédula) y la novedad (tipo + valor) en una sola celda, más el
// centro de costos B11. Por eso se apoya en el `DataTable` compartido con
// paginación server-side (`manualPagination`), y por eso NO se le pasa
// `globalFilterValue` ni `sortingValue`: el que filtra, pagina y ordena es
// el servidor, y rehacer esas operaciones sobre la página visible engañaría
// (el total no cuadraría con lo que se ve). Mismo criterio documentado en
// `SalidasTable`.
//
// Los filtros de este bloque son PROPIOS (estado/área/carpeta/sede y
// búsqueda), no los de la barra global: la barra global cambia el PERIODO
// de toda la pantalla, estos afinan dentro del mes.

import type { ReactNode } from "react";
import { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { BadgeEstadoSalida } from "../../components/EstadoSalidaBadge";
import {
  ESTADOS_SALIDA,
  type Salida,
} from "@/types/transporte.types";
import { ETIQUETAS_ESTADO } from "../../operacion/salidas/salidasView.utils";
import { BOTON_CLASES, SELECT_CLASES } from "./InformeToolbar";
import {
  DIA_A_DIA_POR_PAGINA,
  useInformeDiaADia,
} from "../informeDiaADia.hooks";
import { etiquetaFecha, formatoCOP } from "../informesView.utils";

const CLASE_NUMERO =
  "whitespace-nowrap text-sm tabular-nums text-gray-700 dark:text-gray-300";

const CLASE_TEXTO = "text-sm text-gray-600 dark:text-gray-400";

/** `null`/vacío de `Salida` (área, carpeta, sede) → raya, no celda hueca. */
const Raya = () => <span className="text-gray-400">—</span>;

const COLUMNAS: ColumnDef<Salida, unknown>[] = [
  {
    id: "fecha_salida",
    accessorKey: "fecha_salida",
    header: "DÍA",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMERO} whitespace-nowrap`}>
        {etiquetaFecha(row.original.fecha_salida)}
      </span>
    ),
  },
  {
    id: "vehiculo_placa",
    accessorKey: "vehiculo_placa",
    header: "PLACA",
    cell: ({ row }) => (
      <span className="text-sm font-medium text-gray-800 dark:text-white/90">
        {row.original.vehiculo_placa}
      </span>
    ),
  },
  {
    // Legacy `movil_sale`: quién sale (o la sentinela 'disponible', que aquí
    // ya es el flag `es_disponible` y no texto).
    id: "quien_sale",
    header: "QUIÉN SALE",
    enableSorting: false,
    cell: ({ row }) => {
      const { conductor_detalle, es_disponible } = row.original;
      if (es_disponible) {
        return <span className="text-xs text-gray-400">Disponible</span>;
      }
      if (!conductor_detalle) return <Raya />;
      return (
        <div className="flex flex-col">
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {conductor_detalle.nombre || "—"}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            CC {conductor_detalle.cedula}
          </span>
        </div>
      );
    },
  },
  {
    id: "area",
    accessorKey: "area",
    header: "ÁREA",
    cell: ({ row }) => (
      <span className={CLASE_TEXTO}>{row.original.area || <Raya />}</span>
    ),
  },
  {
    id: "carpeta",
    accessorKey: "carpeta",
    header: "CARPETA",
    cell: ({ row }) => (
      <span className={CLASE_TEXTO}>{row.original.carpeta || <Raya />}</span>
    ),
  },
  {
    // B11: centro de costos resuelto EN SERVIDOR (carpeta + área) con
    // fallback "Sin asignar" del legacy.
    id: "centro_costos",
    accessorKey: "centro_costos",
    header: "C. COSTOS",
    cell: ({ row }) => (
      <span className={CLASE_TEXTO}>{row.original.centro_costos || <Raya />}</span>
    ),
  },
  {
    id: "sede",
    accessorKey: "sede",
    header: "SEDE",
    cell: ({ row }) => (
      <span className={CLASE_TEXTO}>{row.original.sede || <Raya />}</span>
    ),
  },
  {
    id: "valor_dia",
    accessorKey: "valor_dia",
    header: "VALOR DÍA",
    cell: ({ row }) => (
      <span className={CLASE_NUMERO}>
        {formatoCOP(Number(row.original.valor_dia))}
      </span>
    ),
  },
  {
    id: "novedad",
    header: "NOVEDAD",
    enableSorting: false,
    cell: ({ row }) => {
      const novedad = row.original.novedad_detalle;
      if (!novedad) return <Raya />;
      return (
        <span
          title={novedad.descripcion}
          className={`${CLASE_NUMERO} text-amber-600 dark:text-amber-400/90`}
        >
          {novedad.tipo} {formatoCOP(Number(novedad.valor))}
        </span>
      );
    },
  },
  {
    id: "total_a_pagar",
    accessorKey: "total_a_pagar",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMERO} font-medium text-gray-800 dark:text-white/90`}>
        {formatoCOP(Number(row.original.total_a_pagar))}
      </span>
    ),
  },
  {
    id: "estado",
    accessorKey: "estado",
    header: "ESTADO",
    cell: ({ row }) => <BadgeEstadoSalida estado={row.original.estado} />,
  },
];

const INPUT_CLASES =
  "h-9 w-full min-w-0 rounded-lg border border-gray-300 bg-white px-2.5 text-sm " +
  "text-gray-700 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none " +
  "focus:ring-2 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 " +
  "dark:text-white/90";

const Filtro = ({
  etiqueta,
  ancho = "w-40",
  children,
}: {
  etiqueta: string;
  ancho?: string;
  children: ReactNode;
}) => (
  <label className="flex flex-col gap-1">
    <span className="text-xs text-gray-500 dark:text-gray-400">{etiqueta}</span>
    <span className={ancho}>{children}</span>
  </label>
);

interface InformeDiaADiaProps {
  /** Salida de `useInformeDiaADia`: filas, filtros y paginación server-side. */
  datos: ReturnType<typeof useInformeDiaADia>;
}

export const InformeDiaADia = ({ datos }: InformeDiaADiaProps) => {
  const {
    filas,
    total,
    isLoading,
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
    setVisibleRows,
  } = datos;

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <>
      <div className="mb-2 flex flex-wrap items-end gap-2 px-2 pt-1">
        <Filtro etiqueta="Estado">
          <select
            value={filtros.estado}
            onChange={(e) => actualizarFiltro("estado", e.target.value)}
            className={SELECT_CLASES}
            aria-label="Estado de la salida"
          >
            <option value="">Todos (sin eliminadas)</option>
            {ESTADOS_SALIDA.map((estado) => (
              <option key={estado} value={estado}>
                {ETIQUETAS_ESTADO[estado]}
              </option>
            ))}
          </select>
        </Filtro>

        <Filtro etiqueta="Área">
          <select
            value={filtros.area}
            onChange={(e) => actualizarFiltro("area", e.target.value)}
            className={SELECT_CLASES}
            aria-label="Área de la salida"
          >
            <option value="">Todas</option>
            {areas.map((area) => (
              <option key={area} value={area}>
                {area}
              </option>
            ))}
          </select>
        </Filtro>

        <Filtro etiqueta="Carpeta" ancho="w-32">
          <input
            type="text"
            value={filtros.carpeta}
            onChange={(e) => actualizarFiltro("carpeta", e.target.value)}
            placeholder="Exacta"
            className={INPUT_CLASES}
            aria-label="Carpeta de la salida"
          />
        </Filtro>

        <Filtro etiqueta="Sede" ancho="w-36">
          <input
            type="text"
            value={filtros.sede}
            onChange={(e) => actualizarFiltro("sede", e.target.value)}
            placeholder="Exacta"
            className={INPUT_CLASES}
            aria-label="Sede de la salida"
          />
        </Filtro>

        <Filtro etiqueta="Buscar" ancho="w-56">
          <input
            type="search"
            value={busqueda}
            onChange={(e) => cambiarBusqueda(e.target.value)}
            placeholder="Placa, cédula, nombre, área u observación"
            className={INPUT_CLASES}
            aria-label="Buscar en el informe del mes"
          />
        </Filtro>

        {hayFiltrosActivos && (
          <button
            type="button"
            onClick={limpiarFiltros}
            className={BOTON_CLASES}
            title="Quitar los filtros de este bloque"
          >
            Limpiar
          </button>
        )}

        <span className="ml-auto pb-2 text-xs text-gray-500 dark:text-gray-400">
          {total} {total === 1 ? "salida" : "salidas"} en el periodo
        </span>
      </div>

      <DataTable
        data={filas}
        columns={COLUMNAS}
        isLoading={isLoading}
        emptyMessage="No hay salidas que coincidan con los filtros."
        enablePagination
        manualPagination
        pageCount={pageCount}
        pageSize={DIA_A_DIA_POR_PAGINA}
        pageSizeOptions={[25, 50, 100]}
        pageIndexValue={pageIndex}
        pageSizeValue={pageSize}
        onPageChange={setPageIndex}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPageIndex(0);
        }}
        onVisibleDataChange={setVisibleRows}
      />
    </>
  );
};
