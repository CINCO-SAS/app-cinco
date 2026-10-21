// src/modules/transporte/conductores/components/ConductorFormModal.tsx
//
// Alta y edición de conductores (F2 · §5.4).
//
// Reglas del backend que este form replica en cliente:
//   · `cedula` obligatoria y única (el 400 "Ya existe…" llega del servidor).
//   · `fecha_ingreso` obligatoria.
//   · `fecha_nacimiento` no puede ser posterior a `fecha_ingreso`.
//   · `fecha_egreso` es de SOLO LECTURA: solo se setea al inactivar
//     (el serializer la tiene en `read_only_fields`). Por eso no aparece aquí.
//   · `activo` tampoco se edita: se cambia con la acción `inactivar`.

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
import Select from "@/components/form/Select";
import { Modal } from "@/components/ui/modal";
import { classifyError, extractValidationErrors } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import {
  CATEGORIAS_LICENCIA,
  TIPOS_VINCULACION,
  type CategoriaLicencia,
} from "@/types/transporte.types";
import { ETIQUETAS_VINCULACION } from "../conductoresView.utils";

const EsquemaConductor = z
  .object({
    cedula: z
      .string()
      .trim()
      .min(1, "La cédula es obligatoria.")
      .max(20, "La cédula no puede superar 20 caracteres."),
    nombre_completo: z
      .string()
      .trim()
      .min(1, "El nombre completo es obligatorio.")
      .max(150, "El nombre no puede superar 150 caracteres."),
    celular: z
      .string()
      .trim()
      .min(1, "El celular es obligatorio.")
      .max(30, "El celular no puede superar 30 caracteres."),
    tipo_vinculacion: z.enum(TIPOS_VINCULACION),
    fecha_ingreso: z
      .string()
      .min(1, "La fecha de ingreso es obligatoria."),
    fecha_nacimiento: z.string(),
    licencia_categoria: z.string(),
    licencia_vencimiento: z.string(),
    direccion: z.string().trim().max(150, "Máximo 150 caracteres."),
    barrio: z.string().trim().max(100, "Máximo 100 caracteres."),
  })
  .refine(
    (datos) =>
      !datos.fecha_nacimiento ||
      !datos.fecha_ingreso ||
      datos.fecha_nacimiento <= datos.fecha_ingreso,
    {
      message: "La fecha de nacimiento no puede ser posterior a la fecha de ingreso.",
      path: ["fecha_nacimiento"],
    },
  );

type DatosConductor = z.infer<typeof EsquemaConductor>;

const VALORES_VACIOS: DatosConductor = {
  cedula: "",
  nombre_completo: "",
  celular: "",
  tipo_vinculacion: "EXTERNO",
  fecha_ingreso: "",
  fecha_nacimiento: "",
  licencia_categoria: "",
  licencia_vencimiento: "",
  direccion: "",
  barrio: "",
};

const A_PAYLOAD = (datos: DatosConductor) => ({
  cedula: datos.cedula.trim(),
  nombre_completo: datos.nombre_completo.trim(),
  celular: datos.celular.trim(),
  tipo_vinculacion: datos.tipo_vinculacion,
  fecha_ingreso: datos.fecha_ingreso,
  fecha_nacimiento: datos.fecha_nacimiento || null,
  licencia_categoria: (datos.licencia_categoria || null) as CategoriaLicencia | null,
  licencia_vencimiento: datos.licencia_vencimiento || null,
  direccion: datos.direccion.trim() || null,
  barrio: datos.barrio.trim() || null,
});

interface ConductorFormModalProps {
  isOpen: boolean;
  /** `null` → alta; número → edición. */
  conductorId: number | null;
  onClose: () => void;
  onGuardado: () => void;
}

export const ConductorFormModal = ({
  isOpen,
  conductorId,
  onClose,
  onGuardado,
}: ConductorFormModalProps) => {
  const esEdicion = conductorId !== null;
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorDetalle, setErrorDetalle] = useState<string | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<DatosConductor>({
    // `as any` por la fricción de tipos zod-v4 ↔ @hookform/resolvers v5
    // (mismo patrón que ActividadForm.hooks.ts).
    resolver: zodResolver(EsquemaConductor) as never,
    defaultValues: VALORES_VACIOS,
  });

  // -------------------------------------------------------------------------
  // Al abrir: alta → valores vacíos; edición → detalle completo del servidor
  // (el listado no trae dirección ni fechas de ingreso/nacimiento).
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!isOpen) return;

    reset(VALORES_VACIOS);
    setErrorServidor(null);
    setErrorDetalle(null);

    if (conductorId === null) return;

    let cancelado = false;
    setCargandoDetalle(true);

    void (async () => {
      try {
        const conductor = await transporteService.getConductor(conductorId);
        if (cancelado) return;
        reset({
          cedula: conductor.cedula,
          nombre_completo: conductor.nombre_completo,
          celular: conductor.celular,
          tipo_vinculacion: conductor.tipo_vinculacion,
          fecha_ingreso: conductor.fecha_ingreso ?? "",
          fecha_nacimiento: conductor.fecha_nacimiento ?? "",
          licencia_categoria: conductor.licencia_categoria ?? "",
          licencia_vencimiento: conductor.licencia_vencimiento ?? "",
          direccion: conductor.direccion ?? "",
          barrio: conductor.barrio ?? "",
        });
      } catch (error) {
        if (cancelado) return;
        const detalle = classifyError(error);
        setErrorDetalle(detalle.message);
        logDevelopmentError("Error cargando conductor:", error);
      } finally {
        if (!cancelado) setCargandoDetalle(false);
      }
    })();

    return () => {
      cancelado = true;
    };
  }, [isOpen, conductorId, reset]);

  const cerrar = useCallback(() => {
    if (isSubmitting) return;
    onClose();
  }, [isSubmitting, onClose]);

  const enviar = handleSubmit(async (datos) => {
    setErrorServidor(null);
    try {
      const payload = A_PAYLOAD(datos);
      if (conductorId === null) {
        await transporteService.crearConductor(payload);
        toast.success("Conductor registrado correctamente.");
      } else {
        await transporteService.actualizarConductor(conductorId, payload);
        toast.success("Conductor actualizado correctamente.");
      }
      onGuardado();
      onClose();
    } catch (error) {
      const detalle = classifyError(error);
      const erroresDeCampo = extractValidationErrors(detalle);

      Object.entries(erroresDeCampo).forEach(([campo, mensaje]) => {
        setError(campo as keyof DatosConductor, {
          type: "server",
          message: mensaje,
        });
      });

      // Si el backend no devolvió errores por campo (p. ej. el
      // `{ok:false, error, detail}` de los ValueError del servicio),
      // el mensaje general va en el banner.
      if (!Object.keys(erroresDeCampo).length) {
        setErrorServidor(detalle.message);
      }

      logDevelopmentError("Error guardando conductor:", error);
    }
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={cerrar}
      className="max-w-2xl"
      // `title` NO es texto visible: Modal lo usa como `aria-labelledby`, apuntando al h2.
      title="conductor-form-titulo"
    >
      <form onSubmit={enviar} noValidate>
        {/*
          Encabezado visible: `Modal` NO renderiza la prop `title` (solo la usa
          para aria-labelledby), su botón de cerrar va absoluto en la esquina
          (pr-16) y el padding horizontal es responsabilidad nuestro porque
          `Modal` solo aporta `rounded-3xl bg-white`.
        */}
        <div className="px-5 pt-5 pb-1 pr-16">
          <h2
            id="conductor-form-titulo"
            className="text-base font-semibold text-gray-800 dark:text-white/90"
          >
            {esEdicion ? "Editar conductor" : "Nuevo conductor"}
          </h2>
        </div>

        <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
          {errorServidor && (
            <Alert variant="error" title="No se pudo guardar" message={errorServidor} />
          )}
          {errorDetalle && (
            <Alert
              variant="error"
              title="No se pudo cargar el conductor"
              message={errorDetalle}
            />
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="conductor-cedula">
                Cédula <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="cedula"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-cedula"
                    type="text"
                    inputMode="numeric"
                    placeholder="N.º de documento"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.cedula)}
                    hint={errors.cedula?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-nombre">
                Nombre completo <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="nombre_completo"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-nombre"
                    type="text"
                    placeholder="Nombre y apellidos"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.nombre_completo)}
                    hint={errors.nombre_completo?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-celular">
                Celular <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="celular"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-celular"
                    type="tel"
                    inputMode="tel"
                    placeholder="Celular de contacto"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.celular)}
                    hint={errors.celular?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-vinculo">
                Tipo de vínculo <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="tipo_vinculacion"
                render={({ field }) => (
                  <Select
                    {...field}
                    value={field.value}
                    options={TIPOS_VINCULACION.map((valor) => ({
                      value: valor,
                      label: ETIQUETAS_VINCULACION[valor],
                    }))}
                    placeholder=""
                    disabled={cargandoDetalle}
                    error={Boolean(errors.tipo_vinculacion)}
                    hint={errors.tipo_vinculacion?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-ingreso">
                Fecha de ingreso <span className="text-error-500">*</span>
              </Label>
              <Controller
                control={control}
                name="fecha_ingreso"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-ingreso"
                    type="date"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.fecha_ingreso)}
                    hint={errors.fecha_ingreso?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-nacimiento">Fecha de nacimiento</Label>
              <Controller
                control={control}
                name="fecha_nacimiento"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-nacimiento"
                    type="date"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.fecha_nacimiento)}
                    hint={errors.fecha_nacimiento?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-licencia-cat">Categoría de licencia</Label>
              {/*
                `<select>` nativo y no el componente Select: ese componente
                renderiza su placeholder como opción `disabled`, lo que
                impediría volver a "sin licencia" en un campo OPCIONAL.
              */}
              <Controller
                control={control}
                name="licencia_categoria"
                render={({ field }) => (
                  <div>
                    <select
                      {...field}
                      id="conductor-licencia-cat"
                      disabled={cargandoDetalle}
                      className={
                        "h-8 w-full rounded-lg border appearance-none px-2 py-0.5 text-sm shadow-theme-xs " +
                        "focus:outline-hidden focus:ring-3 dark:bg-gray-900 dark:text-white/90 " +
                        "dark:focus:border-brand-800 " +
                        (errors.licencia_categoria
                          ? "border-error-500 text-error-800 dark:border-error-500 dark:text-error-400"
                          : "border-gray-300 text-gray-800 focus:border-brand-300 focus:ring-brand-500/10 " +
                            "dark:border-gray-700 dark:focus:border-brand-800")
                      }
                    >
                      <option value="">Sin licencia</option>
                      {CATEGORIAS_LICENCIA.map((valor) => (
                        <option key={valor} value={valor}>
                          {valor}
                        </option>
                      ))}
                    </select>
                    {errors.licencia_categoria?.message && (
                      <p className="mt-1.5 text-xs text-error-400">
                        {errors.licencia_categoria.message}
                      </p>
                    )}
                  </div>
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-licencia-vence">Vencimiento de licencia</Label>
              <Controller
                control={control}
                name="licencia_vencimiento"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-licencia-vence"
                    type="date"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.licencia_vencimiento)}
                    hint={errors.licencia_vencimiento?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-direccion">Dirección</Label>
              <Controller
                control={control}
                name="direccion"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-direccion"
                    type="text"
                    placeholder="Dirección de residencia"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.direccion)}
                    hint={errors.direccion?.message}
                  />
                )}
              />
            </div>

            <div>
              <Label htmlFor="conductor-barrio">Barrio</Label>
              <Controller
                control={control}
                name="barrio"
                render={({ field }) => (
                  <Input
                    {...field}
                    id="conductor-barrio"
                    type="text"
                    placeholder="Barrio de residencia"
                    disabled={cargandoDetalle}
                    error={Boolean(errors.barrio)}
                    hint={errors.barrio?.message}
                  />
                )}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
          <Button type="button" variant="outline" onClick={cerrar} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting || cargandoDetalle}>
            {isSubmitting ? "Guardando..." : "Guardar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
