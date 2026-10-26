// src/modules/transporte/planillas/planillasView.tsx
//
// Vista de la Planilla Oficial de Salida F-104 (§5.6 / S5 / CR-11).
// Permite generar los consecutivos atómicos por vehículo y consultar/imprimir
// el formato físico de despacho (LETTER horizontal con código QR y firmas).

"use client";

import React from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";

import { usePlanillasState } from "./planillasView.hooks";
import type { AlcancePlanilla, VehiculoPlanilla } from "@/types/transporte.types";

const CLASES_INPUT =
  "h-11 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "placeholder:text-gray-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const CONTRATO_BADGE: Record<string, string> = {
  PROPIO: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400",
  EXTERNO: "bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400",
  RENTING: "bg-purple-50 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400",
};

export default function PlanillasView() {
  const {
    fecha,
    setFecha,
    alcance,
    setAlcance,
    placa,
    setPlaca,
    planilla,
    cargando,
    imprimiendo,
    error,
    consultar,
    imprimirFormato,
  } = usePlanillasState();

  const vehiculos = planilla?.vehiculos ?? [];
  const totalVehiculos = vehiculos.length;
  const totalPropios = vehiculos.filter((v) => v.tipo_contrato === "PROPIO").length;
  const totalExternos = vehiculos.filter((v) => v.tipo_contrato === "EXTERNO").length;
  const totalRenting = vehiculos.filter((v) => v.tipo_contrato === "RENTING").length;

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6 space-y-6">
      {/* Encabezado y Breadcrumbs */}
      <PageBreadcrumb
        pageTitle={["Transporte", "Administración", "Planilla Oficial F-104"]}
      />

      {/* Banner de Información Operativa */}
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </span>
          <div className="text-sm">
            <p className="font-semibold text-gray-800 dark:text-white/90">
              Formato Oficial F-104 para Portería y Despacho Físico
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">
              Genera la hoja oficial de salida en formato horizontal tipo carta con código QR
              único y casillas de firma obligatoria para porteros (salida y retorno). Los
              consecutivos atómicos se asignan de forma mensual irreversible. Excluye
              estrictamente motocicletas (aplicable a flota vehicular de 4+ ruedas).
            </p>
          </div>
        </div>
      </div>

      {/* Panel de Parámetros de Generación */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-theme-xs dark:border-gray-800 dark:bg-gray-850">
        <h2 className="mb-4 text-base font-semibold text-gray-800 dark:text-white/90">
          Parámetros de la Planilla
        </h2>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Fecha */}
          <div>
            <label
              htmlFor="planilla-fecha"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
            >
              Fecha de despacho <span className="text-error-500">*</span>
            </label>
            <input
              id="planilla-fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              disabled={cargando || imprimiendo}
              className={CLASES_INPUT}
            />
          </div>

          {/* Alcance */}
          <div>
            <label
              htmlFor="planilla-alcance"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
            >
              Alcance de la flota <span className="text-error-500">*</span>
            </label>
            <select
              id="planilla-alcance"
              value={alcance}
              onChange={(e) => setAlcance(e.target.value as AlcancePlanilla)}
              disabled={cargando || imprimiendo}
              className={CLASES_INPUT}
            >
              <option value="TODAS">Toda la flota activa (Todas las placas)</option>
              <option value="PLACA">Una placa específica</option>
              <option value="PROPIO">Solo flota Propia</option>
              <option value="EXTERNO">Solo flota Externa</option>
              <option value="RENTING">Solo flota Renting</option>
            </select>
          </div>

          {/* Placa (condicional) */}
          <div>
            <label
              htmlFor="planilla-placa"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
            >
              Placa del vehículo{" "}
              {alcance === "PLACA" ? (
                <span className="text-error-500">* (Requerida)</span>
              ) : (
                <span className="text-gray-400 font-normal">(Opcional)</span>
              )}
            </label>
            <input
              id="planilla-placa"
              type="text"
              value={placa}
              onChange={(e) =>
                setPlaca(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))
              }
              onKeyDown={(e) => e.key === "Enter" && consultar()}
              placeholder="Ej: ABC123"
              disabled={alcance !== "PLACA" || cargando || imprimiendo}
              maxLength={7}
              className={CLASES_INPUT}
            />
          </div>

          {/* Acciones principales */}
          <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
            <Button
              id="planilla-btn-consultar"
              variant="primary"
              onClick={consultar}
              disabled={cargando || (alcance === "PLACA" && !placa.trim())}
              className="w-full flex-1"
            >
              {cargando ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="h-4 w-4 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Generando...
                </span>
              ) : (
                "Generar y Ver"
              )}
            </Button>

            <Button
              id="planilla-btn-imprimir-todo"
              variant="outline"
              onClick={() => imprimirFormato()}
              disabled={imprimiendo || (alcance === "PLACA" && !placa.trim())}
              className="shrink-0"
              title="Abrir formato físico oficial para impresión"
            >
              {imprimiendo ? "Preparando..." : "Imprimir F-104"}
            </Button>
          </div>
        </div>

        {error && (
          <div className="mt-4">
            <Alert variant="error" title="Error en la planilla" message={error} />
          </div>
        )}
      </div>

      {/* Resumen estadístico cuando hay datos */}
      {planilla && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Total Vehículos
            </p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
              {totalVehiculos}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">Para fecha {planilla.fecha}</p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Propios</p>
            <p className="mt-1 text-2xl font-bold text-blue-600 dark:text-blue-400">
              {totalPropios}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">Flota interna</p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Externos</p>
            <p className="mt-1 text-2xl font-bold text-warning-600 dark:text-warning-400">
              {totalExternos}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">Terceros transportadores</p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Renting</p>
            <p className="mt-1 text-2xl font-bold text-purple-600 dark:text-purple-400">
              {totalRenting}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">Flota arrendada</p>
          </div>
        </div>
      )}

      {/* Tabla detallada de Vehículos y Consecutivos */}
      {planilla && (
        <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden dark:border-gray-800 dark:bg-gray-850">
          <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-base font-semibold text-gray-800 dark:text-white/90">
                Detalle de Vehículos en la Planilla
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Alcance: <strong>{planilla.alcance}</strong> · Cada fila cuenta con su
                consecutivo asignado y formato individual listo para imprimir.
              </p>
            </div>
            <Button
              id="planilla-btn-imprimir-lote"
              variant="outline"
              size="sm"
              onClick={() => imprimirFormato()}
              disabled={imprimiendo || totalVehiculos === 0}
            >
              Imprimir Lote Completo ({totalVehiculos})
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 dark:bg-gray-800/50 dark:text-gray-400">
                <tr>
                  <th scope="col" className="px-5 py-3 font-semibold">
                    Consecutivo
                  </th>
                  <th scope="col" className="px-5 py-3 font-semibold">
                    Vehículo / Placa
                  </th>
                  <th scope="col" className="px-5 py-3 font-semibold">
                    Tipo / Contrato
                  </th>
                  <th scope="col" className="px-5 py-3 font-semibold">
                    Conductor Habitual
                  </th>
                  <th scope="col" className="px-5 py-3 font-semibold">
                    Propietario
                  </th>
                  <th scope="col" className="px-5 py-3 font-semibold">
                    Tarifa Base
                  </th>
                  <th scope="col" className="px-5 py-3 text-right font-semibold">
                    Acción
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {vehiculos.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-8 text-center text-gray-500 dark:text-gray-400"
                    >
                      No se encontraron vehículos activos para el alcance seleccionado.
                    </td>
                  </tr>
                ) : (
                  vehiculos.map((v: VehiculoPlanilla) => (
                    <tr
                      key={v.vehiculo_id}
                      className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40 transition-colors"
                    >
                      {/* Consecutivo */}
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 rounded-md bg-gray-100 px-2.5 py-1 font-mono text-xs font-bold text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                          #{v.consecutivo}
                        </span>
                        {v.consecutivo_creado && (
                          <span className="ml-1.5 inline-block rounded bg-success-50 px-1.5 py-0.5 text-[10px] font-semibold text-success-600 dark:bg-success-500/10 dark:text-success-400">
                            Nuevo
                          </span>
                        )}
                      </td>

                      {/* Placa y Marca */}
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-base font-bold tracking-wider text-gray-900 dark:text-white">
                            {v.placa}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {v.marca} {v.referencia ?? ""} ({v.modelo_anio})
                        </p>
                      </td>

                      {/* Tipo y Contrato */}
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span
                          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            CONTRATO_BADGE[v.tipo_contrato] ??
                            "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                          }`}
                        >
                          {v.tipo_contrato}
                        </span>
                        <p className="text-xs text-gray-400 mt-0.5">{v.tipo_vehiculo}</p>
                      </td>

                      {/* Conductor */}
                      <td className="px-5 py-3.5">
                        {v.conductor ? (
                          <div>
                            <p className="font-medium text-gray-800 dark:text-gray-200">
                              {v.conductor.nombre}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              C.C. {v.conductor.cedula} · Cel: {v.conductor.celular || "—"}
                            </p>
                          </div>
                        ) : (
                          <span className="text-xs italic text-gray-400">
                            Sin conductor habitual
                          </span>
                        )}
                      </td>

                      {/* Propietario */}
                      <td className="px-5 py-3.5 text-xs">
                        <p className="font-medium text-gray-800 dark:text-gray-200">
                          {v.nombre_propietario}
                        </p>
                        <p className="text-gray-400">C.C. {v.cedula_propietario}</p>
                      </td>

                      {/* Tarifa base */}
                      <td className="px-5 py-3.5 whitespace-nowrap text-sm font-medium text-gray-800 dark:text-gray-200">
                        ${Number(v.valor_dia_base).toLocaleString("es-CO")}
                      </td>

                      {/* Botón individual */}
                      <td className="px-5 py-3.5 text-right whitespace-nowrap">
                        <Button
                          id={`planilla-btn-imprimir-${v.placa}`}
                          variant="outline"
                          size="sm"
                          onClick={() => imprimirFormato("PLACA", v.placa)}
                          disabled={imprimiendo}
                          className="text-xs"
                          title={`Imprimir hoja individual para ${v.placa}`}
                        >
                          Imprimir F-104
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
