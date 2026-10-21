// src/modules/transporte/flota/flotaView.tsx
//
// Vista de Flota Vehicular — T1 del módulo Transporte.
// Deliberadamente liviana: filtros en una línea + tabla.

"use client";

import { useMemo } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useFlotaData } from "./flotaView.hooks";
import { getFlotaColumns } from "./flotaView.utils";
import { FlotaTable } from "./components/FlotaTable";
import { FlotaToolbar } from "./components/FlotaToolbar";

const FlotaView = () => {
  const {
    vehiculos,
    isLoading,
    loadError,
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
  } = useFlotaData();

  const columns = useMemo(() => getFlotaColumns(), []);

  const toolbarActions = (
    <FlotaToolbar
      total={vehiculos.length}
      filtros={filtros}
      actualizarFiltro={actualizarFiltro}
      limpiarFiltros={limpiarFiltros}
      hayFiltrosActivos={hayFiltrosActivos}
    />
  );

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb pageTitle={["Transporte", "Maestros", "Flota Vehicular"]} />

      {loadError && (
        <div className="mb-4">
          <Alert
            variant="error"
            title="Error al cargar la flota"
            message={loadError}
          />
        </div>
      )}

      <FlotaTable
        vehiculos={vehiculos}
        columns={columns}
        isLoading={isLoading}
        globalFilter={globalFilter}
        setGlobalFilter={setGlobalFilter}
        sorting={sorting}
        setSorting={setSorting}
        pageIndex={pageIndex}
        setPageIndex={setPageIndex}
        pageSize={pageSize}
        setPageSize={setPageSize}
        visibleRows={visibleRows}
        setVisibleRows={setVisibleRows}
        toolbarActions={toolbarActions}
      />
    </div>
  );
};

export default FlotaView;
