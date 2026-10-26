// src/modules/transporte/gestion/gestionView.tsx
//
// Vista de Gestión de Salidas / Backoffice (F4 / B4 / Tab 1 del legacy).
// Diseñada para supervisores y jefes de área:
//   - Aprobación masiva y control de transiciones de salidas (REPORTADO -> APROBADO -> VALIDADO).
//   - Gestión de rechazos con motivo obligatorio y novedades económicas.
//   - Cierre y validación mensual por área (ValidacionSalida).

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";

import { useSalidasData } from "../operacion/salidas/salidasView.hooks";
import { useSalidasAcciones } from "../operacion/salidas/salidasView.acciones";
import { getSalidasColumns } from "../operacion/salidas/salidasView.utils";
import { SalidasTable } from "../operacion/salidas/components/SalidasTable";
import {
  SalidaAprobarLoteModal,
  SalidaConfirmarModal,
  SalidaRechazarModal,
} from "../operacion/salidas/components/SalidaAccionModal";
import { SalidaNovedadModal } from "../operacion/salidas/components/SalidaNovedadModal";
import { SalidaHistorialModal } from "../operacion/salidas/components/SalidaHistorialModal";
import { useValidacionesCierre, useExportarSalidas } from "./gestionView.hooks";
import { CierreAreaModal } from "./components/CierreAreaModal";
import type { ValidacionSalida } from "@/types/transporte.types";

const CLASES_INPUT =
  "h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "placeholder:text-gray-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

export default function GestionView() {
  const [tabActivo, setTabActivo] = useState<"bandeja" | "cierres">("bandeja");

  // Hook de datos de salidas
  const {
    salidas,
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
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    setVisibleRows,
  } = useSalidasData();

  // Acciones sobre salidas (aprobar, rechazar, validar, novedad, lote)
  const acciones = useSalidasAcciones(recargar);

  // Exportador Excel / CSV
  const { exportar, exportando } = useExportarSalidas();

  // Hook de Cierres de Validación por Área
  const {
    mes: mesCierre,
    setMes: setMesCierre,
    anio: anioCierre,
    setAnio: setAnioCierre,
    validaciones,
    cargando: cargandoCierres,
    error: errorCierres,
    recargar: recargarCierres,
  } = useValidacionesCierre();

  const [modalCierreAbierto, setModalCierreAbierto] = useState<boolean>(false);

  // Limpiar selección de filas al cambiar página
  useEffect(() => {
    acciones.limpiarSeleccion();
  }, [pageIndex, pageSize, acciones.limpiarSeleccion]);

  const columns = useMemo(() => getSalidasColumns(acciones), [acciones]);

  const pageCount = useMemo(
    () => Math.max(Math.ceil(total / pageSize), 1),
    [total, pageSize],
  );

  const confirmarLote = useCallback(async (): Promise<boolean> => {
    const fallo = await acciones.aprobarLote();
    if (!fallo) acciones.cerrarDialogo();
    return fallo;
  }, [acciones]);

  const confirmarAccionSimple = useCallback(async () => {
    const fallo = await acciones.confirmarAccionSimple();
    if (!fallo) acciones.cerrarDialogo();
  }, [acciones]);

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6 space-y-6">
      {/* Encabezado y Breadcrumbs */}
      <PageBreadcrumb
        pageTitle={["Transporte", "Administración", "Gestión de Salidas"]}
      />

      {/* Selector de Pestañas */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <nav className="flex space-x-6" aria-label="Tabs">
          <button
            type="button"
            onClick={() => setTabActivo("bandeja")}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              tabActivo === "bandeja"
                ? "border-brand-500 text-brand-600 dark:text-brand-400 font-semibold"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            }`}
          >
            Bandeja de Aprobaciones y Novedades
          </button>
          <button
            type="button"
            onClick={() => setTabActivo("cierres")}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              tabActivo === "cierres"
                ? "border-brand-500 text-brand-600 dark:text-brand-400 font-semibold"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            }`}
          >
            Cierres de Validación por Área ({validaciones.length})
          </button>
        </nav>
      </div>

      {/* ============================================================== */}
      {/* PESTAÑA 1: BANDEJA DE APROBACIONES Y SALIDAS */}
      {/* ============================================================== */}
      {tabActivo === "bandeja" && (
        <div className="space-y-4">
          {loadError && (
            <Alert
              variant="error"
              title="Error al cargar las salidas"
              message={loadError}
            />
          )}

          {/* Barra de Filtros y Operaciones del Backoffice */}
          <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-theme-xs dark:border-gray-800 dark:bg-gray-850 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              {/* Pills de Filtrado Rápido por Estado */}
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: "", label: "Todos los Estados" },
                  { id: "REPORTADO", label: "Pendientes por Aprobar" },
                  { id: "APROBADO", label: "Aprobadas" },
                  { id: "VALIDADO", label: "Validadas" },
                  { id: "RECHAZADO", label: "Rechazadas" },
                ].map((item) => {
                  const activo = filtros.estado === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => actualizarFiltro("estado", item.id)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                        activo
                          ? "bg-brand-500 text-white shadow-theme-xs font-semibold"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>

              {/* Botones de Acción Masiva y Exportación */}
              <div className="flex items-center gap-2">
                {acciones.seleccionCantidad > 0 && (
                  <Button
                    id="gestion-btn-aprobar-lote"
                    variant="primary"
                    size="sm"
                    onClick={acciones.abrirLote}
                    disabled={acciones.enviando}
                  >
                    Aprobar Selección ({acciones.seleccionCantidad})
                  </Button>
                )}

                <Button
                  id="gestion-btn-exportar-xlsx"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    exportar(
                      {
                        desde: filtros.desde || undefined,
                        hasta: filtros.hasta || undefined,
                        estado: filtros.estado || undefined,
                        area: filtros.area || undefined,
                        vehiculo: filtros.vehiculo || undefined,
                      },
                      "xlsx",
                    )
                  }
                  disabled={exportando}
                >
                  {exportando ? "Exportando..." : "Descargar Excel"}
                </Button>
              </div>
            </div>

            {/* Filtros secundarios: Fechas, Área, Placa, Búsqueda */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 pt-2 border-t border-gray-100 dark:border-gray-800">
              <div>
                <label
                  htmlFor="filtro-desde"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Desde
                </label>
                <input
                  id="filtro-desde"
                  type="date"
                  value={filtros.desde}
                  onChange={(e) => actualizarFiltro("desde", e.target.value)}
                  className={`w-full ${CLASES_INPUT}`}
                />
              </div>

              <div>
                <label
                  htmlFor="filtro-hasta"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Hasta
                </label>
                <input
                  id="filtro-hasta"
                  type="date"
                  value={filtros.hasta}
                  onChange={(e) => actualizarFiltro("hasta", e.target.value)}
                  className={`w-full ${CLASES_INPUT}`}
                />
              </div>

              <div>
                <label
                  htmlFor="filtro-area"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Área
                </label>
                <input
                  id="filtro-area"
                  type="text"
                  value={filtros.area}
                  onChange={(e) => actualizarFiltro("area", e.target.value.toUpperCase())}
                  placeholder="Ej: OPERACIONES"
                  className={`w-full ${CLASES_INPUT}`}
                />
              </div>

              <div>
                <label
                  htmlFor="filtro-vehiculo"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Placa
                </label>
                <input
                  id="filtro-vehiculo"
                  type="text"
                  value={filtros.vehiculo}
                  onChange={(e) =>
                    actualizarFiltro(
                      "vehiculo",
                      e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""),
                    )
                  }
                  placeholder="Ej: ABC123"
                  className={`w-full ${CLASES_INPUT}`}
                />
              </div>

              <div>
                <label
                  htmlFor="filtro-busqueda"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Búsqueda rápida
                </label>
                <input
                  id="filtro-busqueda"
                  type="text"
                  value={globalFilter}
                  onChange={(e) => setGlobalFilter(e.target.value)}
                  placeholder="Conductor, móvil, obs..."
                  className={`w-full ${CLASES_INPUT}`}
                />
              </div>
            </div>

            {hayFiltrosActivos && (
              <div className="flex justify-end pt-1">
                <button
                  type="button"
                  onClick={limpiarFiltros}
                  className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
                >
                  Limpiar todos los filtros
                </button>
              </div>
            )}
          </div>

          {/* Tabla de Salidas */}
          <SalidasTable
            salidas={salidas}
            columns={columns}
            isLoading={isLoading}
            pageCount={pageCount}
            pageIndex={pageIndex}
            setPageIndex={setPageIndex}
            pageSize={pageSize}
            setPageSize={setPageSize}
            setVisibleRows={setVisibleRows}
          />

          {/* Modales de acciones (Aprobar, Rechazar, Novedad, Historial, Lote) */}
          <SalidaConfirmarModal
            accion={acciones.dialogo.confirmar?.accion ?? null}
            salida={acciones.dialogo.confirmar?.salida ?? null}
            enviando={acciones.enviando}
            errorServidor={acciones.errorAccion}
            onClose={acciones.cerrarDialogo}
            onConfirmar={() => void confirmarAccionSimple()}
          />

          <SalidaRechazarModal
            salida={acciones.dialogo.rechazar}
            enviando={acciones.enviando}
            errorServidor={acciones.errorAccion}
            onClose={acciones.cerrarDialogo}
            onRechazar={async (motivo) => {
              const fallo = await acciones.rechazar(motivo);
              if (!fallo) acciones.cerrarDialogo();
              return fallo;
            }}
          />

          <SalidaNovedadModal
            salida={acciones.dialogo.novedad}
            enviando={acciones.enviando}
            errorServidor={acciones.errorAccion}
            onClose={acciones.cerrarDialogo}
            onGuardar={async (payload) => {
              const fallo = await acciones.guardarNovedad(payload);
              if (!fallo) acciones.cerrarDialogo();
              return fallo;
            }}
            onEliminar={async () => {
              const fallo = await acciones.eliminarNovedad();
              if (!fallo) acciones.cerrarDialogo();
              return fallo;
            }}
          />

          <SalidaHistorialModal
            salida={acciones.dialogo.historial}
            onClose={acciones.cerrarDialogo}
          />

          <SalidaAprobarLoteModal
            cantidad={acciones.dialogo.lote ? acciones.seleccionCantidad : null}
            enviando={acciones.enviando}
            errorServidor={acciones.errorAccion}
            onClose={acciones.cerrarDialogo}
            onConfirmar={confirmarLote}
          />
        </div>
      )}

      {/* ============================================================== */}
      {/* PESTAÑA 2: CIERRES DE VALIDACIÓN POR ÁREA */}
      {/* ============================================================== */}
      {tabActivo === "cierres" && (
        <div className="space-y-4">
          {errorCierres && (
            <Alert
              variant="error"
              title="Error al cargar cierres"
              message={errorCierres}
            />
          )}

          {/* Barra de Filtro de Período y Botón Nuevo Cierre */}
          <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-theme-xs dark:border-gray-800 dark:bg-gray-850 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div>
                <label
                  htmlFor="filtro-cierre-mes"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Mes
                </label>
                <select
                  id="filtro-cierre-mes"
                  value={mesCierre}
                  onChange={(e) => setMesCierre(Number(e.target.value))}
                  className={CLASES_INPUT}
                >
                  {MESES.map((nombre, idx) => (
                    <option key={nombre} value={idx + 1}>
                      {idx + 1} - {nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="filtro-cierre-anio"
                  className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Año
                </label>
                <input
                  id="filtro-cierre-anio"
                  type="number"
                  value={anioCierre}
                  onChange={(e) => setAnioCierre(Number(e.target.value))}
                  min={2020}
                  max={2035}
                  className={`w-28 ${CLASES_INPUT}`}
                />
              </div>

              <div className="flex items-end pt-5">
                <Button
                  id="gestion-btn-recargar-cierres"
                  variant="outline"
                  size="sm"
                  onClick={() => recargarCierres()}
                  disabled={cargandoCierres}
                >
                  Actualizar
                </Button>
              </div>
            </div>

            <Button
              id="gestion-btn-nuevo-cierre"
              variant="primary"
              size="sm"
              onClick={() => setModalCierreAbierto(true)}
            >
              + Registrar Cierre de Área
            </Button>
          </div>

          {/* Tabla de Cierres de Validación */}
          <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden dark:border-gray-800 dark:bg-gray-850">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 dark:bg-gray-800/50 dark:text-gray-400">
                  <tr>
                    <th scope="col" className="px-5 py-3 font-semibold">
                      Área
                    </th>
                    <th scope="col" className="px-5 py-3 font-semibold">
                      Período
                    </th>
                    <th scope="col" className="px-5 py-3 font-semibold">
                      Estado de Validación
                    </th>
                    <th scope="col" className="px-5 py-3 font-semibold">
                      Fecha de Cierre
                    </th>
                    <th scope="col" className="px-5 py-3 font-semibold">
                      Detalles / Observación
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {validaciones.length === 0 ? (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-5 py-8 text-center text-gray-500 dark:text-gray-400"
                      >
                        {cargandoCierres
                          ? "Cargando validaciones de área..."
                          : `No se han registrado cierres de área para ${MESES[mesCierre - 1]} ${anioCierre}.`}
                      </td>
                    </tr>
                  ) : (
                    validaciones.map((val: ValidacionSalida) => {
                      const obs =
                        (val.datos as { observacion_cierre?: string } | undefined)
                          ?.observacion_cierre ?? "—";
                      return (
                        <tr
                          key={val.id}
                          className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40 transition-colors"
                        >
                          <td className="px-5 py-3.5 font-semibold text-gray-900 dark:text-white">
                            {val.area}
                          </td>
                          <td className="px-5 py-3.5 whitespace-nowrap text-gray-700 dark:text-gray-300">
                            {MESES[val.mes - 1]} {val.anio}
                          </td>
                          <td className="px-5 py-3.5 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-success-50 px-2.5 py-0.5 text-xs font-semibold text-success-700 dark:bg-success-500/15 dark:text-success-400">
                              <span className="h-1.5 w-1.5 rounded-full bg-success-500" />
                              Cerrado y Certificado
                            </span>
                          </td>
                          <td className="px-5 py-3.5 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                            {val.creado_en
                              ? new Date(val.creado_en).toLocaleString("es-CO")
                              : "—"}
                          </td>
                          <td className="px-5 py-3.5 text-xs text-gray-600 dark:text-gray-400 max-w-xs truncate">
                            {obs}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <CierreAreaModal
            isOpen={modalCierreAbierto}
            onClose={() => setModalCierreAbierto(false)}
            onGuardado={() => recargarCierres()}
            mesDefecto={mesCierre}
            anioDefecto={anioCierre}
          />
        </div>
      )}
    </div>
  );
}
