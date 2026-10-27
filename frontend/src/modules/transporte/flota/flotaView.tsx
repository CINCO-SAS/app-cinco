// src/modules/transporte/flota/flotaView.tsx
//
// Vista de Flota Vehicular — T1 del módulo Transporte.
// Deliberadamente liviana: filtros en una línea + tabla.

"use client";

import { useCallback, useMemo, useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useFlotaData } from "./flotaView.hooks";
import { getFlotaColumns } from "./flotaView.utils";
import { FlotaKpis } from "./components/FlotaKpis";
import { FlotaTable } from "./components/FlotaTable";
import { FlotaToolbar } from "./components/FlotaToolbar";
import { VehiculoFormModal } from "./components/VehiculoFormModal";
import { VehiculoInactivarModal } from "./components/VehiculoInactivarModal";
import type { VehiculoListado } from "@/types/transporte.types";

const FlotaView = () => {
  const {
    vehiculos,
    resumen,
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
  } = useFlotaData();

  const columns = useMemo(() => getFlotaColumns(), []);

  // `null` → modal cerrado; `number` → id del vehículo a editar; `0` → alta.
  const [vehiculoEnEdicion, setVehiculoEnEdicion] = useState<number | null>(null);
  const [vehiculoAInactivar, setVehiculoAInactivar] =
    useState<VehiculoListado | null>(null);

  const cerrarFormulario = useCallback(() => setVehiculoEnEdicion(null), []);
  const onNuevo = useCallback(() => setVehiculoEnEdicion(0), []);
  const onEditar = useCallback((vehiculo: VehiculoListado) => {
    setVehiculoEnEdicion(vehiculo.id);
  }, []);
  const onInactivar = useCallback((vehiculo: VehiculoListado) => {
    setVehiculoAInactivar(vehiculo);
  }, []);

  const toolbarActions = (
    <FlotaToolbar
      total={vehiculos.length}
      filtros={filtros}
      actualizarFiltro={actualizarFiltro}
      limpiarFiltros={limpiarFiltros}
      hayFiltrosActivos={hayFiltrosActivos}
      onNuevo={onNuevo}
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

      <FlotaKpis resumen={resumen} />

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
        onEditar={onEditar}
        onInactivar={onInactivar}
      />

      <VehiculoFormModal
        isOpen={vehiculoEnEdicion !== null}
        vehiculoId={vehiculoEnEdicion === 0 ? null : vehiculoEnEdicion}
        onClose={cerrarFormulario}
        onGuardado={recargar}
      />

      <VehiculoInactivarModal
        vehiculo={vehiculoAInactivar}
        onClose={() => setVehiculoAInactivar(null)}
        onInactivado={recargar}
      />
    </div>
  );
};

export default FlotaView;
