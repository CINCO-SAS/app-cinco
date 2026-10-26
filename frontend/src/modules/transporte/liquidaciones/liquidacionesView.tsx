// src/modules/transporte/liquidaciones/liquidacionesView.tsx
//
// Vista de Liquidaciones Financieras de Transporte (A2 / D3 / D4 / Tab 3 del legacy).
// Integra sábanas de pago mensual y pronto pago, emisión de cuentas de cobro,
// consecutivos atómicos y registro de pagos a propietarios/vehículos.

"use client";

import React, { useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";

import { useLiquidacionesState, type TipoSabana } from "./liquidacionesView.hooks";
import { RegistrarPagoModal } from "./components/RegistrarPagoModal";
import type { SabanaFila } from "@/types/transporte.types";

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const CLASES_INPUT =
  "h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "placeholder:text-gray-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const CONTRATO_BADGE: Record<string, string> = {
  PROPIO: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400",
  EXTERNO: "bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400",
  RENTING: "bg-purple-50 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400",
};

export default function LiquidacionesView() {
  const {
    mes,
    setMes,
    anio,
    setAnio,
    tipo,
    setTipo,
    placa,
    setPlaca,
    sabana,
    cargando,
    error,
    recargar,
    abrirCuentaCobro,
    registrarPagoVehiculo,
    generarConsecutivoVehiculo,
  } = useLiquidacionesState();

  const [filaPagoSeleccionada, setFilaPagoSeleccionada] = useState<SabanaFila | null>(null);

  const filas = sabana?.filas ?? [];
  const totalVehiculos = filas.length;
  const totalDias = sabana?.totales?.dias ?? 0;
  const totalImporte = sabana?.totales?.total ?? 0;
  const totalPagados = filas.filter((f) => f.pagado).length;

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6 space-y-6">
      <PageBreadcrumb
        pageTitle={["Transporte", "Administración", "Liquidaciones"]}
      />

      {/* Selector de Modalidad: Pago Mensual vs Pronto Pago */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-theme-xs dark:border-gray-800 dark:bg-gray-850 space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-gray-100 pb-3 dark:border-gray-800">
          <div className="flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
            <button
              type="button"
              onClick={() => setTipo("pago-mensual")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium transition ${
                tipo === "pago-mensual"
                  ? "bg-white text-gray-900 shadow-sm font-semibold dark:bg-gray-700 dark:text-white"
                  : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
              }`}
            >
              Pago Mensual Ordinario (CR-10)
            </button>
            <button
              type="button"
              onClick={() => setTipo("pronto-pago")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium transition ${
                tipo === "pronto-pago"
                  ? "bg-white text-gray-900 shadow-sm font-semibold dark:bg-gray-700 dark:text-white"
                  : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
              }`}
            >
              Pronto Pago (Solo Aprobadas)
            </button>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            {tipo === "pago-mensual"
              ? "Incluye salidas en estado APROBADO, REPORTADO y VALIDADO con retroceso de 6 meses."
              : "Liquidación anticipada de cortes: incluye estrictamente salidas en estado APROBADO."}
          </p>
        </div>

        {/* Filtros de consulta */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 items-end">
          <div>
            <label
              htmlFor="liq-mes"
              className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Mes del período
            </label>
            <select
              id="liq-mes"
              value={mes}
              onChange={(e) => setMes(Number(e.target.value))}
              disabled={cargando}
              className={`w-full ${CLASES_INPUT}`}
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
              htmlFor="liq-anio"
              className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Año del período
            </label>
            <input
              id="liq-anio"
              type="number"
              value={anio}
              min={2020}
              max={2035}
              onChange={(e) => setAnio(Number(e.target.value))}
              disabled={cargando}
              className={`w-full ${CLASES_INPUT}`}
            />
          </div>

          <div>
            <label
              htmlFor="liq-placa"
              className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Filtrar por Placa (Opcional)
            </label>
            <input
              id="liq-placa"
              type="text"
              value={placa}
              onChange={(e) =>
                setPlaca(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))
              }
              onKeyDown={(e) => e.key === "Enter" && recargar()}
              placeholder="Ej: ABC123"
              disabled={cargando}
              maxLength={7}
              className={`w-full ${CLASES_INPUT}`}
            />
          </div>

          <div className="flex gap-2">
            <Button
              id="liq-btn-consultar"
              variant="primary"
              size="sm"
              onClick={recargar}
              disabled={cargando}
              className="w-full"
            >
              {cargando ? "Liquidando..." : "Actualizar Sábana"}
            </Button>
          </div>
        </div>

        {error && (
          <div className="mt-2">
            <Alert variant="error" title="Error en liquidación" message={error} />
          </div>
        )}
      </div>

      {/* KPI Cards de Liquidación */}
      {sabana && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Vehículos Liquidados
            </p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
              {totalVehiculos}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">
              {totalPagados} con pago registrado
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Total Días Operados
            </p>
            <p className="mt-1 text-2xl font-bold text-brand-600 dark:text-brand-400">
              {totalDias.toLocaleString("es-CO")}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">Jornadas computadas</p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-850 sm:col-span-2">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Total Liquidado del Período
            </p>
            <p className="mt-1 text-2xl font-bold text-success-600 dark:text-success-400">
              ${Number(totalImporte).toLocaleString("es-CO")} COP
            </p>
            <p className="mt-0.5 text-xs text-gray-400">
              Período {MESES[sabana.mes - 1]} {sabana.anio}{" "}
              {sabana.retroactivo && "(Aplicado con cálculo retroactivo)"}
            </p>
          </div>
        </div>
      )}

      {/* Tabla Sábana de Liquidación */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden dark:border-gray-800 dark:bg-gray-850">
        <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-gray-800 dark:text-white/90">
              Sábana Detallada por Vehículo
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Cálculo con snapshots de tarifa y novedades consolidadas en servidor.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 dark:bg-gray-800/50 dark:text-gray-400">
              <tr>
                <th scope="col" className="px-5 py-3 font-semibold">
                  Vehículo / Placa
                </th>
                <th scope="col" className="px-5 py-3 font-semibold">
                  Contrato
                </th>
                <th scope="col" className="px-5 py-3 font-semibold">
                  Conductor C.C.
                </th>
                <th scope="col" className="px-5 py-3 font-semibold">
                  Tarifa Día
                </th>
                <th scope="col" className="px-5 py-3 text-center font-semibold">
                  Días
                </th>
                <th scope="col" className="px-5 py-3 font-semibold">
                  Total Liquidado
                </th>
                <th scope="col" className="px-5 py-3 font-semibold">
                  Estado Pago
                </th>
                <th scope="col" className="px-5 py-3 text-right font-semibold">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {filas.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-8 text-center text-gray-500 dark:text-gray-400"
                  >
                    {cargando
                      ? "Calculando liquidación financiera..."
                      : "No hay registros de salidas liquidadas para los filtros seleccionados."}
                  </td>
                </tr>
              ) : (
                filas.map((fila: SabanaFila) => (
                  <tr
                    key={fila.vehiculo}
                    className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40 transition-colors"
                  >
                    {/* Placa */}
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="font-mono text-base font-bold tracking-wider text-gray-900 dark:text-white">
                        {fila.placa}
                      </span>
                    </td>

                    {/* Contrato */}
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          CONTRATO_BADGE[fila.tipo_contrato] ??
                          "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                        }`}
                      >
                        {fila.tipo_contrato}
                      </span>
                    </td>

                    {/* Conductor Cédula */}
                    <td className="px-5 py-3.5 text-xs text-gray-600 dark:text-gray-400">
                      {fila.conductor_cedula ?? "—"}
                    </td>

                    {/* Tarifa base */}
                    <td className="px-5 py-3.5 whitespace-nowrap text-xs text-gray-700 dark:text-gray-300">
                      ${Number(fila.valor_dia).toLocaleString("es-CO")}
                    </td>

                    {/* Días */}
                    <td className="px-5 py-3.5 text-center font-bold text-gray-900 dark:text-white">
                      {fila.dias}
                    </td>

                    {/* Total Liquidado */}
                    <td className="px-5 py-3.5 whitespace-nowrap font-bold text-brand-600 dark:text-brand-400">
                      ${Number(fila.total).toLocaleString("es-CO")}
                    </td>

                    {/* Estado Pago */}
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      {fila.pagado ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-success-50 px-2 py-0.5 text-xs font-semibold text-success-700 dark:bg-success-500/15 dark:text-success-400">
                          <span className="h-1.5 w-1.5 rounded-full bg-success-500" />
                          Pagado {fila.fecha_pago ? `(${fila.fecha_pago})` : ""}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                          Pendiente
                        </span>
                      )}
                    </td>

                    {/* Acciones */}
                    <td className="px-5 py-3.5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          id={`liq-btn-cuenta-${fila.placa}`}
                          variant="outline"
                          size="sm"
                          onClick={() => abrirCuentaCobro(fila.placa)}
                          className="text-xs"
                          title="Imprimir o ver Cuenta de Cobro con 1% Retefuente"
                        >
                          Cuenta Cobro
                        </Button>

                        <Button
                          id={`liq-btn-consecutivo-${fila.placa}`}
                          variant="outline"
                          size="sm"
                          onClick={() => generarConsecutivoVehiculo(fila.vehiculo)}
                          className="text-xs"
                          title="Generar o consultar Consecutivo Mensual"
                        >
                          Consecutivo
                        </Button>

                        <Button
                          id={`liq-btn-pago-${fila.placa}`}
                          variant="primary"
                          size="sm"
                          onClick={() => setFilaPagoSeleccionada(fila)}
                          className="text-xs"
                          title="Registrar o actualizar pago"
                        >
                          {fila.pagado ? "Modificar Pago" : "Pagar"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Registro de Pago */}
      <RegistrarPagoModal
        fila={filaPagoSeleccionada}
        mes={mes}
        anio={anio}
        tipo={tipo}
        isOpen={Boolean(filaPagoSeleccionada)}
        onClose={() => setFilaPagoSeleccionada(null)}
        onGuardar={registrarPagoVehiculo}
      />
    </div>
  );
}
