// src/modules/transporte/operacion/reporte-fotografico/components/ReporteFotoFormModal.tsx
//
// Alta de reporte fotográfico (F3/B3 · matriz §6).
//
// Reglas del backend (`ReporteFotograficoService.guardar`) que este form
// replica o delega:
//   · La VENTANA de captura 10:00–16:00 la exige el SERVIDOR (`en_ventana`).
//     Aquí solo se pinta el aviso: si el usuario lo ignora, el POST devuelve
//     el mensaje legacy y no se re-implementa la hora en cliente.
//   · La FECHA la elige el servidor (`cls.hoy()`): no hay input de fecha.
//     Un reporte de un día anterior se rechaza con MSG_FECHA_PASADA.
//   · El RESPONSABLE tampoco se elige: se deriva del usuario autenticado
//     (D-A10). Por eso el form no tiene ese campo.
//   · El GATE de agenda se consulta con el pre-chequeo (`validar-agenda/`)
//     para dar feedback ANTES de enviar; el servidor lo vuelve a validar en
//     `guardar()` — aquí es UX, no seguridad.
//   · 1..5 IMÁGENES en `multipart`: el backend usa `getlist("imagenes")`,
//     así que un `[]` en JSON llegaría como un solo string.
//   · La placa se RESUELVE contra el vehículo activo (`vehiculo-placa/`) para
//     confirmar al usuario qué móvil está reportando.
//
// Mejora sobre el legacy: el pre-chequeo de agenda y el de OT-específica se
// muestran en vivo; en el PHP solo se veían al enviar y perdías el reporte.

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import { Modal } from "@/components/ui/modal";
import { classifyError, extractValidationErrors } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type {
  ResultadoAgendaReporte,
  VehiculoResuelto,
} from "@/types/transporte.types";
import { hoyISO } from "../reporteFotoView.utils";

const TITULO = "reporte-foto-form-titulo";

/** Máximo de evidencias que acepta el backend (CR del reporte fotográfico). */
export const MAX_IMAGENES = 5;
const TAMANO_MAX_MB = 10;

const EsquemaReporte = z.object({
  placa: z
    .string()
    .trim()
    .min(1, "La placa es obligatoria.")
    .max(10, "Máximo 10 caracteres."),
  ot_actividad: z.string().trim().max(200, "Máximo 200 caracteres."),
  observaciones: z.string().trim().max(2000, "Máximo 2000 caracteres."),
});

type DatosReporte = z.infer<typeof EsquemaReporte>;

const VALORES_VACIOS: DatosReporte = {
  placa: "",
  ot_actividad: "",
  observaciones: "",
};

interface ReporteFotoFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGuardado: () => void;
}

const CLASES_FOTO =
  "hidden h-0 w-0 overflow-hidden opacity-0 absolute";

export const ReporteFotoFormModal = ({
  isOpen,
  onClose,
  onGuardado,
}: ReporteFotoFormModalProps) => {
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [vehiculo, setVehiculo] = useState<VehiculoResuelto | null>(null);
  const [errorVehiculo, setErrorVehiculo] = useState<string | null>(null);
  const [agenda, setAgenda] = useState<ResultadoAgendaReporte | null>(null);
  const [cargandoAgenda, setCargandoAgenda] = useState(false);

  // Las imágenes viven FUERA de RHF: el input file no se puede controlar y
  // además necesitamos las previsualizaciones.
  const [imagenes, setImagenes] = useState<File[]>([]);
  const [previsualizaciones, setPrevisualizaciones] = useState<string[]>([]);
  const [errorImagenes, setErrorImagenes] = useState<string | null>(null);

  const [location, setLocation] = useState<Record<string, unknown> | null>(
    null,
  );
  const [capturandoUbicacion, setCapturandoUbicacion] = useState(false);

  const inputArchivosRef = useRef<HTMLInputElement>(null);
  const previsualizacionesRef = useRef<string[]>([]);

  const {
    control,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<DatosReporte>({
    // `as any` por la fricción de tipos zod-v4 ↔ @hookform/resolvers v5
    // (mismo patrón que SalidaFormModal y ConductorFormModal).
    resolver: zodResolver(EsquemaReporte) as never,
    defaultValues: { ...VALORES_VACIOS },
  });

  const placa = watch("placa");
  const otActividad = watch("ot_actividad");

  /** Libera los object-URL al desmontar o al cambiar la lista. */
  const limpiarPrevisualizaciones = useCallback(() => {
    previsualizacionesRef.current.forEach((url) => URL.revokeObjectURL(url));
    previsualizacionesRef.current = [];
    setPrevisualizaciones([]);
  }, []);

  useEffect(() => {
    previsualizacionesRef.current = previsualizaciones;
  }, [previsualizaciones]);

  useEffect(() => () => limpiarPrevisualizaciones(), [limpiarPrevisualizaciones]);

  /** Al abrir: estado limpio. */
  useEffect(() => {
    if (isOpen) {
      reset({ ...VALORES_VACIOS });
      setVehiculo(null);
      setErrorVehiculo(null);
      setAgenda(null);
      setImagenes([]);
      setErrorImagenes(null);
      setLocation(null);
      setErrorServidor(null);
      limpiarPrevisualizaciones();
    }
  }, [isOpen, reset, limpiarPrevisualizaciones]);

  // -------------------------------------------------------------------------
  // Resolución de placa
  // -------------------------------------------------------------------------
  const resolverPlaca = useCallback(async (valorPlaca: string) => {
    const placaLimpia = valorPlaca.trim().toUpperCase();
    if (!placaLimpia) {
      setVehiculo(null);
      setErrorVehiculo(null);
      return;
    }
    try {
      const resultado = await transporteService.getVehiculoPorPlaca(
        placaLimpia,
      );
      setVehiculo(resultado);
      setErrorVehiculo(null);
    } catch (error) {
      setVehiculo(null);
      // No es bloqueante: el servidor valida de nuevo al guardar. Aquí solo
      // se avisa para que no se reporte una placa que no existe.
      const apiError = error as { message?: string };
      setErrorVehiculo(
        apiError?.message ?? `No se encontró el vehículo ${placaLimpia}.`,
      );
    }
  }, []);

  // -------------------------------------------------------------------------
  // Pre-chequeo de agenda (y OT-específica) — feedback ANTES de enviar
  // -------------------------------------------------------------------------
  const consultarAgenda = useCallback(
    async (valorPlaca: string, valorOt: string) => {
      // Sin placa no tiene sentido el chequeo: el reporte no se puede guardar.
      if (!valorPlaca.trim()) {
        setAgenda(null);
        return;
      }
      setCargandoAgenda(true);
      try {
        const resultado = await transporteService.validarAgendaReporte({
          fecha: hoyISO(),
          ot_actividad: valorOt.trim() || undefined,
        });
        setAgenda(resultado);
      } catch (error) {
        // Un fallo del pre-chequeo NO impide enviar: quien decide es `guardar`.
        logDevelopmentError("No fue posible consultar la agenda:", error);
        setAgenda(null);
      } finally {
        setCargandoAgenda(false);
      }
    },
    [],
  );

  useEffect(() => {
    void consultarAgenda(placa, otActividad);
  }, [placa, otActividad, consultarAgenda]);

  // -------------------------------------------------------------------------
  // Imágenes
  // -------------------------------------------------------------------------
  const agregarImagenes = useCallback(
    (lista: FileList | null) => {
      if (!lista || lista.length === 0) return;

      setErrorImagenes(null);
      const nuevas = Array.from(lista);

      const excedeTamano = nuevas.find(
        (archivo) => archivo.size > TAMANO_MAX_MB * 1024 * 1024,
      );
      if (excedeTamano) {
        setErrorImagenes(`"${excedeTamano.name}" supera ${TAMANO_MAX_MB} MB.`);
        return;
      }

      const total = imagenes.length + nuevas.length;
      if (total > MAX_IMAGENES) {
        setErrorImagenes(
          `El reporte admite máximo ${MAX_IMAGENES} imágenes (vas por ${total}).`,
        );
        return;
      }

      const urls = nuevas.map((archivo) => URL.createObjectURL(archivo));
      setImagenes((prev) => [...prev, ...nuevas]);
      setPrevisualizaciones((prev) => [...prev, ...urls]);
    },
    [imagenes.length],
  );

  const quitarImagen = useCallback(
    (indice: number) => {
      const url = previsualizaciones[indice];
      if (url) URL.revokeObjectURL(url);
      setImagenes((prev) => prev.filter((_, i) => i !== indice));
      setPrevisualizaciones((prev) => prev.filter((_, i) => i !== indice));
      setErrorImagenes(null);
    },
    [previsualizaciones],
  );

  // -------------------------------------------------------------------------
  // Geolocalización (opcional, como en el kiosco legacy)
  // -------------------------------------------------------------------------
  const capturarUbicacion = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setErrorImagenes("Este navegador no permite obtener la ubicación.");
      return;
    }
    setCapturandoUbicacion(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          precision: Math.round(pos.coords.accuracy),
        });
        setCapturandoUbicacion(false);
      },
      (error) => {
        logDevelopmentError("No fue posible capturar la ubicación:", error);
        setCapturandoUbicacion(false);
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }, []);

  // -------------------------------------------------------------------------
  // Envío
  // -------------------------------------------------------------------------
  const cerrar = useCallback(() => {
    if (isSubmitting) return;
    onClose();
  }, [isSubmitting, onClose]);

  const enviar = handleSubmit(async (datos) => {
    if (imagenes.length === 0) {
      setErrorImagenes("Adjunta al menos una imagen de evidencia.");
      return;
    }
    setErrorImagenes(null);
    setErrorServidor(null);

    try {
      await transporteService.guardarReporteFotografico({
        placa: datos.placa.trim().toUpperCase(),
        imagenes,
        ot_actividad: datos.ot_actividad.trim() || undefined,
        observaciones: datos.observaciones.trim() || undefined,
        location: location ?? undefined,
      });
      toast.success("Reporte fotográfico registrado.");
      onGuardado();
      onClose();
    } catch (error) {
      const detalle = classifyError(error);
      const erroresDeCampo = extractValidationErrors(detalle);
      Object.entries(erroresDeCampo).forEach(([campo, mensaje]) => {
        if (campo in VALORES_VACIOS) {
          setError(campo as keyof DatosReporte, {
            type: "server",
            message: mensaje,
          });
        }
      });
      // Sin errores por campo → es un ValueError del servicio (fuera de la
      // ventana, sin agenda del día, OT que no coincide…): va al banner.
      if (!Object.keys(erroresDeCampo).length) {
        setErrorServidor(detalle.message);
      }
      logDevelopmentError("Error guardando el reporte:", error);
    }
  });

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  const enVentana = (() => {
    const hora = new Date().getHours();
    return hora >= 10 && hora <= 16;
  })();

  return (
    <Modal isOpen={isOpen} onClose={cerrar} className="max-w-2xl" title={TITULO}>
      <form onSubmit={enviar} noValidate>
        <div className="px-5 pt-5 pb-1 pr-16">
          <h2
            id={TITULO}
            className="text-base font-semibold text-gray-800 dark:text-white/90"
          >
            Nuevo reporte fotográfico
          </h2>
        </div>

        <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
          {errorServidor && (
            <Alert
              variant="error"
              title="No se pudo registrar"
              message={errorServidor}
            />
          )}

          {/* --- Ventana de captura (solo aviso: lo decide el servidor) --- */}
          {!enVentana && (
            <Alert
              variant="warning"
              title="Fuera de la ventana de captura"
              message="La captura está permitida entre las 10:00 y las 16:00 (hora Colombia). El servidor puede rechazar el reporte."
            />
          )}

          {/* --- Pre-chequeo de agenda --- */}
          {agenda && !agenda.tiene_agenda && (
            <Alert
              variant="error"
              title="Sin agenda para hoy"
              message={
                agenda.msg ||
                "El responsable no tiene agenda registrada para hoy; el servidor rechazará el reporte."
              }
            />
          )}
          {agenda?.ot && !agenda.ot.valida && (
            <Alert
              variant="error"
              title="La OT no coincide con la agenda"
              message={agenda.ot.msg}
            />
          )}
          {agenda?.ot && agenda.ot.valida && (
            <Alert
              variant="success"
              title="OT verificada"
              message={`Coincide con la agenda del día: ${agenda.ot.ot}`}
            />
          )}

          {/* --- Placa --- */}
          <div>
            <Label htmlFor="reporte-placa">
              Placa <span className="text-error-500">*</span>
            </Label>
            <Controller
              control={control}
              name="placa"
              render={({ field }) => (
                <Input
                  {...field}
                  id="reporte-placa"
                  type="text"
                  placeholder="ABC123"
                  error={Boolean(errors.placa)}
                  hint={errors.placa?.message}
                  onChange={(e) => {
                    field.onChange(e.target.value.toUpperCase());
                  }}
                  onBlur={(e) => void resolverPlaca(e.target.value)}
                />
              )}
            />
            {vehiculo && (
              <p className="mt-1 text-xs text-success-500">
                {vehiculo.marca} {vehiculo.referencia} · {vehiculo.ciudad}
              </p>
            )}
            {errorVehiculo && (
              <p className="mt-1 text-xs text-error-500">{errorVehiculo}</p>
            )}
          </div>

          {/* --- OT / actividad --- */}
          <div>
            <Label htmlFor="reporte-ot">OT / Actividad</Label>
            <Controller
              control={control}
              name="ot_actividad"
              render={({ field }) => (
                <Input
                  {...field}
                  id="reporte-ot"
                  type="text"
                  placeholder="Opcional — se valida contra la agenda del día"
                  error={Boolean(errors.ot_actividad)}
                  hint={errors.ot_actividad?.message}
                />
              )}
            />
          </div>

          {/* --- Imágenes --- */}
          <div>
            <Label>
              Evidencias <span className="text-error-500">*</span>{" "}
              <span className="text-xs font-normal text-gray-400">
                (mínimo 1, máximo {MAX_IMAGENES})
              </span>
            </Label>

            {previsualizaciones.length > 0 && (
              <div className="mb-2 grid grid-cols-5 gap-2">
                {previsualizaciones.map((url, i) => (
                  <div
                    key={url}
                    className="group relative aspect-square overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={url}
                      alt={`Evidencia ${i + 1}`}
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => quitarImagen(i)}
                      aria-label={`Quitar imagen ${i + 1}`}
                      className="absolute top-0.5 right-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-error-500 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <input
              ref={inputArchivosRef}
              type="file"
              accept="image/*"
              multiple
              className={CLASES_FOTO}
              onChange={(e) => {
                agregarImagenes(e.target.files);
                // Permite volver a elegir el mismo archivo tras quitarlo.
                e.target.value = "";
              }}
            />

            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => inputArchivosRef.current?.click()}
            >
              {imagenes.length === 0 ? "Adjuntar imágenes" : "Añadir más"}
            </Button>

            {errorImagenes && (
              <p className="mt-1 text-xs text-error-500">{errorImagenes}</p>
            )}
          </div>

          {/* --- Observaciones --- */}
          <div>
            <Label htmlFor="reporte-observaciones">Observaciones</Label>
            <Controller
              control={control}
              name="observaciones"
              render={({ field }) => (
                <textarea
                  {...field}
                  id="reporte-observaciones"
                  rows={3}
                  placeholder="Opcional"
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
                />
              )}
            />
            {errors.observaciones && (
              <p className="mt-1 text-xs text-error-500">
                {errors.observaciones.message}
              </p>
            )}
          </div>

          {/* --- Ubicación (opcional) --- */}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={capturarUbicacion}
              disabled={capturandoUbicacion}
            >
              {capturandoUbicacion
                ? "Capturando..."
                : location
                  ? "Ubicación capturada"
                  : "Adjuntar ubicación"}
            </Button>
            {location && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {String(location.lat)},{" "}
                {String(location.lon)} (±{String(location.precision)} m)
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-5 py-4">
          <Button type="button" size="sm" variant="outline" onClick={cerrar}>
            Cancelar
          </Button>
          <Button type="submit" size="sm" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? "Guardando..." : "Guardar reporte"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
