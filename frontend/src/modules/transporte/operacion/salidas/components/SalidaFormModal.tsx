// src/modules/transporte/operacion/salidas/components/SalidaFormModal.tsx
//
// Alta de salida (S6 · matriz §6, legacy `transporte_salida.php` 380–552).
//
// Reglas del backend (`SalidaService.registrar_salida`) que este form replica:
//   · `movil_sale` debe ser un EMPLEADO con área y carpeta en nómina, o la
//     sentinella 'disponible'. Por eso aquí se BUSCA personal
//     (EmployeeSearchInput) y no se escribe una cédula a mano: un conductor
//     externo que no esté en nómina rechaza el alta con
//     "…no tiene área asignada".
//   · Con 'disponible' el ÁREA deja de venir de nómina y pasa a ser
//     obligatoria a mano (`MSG_DISPONIBLE_SIN_AREA`).
//   · `area`/`carpeta` se PRECARGAN desde el empleado elegido: el legacy
//     sacaba los snapshots de la misma fila de personal.
//   · `valor_dia` es opcional y por defecto toma la tarifa del vehículo
//     (`valor_dia_base`), que se precambia al elegir vehículo.
//   · CR-9 (ventana −2 días hábiles), CR-1 (vehículo-día) y CR-2
//     (conductor-día) los valida el SERVIDOR: aquí únicamente se pinta el
//     mensaje en el banner, sin re-implementar la ventana.

"use client";

import { useCallback, useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import { EmployeeSearchInput } from "@/components/form/EmployeeSearchInput";
import { Modal } from "@/components/ui/modal";
import { classifyError, extractValidationErrors } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { Empleado } from "@/types/empleado";
import type { VehiculoListado } from "@/types/transporte.types";
import { hoyISO } from "../salidasView.utils";

const TITULO = "salida-form-titulo";

const EsquemaSalida = z
  .object({
    fecha_salida: z.string().min(1, "La fecha es obligatoria."),
    vehiculo: z.string().min(1, "El vehículo es obligatorio."),
    disponible: z.boolean(),
    /** Cédula del empleado elegido; vacío si aún no se elige ninguno. */
    movil_sale: z.string(),
    cc_asignada: z.string(),
    area: z.string().trim().max(100, "Máximo 100 caracteres."),
    carpeta: z.string().trim().max(100, "Máximo 100 caracteres."),
    sede: z.string().trim().max(100, "Máximo 100 caracteres."),
    valor_dia: z.string(),
    observacion: z.string().trim().max(2000, "Máximo 2000 caracteres."),
  })
  .refine((d) => d.disponible || d.movil_sale, {
    message: "Selecciona el empleado que sale, o marca 'Disponible'.",
    path: ["movil_sale"],
  })
  .refine((d) => !d.disponible || d.area, {
    message: "Si la salida es 'Disponible' el área es obligatoria.",
    path: ["area"],
  });

type DatosSalida = z.infer<typeof EsquemaSalida>;

const VALORES_VACIOS: DatosSalida = {
  fecha_salida: "",
  vehiculo: "",
  disponible: false,
  movil_sale: "",
  cc_asignada: "",
  area: "",
  carpeta: "",
  sede: "",
  valor_dia: "",
  observacion: "",
};

interface SalidaFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGuardado: () => void;
}

const CLASES_SEGMENTO =
  "h-9 flex-1 rounded-lg border px-3 text-sm transition-colors " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20";

export const SalidaFormModal = ({
  isOpen,
  onClose,
  onGuardado,
}: SalidaFormModalProps) => {
  const [vehiculos, setVehiculos] = useState<VehiculoListado[]>([]);
  const [errorVehiculos, setErrorVehiculos] = useState<string | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  // La búsqueda de empleados vive fuera del formulario: RHF solo guarda la
  // CÉDULA (`movil_sale` / `cc_asignada`), que es lo que viaja al backend.
  const [empleado, setEmpleado] = useState<Empleado | null>(null);
  const [movilAsignada, setMovilAsignada] = useState<Empleado | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<DatosSalida>({
    // `as any` por la fricción de tipos zod-v4 ↔ @hookform/resolvers v5
    // (mismo patrón que ConductorFormModal y ActividadForm.hooks.ts).
    resolver: zodResolver(EsquemaSalida) as never,
    defaultValues: { ...VALORES_VACIOS, fecha_salida: hoyISO() },
  });

  // Al abrir: valores frescos + catálogo de vehículos (una sola vez).
  useEffect(() => {
    if (!isOpen) return;

    reset({ ...VALORES_VACIOS, fecha_salida: hoyISO() });
    setErrorServidor(null);
    setErrorVehiculos(null);
    setEmpleado(null);
    setMovilAsignada(null);

    let cancelado = false;
    void (async () => {
      try {
        const lista = await transporteService.getVehiculos();
        if (cancelado) return;
        setVehiculos(lista.filter((vehiculo) => vehiculo.activo));
      } catch (error) {
        if (cancelado) return;
        setErrorVehiculos(classifyError(error).message);
        logDevelopmentError("Error cargando vehículos:", error);
      }
    })();

    return () => {
      cancelado = true;
    };
  }, [isOpen, reset]);

  // Regla de negocio en vivo: con 'disponible' el área se elige a mano y ya
  // no se busca empleado (el backend exige área en ese caso).
  const disponible = watch("disponible");

  const cerrar = useCallback(() => {
    if (isSubmitting) return;
    onClose();
  }, [isSubmitting, onClose]);

  const alElegirEmpleado = useCallback(
    (persona: Empleado | null) => {
      setEmpleado(persona);
      setValue("movil_sale", persona?.cedula ?? "", { shouldValidate: true });
      // Snapshots desde nómina (el backend hace lo mismo si vienen vacíos).
      if (persona?.area) setValue("area", persona.area);
      if (persona?.carpeta) setValue("carpeta", persona.carpeta);
    },
    [setValue],
  );

  const enviar = handleSubmit(async (datos) => {
    setErrorServidor(null);
    try {
      await transporteService.registrarSalida({
        fecha_salida: datos.fecha_salida,
        vehiculo: Number(datos.vehiculo),
        movil_sale: datos.disponible ? "disponible" : datos.movil_sale.trim(),
        cc_asignada: datos.cc_asignada.trim() || undefined,
        area: datos.area.trim() || undefined,
        carpeta: datos.carpeta.trim() || undefined,
        sede: datos.sede.trim() || undefined,
        observacion: datos.observacion.trim() || undefined,
        valor_dia: datos.valor_dia.trim() || undefined,
      });
      toast.success("Salida registrada en estado Reportado.");
      onGuardado();
      onClose();
    } catch (error) {
      const detalle = classifyError(error);
      const erroresDeCampo = extractValidationErrors(detalle);
      Object.entries(erroresDeCampo).forEach(([campo, mensaje]) => {
        if (campo in VALORES_VACIOS) {
          setError(campo as keyof DatosSalida, {
            type: "server",
            message: mensaje,
          });
        }
      });
      // Sin errores por campo → es un ValueError del servicio (ventana CR-9,
      // duplicado CR-1/CR-2, personal sin área…): va al banner.
      if (!Object.keys(erroresDeCampo).length) {
        setErrorServidor(detalle.message);
      }
      logDevelopmentError("Error registrando salida:", error);
    }
  });

  return (
    <Modal isOpen={isOpen} onClose={cerrar} className="max-w-2xl" title={TITULO}>
      <form onSubmit={enviar} noValidate>
        <div className="px-5 pt-5 pb-1 pr-16">
          <h2
            id={TITULO}
            className="text-base font-semibold text-gray-800 dark:text-white/90"
          >
            Nueva salida
          </h2>
        </div>

        <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
          {errorServidor && (
            <Alert variant="error" title="No se pudo registrar" message={errorServidor} />
          )}
          {errorVehiculos && (
            <Alert variant="error" title="No se pudo cargar la flota" message={errorVehiculos} />
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="salida-fecha">
                Fecha <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="fecha_salida"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="salida-fecha"
                    type="date"
                    error={Boolean(errors.fecha_salida)}
                    hint={errors.fecha_salida?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="salida-vehiculo">
                Vehículo <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="vehiculo"
                render={({ field }) => (
                  <select
                    {...field}
                    id="salida-vehiculo"
                    className={
                      "h-11 w-full appearance-none rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
                      "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
                      "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90" +
                      (errors.vehiculo ? " border-error-500" : "")
                    }
                  >
                    <option value="">Seleccione un vehículo</option>
                    {vehiculos.map((vehiculo) => (
                      <option key={vehiculo.id} value={vehiculo.id}>
                        {vehiculo.placa} — {vehiculo.marca}{" "}
                        {vehiculo.referencia ?? ""}
                      </option>
                    ))}
                  </select>
                )}
              />
              {errors.vehiculo?.message && (
                <p className="mt-1.5 text-xs text-error-400">
                  {errors.vehiculo.message}
                </p>
              )}
            </div>
          </div>

          {/* --- Quién sale: empleado de nómina o 'disponible' ------------- */}
          <div>
            <Label>
              Quién sale <span className="text-error-500">*</span>
            </Label>
            <div className="flex gap-2">
              <Controller
                control={control}
                name="disponible"
                render={({ field }) => (
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        field.onChange(false);
                        if (!empleado) setValue("movil_sale", "");
                      }}
                      className={
                        `${CLASES_SEGMENTO} ` +
                        (!field.value
                          ? "border-brand-500 bg-brand-500 text-white"
                          : "border-gray-300 bg-white text-gray-600 hover:border-brand-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300")
                      }
                    >
                      Empleado de nómina
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        field.onChange(true);
                        // La sentinella es lo único que viaja en `movil_sale`.
                        setValue("movil_sale", "disponible", {
                          shouldValidate: true,
                        });
                        setEmpleado(null);
                      }}
                      className={
                        `${CLASES_SEGMENTO} ` +
                        (field.value
                          ? "border-brand-500 bg-brand-500 text-white"
                          : "border-gray-300 bg-white text-gray-600 hover:border-brand-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300")
                      }
                    >
                      Disponible
                    </button>
                  </>
                )}
              />
            </div>

            {!disponible && (
              <div className="mt-3">
                <EmployeeSearchInput
                  label="Empleado que sale"
                  value={empleado}
                  onChange={alElegirEmpleado}
                  error={Boolean(errors.movil_sale)}
                  hint={
                    errors.movil_sale?.message ??
                    "Debe existir en nómina con área y carpeta asignadas."
                  }
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <Label htmlFor="salida-area">
                Área{" "}
                {!disponible && <span className="text-gray-400">(de nómina)</span>}
                {disponible && <span className="text-error-500">*</span>}
              </Label>
              <Controller
                control={control}
                name="area"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="salida-area"
                    type="text"
                    placeholder="OPERACIONES"
                    error={Boolean(errors.area)}
                    hint={errors.area?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="salida-carpeta">Carpeta</Label>
              <Controller
                control={control}
                name="carpeta"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="salida-carpeta"
                    type="text"
                    placeholder="LOGISTICA"
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="salida-sede">Sede</Label>
              <Controller
                control={control}
                name="sede"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="salida-sede"
                    type="text"
                    placeholder="MEDELLIN"
                  />
                )}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <EmployeeSearchInput
                label="Móvil asignada (opcional)"
                value={movilAsignada}
                onChange={(persona) => {
                  setMovilAsignada(persona);
                  setValue("cc_asignada", persona?.cedula ?? "");
                }}
                hint="Personal de nómina asignado al vehículo."
              />
            </div>

            <div>
              <Label htmlFor="salida-valor">Valor del día</Label>
              <Controller
                control={control}
                name="valor_dia"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="salida-valor"
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Se usa la tarifa del vehículo"
                    error={Boolean(errors.valor_dia)}
                    hint={errors.valor_dia?.message}
                  />
                )}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="salida-observacion">Observación</Label>
            <Controller
              control={control}
              name="observacion"
              render={({ field }) => (
                <textarea
                  {...field}
                  id="salida-observacion"
                  rows={2}
                  placeholder="Novedad del reporte (opcional)"
                  className={
                    "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 " +
                    "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
                    "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
                  }
                />
              )}
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
          <Button type="button" variant="outline" onClick={cerrar} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? "Registrando..." : "Registrar salida"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
