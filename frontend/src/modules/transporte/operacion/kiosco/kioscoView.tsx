// src/modules/transporte/operacion/kiosco/kioscoView.tsx
//
// Vista del kiosco de despacho vehicular.
// Flujo de 3 pasos: Identificar -> Validar -> Registrar
// Diseñado para uso en tablet/pantalla de kiosco.

"use client";

import { useCallback } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";

import { useKioscoState, type PasoKiosco } from "./kioscoView.hooks";
import type { KioscoResultadoValidacion } from "@/types/transporte.types";

// ============================================================
// Helpers
// ============================================================

const PASO_LABELS: Record<PasoKiosco, string> = {
  IDLE:         "1. Identificar Vehículo",
  CARGANDO:     "1. Identificando...",
  IDENTIFICADO: "2. Confirmar Salida",
  VALIDANDO:    "2. Validando...",
  VALIDADO:     "3. Confirmar Registro",
  REGISTRANDO:  "3. Registrando...",
  REGISTRADO:   "Salida Registrada",
  ERROR:        "Error — vuelva a intentarlo",
};

const ESTADO_BADGE: Record<string, string> = {
  REPORTADO: "bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400",
  APROBADO:  "bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400",
  RECHAZADO: "bg-error-50 text-error-700 dark:bg-error-500/15 dark:text-error-400",
  ELIMINADO: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  VALIDADO:  "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400",
};

const STEP_NUMBERS: Record<PasoKiosco, number> = {
  IDLE: 1, CARGANDO: 1, ERROR: 1,
  IDENTIFICADO: 2, VALIDANDO: 2,
  VALIDADO: 3, REGISTRANDO: 3, REGISTRADO: 3,
};

// Clases de inputs/selects consistentes con SalidaFormModal y SalidasToolbar
const CLASES_INPUT =
  "h-11 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "placeholder:text-gray-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

// ============================================================
// Tarjeta de vehículo (reutilizada en Paso 2 y 3)
// ============================================================

function TarjetaVehiculo({ vehiculo }: { vehiculo: Record<string, unknown> }) {
  const v = vehiculo as {
    placa?: string; tipo_vehiculo?: string; marca?: string;
    referencia?: string; nombre_propietario?: string; tipo_contrato?: string;
  };
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center gap-3">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-500 dark:bg-brand-500/15">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0M3 12l2-7h14l2 7M5 12h14" />
          </svg>
        </span>
        <div>
          <p className="font-mono text-xl font-bold tracking-widest text-gray-900 dark:text-white">
            {v.placa}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {v.tipo_vehiculo} — {v.marca} {v.referencia}
          </p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-x-4 text-sm">
        <span className="text-gray-500 dark:text-gray-400">Propietario</span>
        <span className="font-medium text-gray-800 dark:text-gray-200">
          {v.nombre_propietario ?? "—"}
        </span>
        <span className="text-gray-500 dark:text-gray-400">Contrato</span>
        <span className="font-medium text-gray-800 dark:text-gray-200">
          {v.tipo_contrato ?? "—"}
        </span>
      </div>
    </div>
  );
}

// ============================================================
// Paso 1 — Ingresar placa
// ============================================================

function PasoIdentificar({
  placa, setPlaca, onIdentificar, cargando,
}: {
  placa: string;
  setPlaca: (v: string) => void;
  onIdentificar: () => void;
  cargando: boolean;
}) {
  const placaLimpia = placa.toUpperCase().replace(/[^A-Z0-9]/g, "").trim();
  const esPlacaValida = placaLimpia.length >= 5 && placaLimpia.length <= 7;

  return (
    <div className="flex flex-col items-center gap-6 py-6">
      <div className="text-center">
        <span className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-brand-500 dark:bg-brand-500/15">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0M3 12l2-7h14l2 7M5 12h14" />
          </svg>
        </span>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white/90">
          Ingrese la placa del vehículo
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Digite los 6 caracteres de la placa vehicular
        </p>
      </div>

      <div className="w-full max-w-sm">
        <input
          id="kiosco-placa-input"
          type="text"
          value={placa}
          onChange={(e) => setPlaca(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
          onKeyDown={(e) => e.key === "Enter" && esPlacaValida && onIdentificar()}
          placeholder="Ej: ABC123"
          autoFocus
          autoComplete="off"
          maxLength={7}
          disabled={cargando}
          className={
            "w-full rounded-xl border-2 px-4 py-3 text-center font-mono text-2xl " +
            "tracking-widest uppercase placeholder:text-gray-300 " +
            "border-gray-300 bg-white text-gray-900 " +
            "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
            "disabled:cursor-not-allowed disabled:opacity-50 " +
            "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 " +
            "transition"
          }
        />
        {placa.length > 0 && !esPlacaValida && (
          <p className="mt-1.5 text-center text-xs text-gray-400 dark:text-gray-500">
            La placa debe tener entre 5 y 7 caracteres alfanuméricos.
          </p>
        )}
      </div>

      <Button
        id="kiosco-btn-buscar"
        onClick={onIdentificar}
        disabled={!esPlacaValida || cargando}
        size="md"
        className="px-10 py-3 text-lg"
      >
        {cargando ? "Buscando..." : "Buscar Vehículo"}
      </Button>
    </div>
  );
}

// ============================================================
// Paso 2 — Confirmar datos de salida
// ============================================================

function PasoConfirmar({
  vehiculo, salidaExistente, movilSale, area, fecha,
  setMovilSale, setArea, setFecha, onValidar, onReiniciar, cargando,
}: {
  vehiculo: Record<string, unknown>;
  salidaExistente: Record<string, unknown> | null;
  movilSale: string;
  area: string;
  fecha: string;
  setMovilSale: (v: string) => void;
  setArea: (v: string) => void;
  setFecha: (v: string) => void;
  onValidar: () => void;
  onReiniciar: () => void;
  cargando: boolean;
}) {
  const s = salidaExistente as { estado?: string; movil_sale?: string } | null;
  const esDisponible = !movilSale.trim() || movilSale.trim().toLowerCase() === "disponible";
  const requiereArea = esDisponible;
  const puedeContinuar = Boolean(fecha) && (!requiereArea || Boolean(area.trim())) && !cargando;

  return (
    <div className="flex flex-col gap-4">
      <TarjetaVehiculo vehiculo={vehiculo} />

      {s && (
        <Alert
          variant="warning"
          title="Salida existente hoy"
          message={`Estado: ${s.estado ?? "—"}  ·  Móvil: ${s.movil_sale ?? "—"}`}
        />
      )}

      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-4 text-sm font-semibold text-gray-800 dark:text-white/90">
          Datos de la salida
        </h3>

        <div className="space-y-4">
          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
              htmlFor="kiosco-fecha"
            >
              Fecha de salida <span className="text-error-500">*</span>
            </label>
            <input
              id="kiosco-fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              disabled={cargando}
              className={CLASES_INPUT}
            />
          </div>

          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
              htmlFor="kiosco-movil"
            >
              Cédula del conductor o móvil{" "}
              <span className="font-normal text-gray-400">(opcional / disponible)</span>
            </label>
            <input
              id="kiosco-movil"
              type="text"
              value={movilSale}
              onChange={(e) => setMovilSale(e.target.value)}
              placeholder="Ej: 1234567890 o dejar vacío para Disponible"
              disabled={cargando}
              className={CLASES_INPUT}
            />
            <p className="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
              Si se deja en blanco, el vehículo se registra en estado <strong>Disponible</strong>.
            </p>
          </div>

          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
              htmlFor="kiosco-area"
            >
              Área operativa{" "}
              {requiereArea ? (
                <span className="text-error-500 font-semibold">* (Obligatoria si no hay conductor)</span>
              ) : (
                <span className="font-normal text-gray-400">(opcional / tomada de nómina)</span>
              )}
            </label>
            <input
              id="kiosco-area"
              type="text"
              value={area}
              onChange={(e) => setArea(e.target.value.toUpperCase())}
              placeholder="Ej: OPERACIONES, LOGISTICA, MANTENIMIENTO"
              disabled={cargando}
              className={CLASES_INPUT}
            />
            {requiereArea && !area.trim() && (
              <p className="mt-1 text-xs text-warning-600 dark:text-warning-400">
                Al marcar como disponible, debe especificar el área a la que prestará servicio el vehículo.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          id="kiosco-btn-volver-confirmar"
          variant="outline"
          onClick={onReiniciar}
          disabled={cargando}
          className="flex-1"
        >
          Volver
        </Button>
        <Button
          id="kiosco-btn-validar"
          onClick={onValidar}
          disabled={!puedeContinuar}
          className="flex-[2]"
        >
          {cargando ? "Validando..." : "Verificar disponibilidad"}
        </Button>
      </div>
    </div>
  );
}

// ============================================================
// Paso 3 — Confirmar registro
// ============================================================

function PasoRegistrar({
  vehiculo, validacion, fecha, movilSale, area,
  onRegistrar, onVolver, cargando,
}: {
  vehiculo: Record<string, unknown>;
  validacion: KioscoResultadoValidacion;
  fecha: string;
  movilSale: string;
  area: string;
  onRegistrar: () => void;
  onVolver: () => void;
  cargando: boolean;
}) {
  const movilMostrar = movilSale.trim() || "Disponible";
  const areaMostrar = area.trim() || (movilSale.trim() ? "Asignada por nómina" : "Sin área");

  return (
    <div className="flex flex-col gap-4">
      <TarjetaVehiculo vehiculo={vehiculo} />

      {/* Resultado del pre-chequeo */}
      {validacion.puede_registrar ? (
        <Alert
          variant="success"
          title="Disponible para despacho"
          message={validacion.mensaje || "El vehículo cumple todas las condiciones y puede ser registrado hoy."}
        />
      ) : (
        <div>
          <Alert
            variant="error"
            title="No se puede registrar"
            message={validacion.mensaje}
          />
          {(validacion.duplicado_vehiculo || validacion.duplicado_movil) && (
            <ul className="mt-1.5 list-inside list-disc text-xs text-error-400">
              {validacion.duplicado_vehiculo && (
                <li>Duplicado de vehículo en la fecha (CR-1)</li>
              )}
              {validacion.duplicado_movil && (
                <li>Duplicado de móvil en la fecha (CR-2)</li>
              )}
            </ul>
          )}
        </div>
      )}

      {/* Resumen */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-800 dark:text-white/90">
          Resumen del despacho
        </h3>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Fecha</span>
          <span className="font-medium text-gray-800 dark:text-gray-200">{fecha}</span>
          <span className="text-gray-500 dark:text-gray-400">Móvil / Conductor</span>
          <span className="font-medium text-gray-800 dark:text-gray-200">{movilMostrar}</span>
          <span className="text-gray-500 dark:text-gray-400">Área</span>
          <span className="font-medium text-gray-800 dark:text-gray-200">{areaMostrar}</span>
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          id="kiosco-btn-editar"
          variant="outline"
          onClick={onVolver}
          disabled={cargando}
          className="flex-1"
        >
          Editar
        </Button>
        {validacion.puede_registrar ? (
          <Button
            id="kiosco-btn-registrar"
            onClick={onRegistrar}
            disabled={cargando}
            className="flex-[2]"
          >
            {cargando ? "Registrando..." : "Confirmar Salida"}
          </Button>
        ) : (
          <Button
            id="kiosco-btn-modificar"
            variant="outline"
            onClick={onVolver}
            className="flex-[2]"
          >
            Modificar datos
          </Button>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Éxito
// ============================================================

function PasoExito({ salida, onNueva }: { salida: Record<string, unknown>; onNueva: () => void }) {
  const s = salida as {
    estado?: string;
    movil_sale?: string;
    fecha?: string;
    fecha_salida?: string;
    vehiculo_placa?: string;
    area?: string;
  };
  const fechaMostrar = s.fecha_salida ?? s.fecha ?? "—";

  return (
    <div className="flex flex-col items-center gap-6 py-6 text-center">
      <span className="inline-flex h-20 w-20 items-center justify-center rounded-full bg-success-50 text-success-500 dark:bg-success-500/15">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </span>

      <div>
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Salida Registrada
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          El despacho fue creado exitosamente en el sistema.
        </p>
      </div>

      <div className="w-full rounded-xl border border-gray-200 bg-white p-5 text-left text-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          <span className="text-gray-500 dark:text-gray-400">Placa</span>
          <span className="font-mono font-bold text-gray-900 dark:text-white">
            {s.vehiculo_placa ?? "—"}
          </span>
          <span className="text-gray-500 dark:text-gray-400">Fecha</span>
          <span className="text-gray-700 dark:text-gray-300">{fechaMostrar}</span>
          <span className="text-gray-500 dark:text-gray-400">Estado</span>
          <span
            className={`inline-block w-fit rounded-full px-2 py-0.5 text-xs font-semibold ${
              ESTADO_BADGE[s.estado ?? ""] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
            }`}
          >
            {s.estado ?? "REPORTADO"}
          </span>
          <span className="text-gray-500 dark:text-gray-400">Móvil</span>
          <span className="text-gray-700 dark:text-gray-300">{s.movil_sale ?? "Disponible"}</span>
          {s.area && (
            <>
              <span className="text-gray-500 dark:text-gray-400">Área</span>
              <span className="text-gray-700 dark:text-gray-300">{s.area}</span>
            </>
          )}
        </div>
      </div>

      <Button
        id="kiosco-btn-nueva-salida"
        onClick={onNueva}
        className="px-10"
      >
        Registrar otra salida
      </Button>
    </div>
  );
}

// ============================================================
// Vista principal
// ============================================================

export default function KioscoView() {
  const {
    estado, reiniciar, setPlaca, setFecha, setMovilSale, setArea,
    identificar, validar, registrar, volverAIdentificado,
  } = useKioscoState();

  const handleRegistrar = useCallback(() => registrar(), [registrar]);

  const stepActual = STEP_NUMBERS[estado.paso];
  const esRegistrado = estado.paso === "REGISTRADO";
  const steps = ["Identificar", "Confirmar", "Registrar"];

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb pageTitle={["Transporte", "Operación", "Kiosco de Despacho"]} />

      <div className="mx-auto max-w-lg">
        {/* Stepper */}
        {!esRegistrado && (
          <nav
            className="mb-6 flex items-center justify-center gap-0"
            aria-label="Pasos del kiosco"
          >
            {steps.map((label, idx) => {
              const num = idx + 1;
              const activo = stepActual === num;
              const completo = stepActual > num;
              return (
                <div key={label} className="flex items-center">
                  <div
                    className={`flex flex-col items-center transition-all ${
                      activo ? "opacity-100" : "opacity-50"
                    }`}
                  >
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-bold transition-all ${
                        completo
                          ? "border-brand-500 bg-brand-500 text-white"
                          : activo
                          ? "border-brand-500 bg-white text-brand-500 dark:bg-gray-800"
                          : "border-gray-300 bg-white text-gray-400 dark:border-gray-700 dark:bg-gray-800"
                      }`}
                    >
                      {completo ? (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : num}
                    </div>
                    <span className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {label}
                    </span>
                  </div>
                  {idx < steps.length - 1 && (
                    <div
                      className={`mx-2 mb-4 h-0.5 w-16 transition-all ${
                        completo ? "bg-brand-500" : "bg-gray-200 dark:bg-gray-700"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </nav>
        )}

        {/* Panel principal */}
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs dark:border-gray-700 dark:bg-gray-800">
          <h1 className="mb-5 text-base font-semibold text-gray-800 dark:text-white/90">
            {PASO_LABELS[estado.paso]}
          </h1>

          {/* Error global */}
          {estado.error && (
            <div className="mb-5">
              <Alert variant="error" title="Error" message={estado.error} />
            </div>
          )}

          {/* Paso 1 */}
          {(estado.paso === "IDLE" || estado.paso === "CARGANDO" || estado.paso === "ERROR") && (
            <PasoIdentificar
              placa={estado.placa}
              setPlaca={setPlaca}
              onIdentificar={() => identificar()}
              cargando={estado.paso === "CARGANDO"}
            />
          )}

          {/* Paso 2 */}
          {(estado.paso === "IDENTIFICADO" || estado.paso === "VALIDANDO") && estado.datos && (
            <PasoConfirmar
              vehiculo={estado.datos.vehiculo as unknown as Record<string, unknown>}
              salidaExistente={estado.datos.salida as unknown as Record<string, unknown> | null}
              movilSale={estado.movilSale}
              area={estado.area}
              fecha={estado.fecha}
              setMovilSale={setMovilSale}
              setArea={setArea}
              setFecha={setFecha}
              onValidar={validar}
              onReiniciar={reiniciar}
              cargando={estado.paso === "VALIDANDO"}
            />
          )}

          {/* Paso 3 */}
          {(estado.paso === "VALIDADO" || estado.paso === "REGISTRANDO") && estado.datos && estado.validacion && (
            <PasoRegistrar
              vehiculo={estado.datos.vehiculo as unknown as Record<string, unknown>}
              validacion={estado.validacion}
              fecha={estado.fecha}
              movilSale={estado.movilSale}
              area={estado.area}
              onRegistrar={handleRegistrar}
              onVolver={volverAIdentificado}
              cargando={estado.paso === "REGISTRANDO"}
            />
          )}

          {/* Éxito */}
          {estado.paso === "REGISTRADO" && estado.salidaRegistrada && (
            <PasoExito
              salida={estado.salidaRegistrada as unknown as Record<string, unknown>}
              onNueva={reiniciar}
            />
          )}
        </div>
      </div>
    </div>
  );
}
