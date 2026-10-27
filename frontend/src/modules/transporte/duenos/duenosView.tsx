// src/modules/transporte/duenos/duenosView.tsx
//
// Vista principal del módulo Dueños de Vehículos (F2 · 2026-10-26):
// Catálogo de propietarios, asignación de múltiples vehículos (1 Dueño → N Vehículos)
// y administración de cuentas bancarias asociadas para liquidación.

"use client";

import { useCallback, useMemo, useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useDuenosData } from "./duenosView.hooks";
import { getDuenosColumns } from "./duenosView.utils";
import { DuenosTable } from "./components/DuenosTable";
import { DuenosToolbar } from "./components/DuenosToolbar";
import { DuenoFormModal } from "./components/DuenoFormModal";
import { DuenoFichaModal } from "./components/DuenoFichaModal";
import type { DuenoResumen } from "@/types/transporte.types";

const DuenosView = () => {
  const {
    duenos,
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
  } = useDuenosData();

 

  // Modales
  // `null` → cerrado, `0` → alta, `number` → edición básica
  const [duenoEnEdicion, setDuenoEnEdicion] = useState<number | null>(null);
  // Ficha completa (vehículos + bancarios)
  const [duenoEnFicha, setDuenoEnFicha] = useState<number | null>(null);
  const [fichaTabInicial, setFichaTabInicial] = useState<"vehiculos" | "bancarios">("vehiculos");
  const [fichaAutoAgregarCuenta, setFichaAutoAgregarCuenta] = useState(false);

  const onNuevo = useCallback(() => setDuenoEnEdicion(0), []);
  const onEditar = useCallback((dueno: DuenoResumen) => {
    setDuenoEnEdicion(dueno.id);
  }, []);
  const onVerFicha = useCallback((dueno: DuenoResumen) => {
    setFichaTabInicial("vehiculos");
    setFichaAutoAgregarCuenta(false);
    setDuenoEnFicha(dueno.id);
  }, []);
  const onAgregarCuenta = useCallback((dueno: DuenoResumen) => {
    setFichaTabInicial("bancarios");
    setFichaAutoAgregarCuenta(true);
    setDuenoEnFicha(dueno.id);
  }, []);

  const columns = useMemo(
    () => getDuenosColumns({ onVerFicha, onAgregarCuenta }),
    [onVerFicha, onAgregarCuenta],
  );

  const cerrarFormulario = useCallback(() => setDuenoEnEdicion(null), []);
  const cerrarFicha = useCallback(() => {
    setDuenoEnFicha(null);
    setFichaAutoAgregarCuenta(false);
  }, []);

  const toolbarActions = (
    <DuenosToolbar
      total={duenos.length}
      filtros={filtros}
      actualizarFiltro={actualizarFiltro}
      limpiarFiltros={limpiarFiltros}
      hayFiltrosActivos={hayFiltrosActivos}
      onNuevo={onNuevo}
    />
  );

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6 space-y-6">
      <PageBreadcrumb
        pageTitle={["Transporte", "Maestros", "Dueños de Vehículos"]}
      />

      {loadError && (
        <Alert
          variant="error"
          title="Error al cargar los dueños de vehículos"
          message={loadError}
        />
      )}

      {/* Banner explicativo del módulo */}
      <div className="rounded-xl border border-gray-200 bg-gradient-to-r from-gray-50 to-white p-4 dark:border-gray-800 dark:from-gray-900 dark:to-gray-850">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-500 dark:bg-brand-500/15">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          </span>
          <div className="text-sm">
            <p className="font-semibold text-gray-800 dark:text-white/90">
              Gestión Integral de Dueños, Flota Asignada y Datos Bancarios
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">
              Permite asociar múltiples vehículos a un mismo propietario (1 Dueño → N Vehículos) y configurar las cuentas bancarias para el giro de liquidaciones financieras.
            </p>
          </div>
        </div>
      </div>

      <DuenosTable
        duenos={duenos}
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
        onVerFicha={onVerFicha}
        onEditar={onEditar}
      />

      {/* Modal para crear o editar datos básicos del dueño */}
      <DuenoFormModal
        isOpen={duenoEnEdicion !== null}
        duenoId={duenoEnEdicion === 0 ? null : duenoEnEdicion}
        onClose={cerrarFormulario}
        onGuardado={recargar}
      />

      {/* Modal interactivo de Ficha: Asignación de vehículos (1 a N) y cuentas bancarias */}
      <DuenoFichaModal
        isOpen={duenoEnFicha !== null}
        duenoId={duenoEnFicha}
        tabInicial={fichaTabInicial}
        autoAgregarCuenta={fichaAutoAgregarCuenta}
        onClose={cerrarFicha}
        onActualizado={recargar}
      />
    </div>
  );
};

export default DuenosView;
