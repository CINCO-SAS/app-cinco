// src/modules/transporte/duenos/components/DuenoFormModal.tsx
//
// Modal para Alta y Edición de datos básicos de Dueño de Vehículos.

"use client";

import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Checkbox from "@/components/form/input/Checkbox";
import { Modal } from "@/components/ui/modal";
import { classifyError, extractValidationErrors } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { DuenoPayload } from "@/types/transporte.types";

const EsquemaDueno = z.object({
  cedula: z
    .string()
    .trim()
    .min(1, "La cédula o NIT es obligatorio.")
    .max(20, "Máximo 20 caracteres."),
  nombre: z
    .string()
    .trim()
    .min(1, "El nombre del dueño es obligatorio.")
    .max(150, "Máximo 150 caracteres."),
  celular: z
    .string()
    .trim()
    .min(1, "El teléfono o celular es obligatorio.")
    .max(30, "Máximo 30 caracteres."),
  activo: z.boolean(),
});

type DatosDuenoForm = z.infer<typeof EsquemaDueno>;

const VALORES_INICIALES: DatosDuenoForm = {
  cedula: "",
  nombre: "",
  celular: "",
  activo: true,
};

interface DuenoFormModalProps {
  isOpen: boolean;
  duenoId: number | null;
  onClose: () => void;
  onGuardado: () => void;
}

export const DuenoFormModal = ({
  isOpen,
  duenoId,
  onClose,
  onGuardado,
}: DuenoFormModalProps) => {
  const esEdicion = duenoId !== null && duenoId > 0;
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<DatosDuenoForm>({
    resolver: zodResolver(EsquemaDueno),
    defaultValues: VALORES_INICIALES,
  });

  useEffect(() => {
    if (!isOpen) return;
    setErrorServidor(null);

    if (esEdicion && duenoId) {
      setCargandoDetalle(true);
      transporteService
        .getDueno(duenoId)
        .then((d) => {
          reset({
            cedula: d.cedula,
            nombre: d.nombre,
            celular: d.celular ?? "",
            activo: d.activo,
          });
        })
        .catch((err) => {
          const clasificado = classifyError(err);
          setErrorServidor(clasificado.message);
          logDevelopmentError("Error cargando dueño:", err);
        })
        .finally(() => setCargandoDetalle(false));
    } else {
      reset(VALORES_INICIALES);
    }
  }, [isOpen, esEdicion, duenoId, reset]);

  const enviar = handleSubmit(async (datos: DatosDuenoForm) => {
    setErrorServidor(null);
    const payload: DuenoPayload = {
      cedula: datos.cedula.trim(),
      nombre: datos.nombre.trim(),
      celular: datos.celular.trim() || null,
      activo: datos.activo,
    };

    try {
      if (esEdicion && duenoId) {
        await transporteService.actualizarDueno(duenoId, payload);
        toast.success(`Dueño ${payload.nombre} actualizado con éxito.`);
      } else {
        await transporteService.crearDueno(payload);
        toast.success(`Dueño ${payload.nombre} registrado con éxito.`);
      }
      onGuardado();
      onClose();
    } catch (err) {
      const detalle = classifyError(err);
      const erroresDeCampo = extractValidationErrors(detalle);

      Object.entries(erroresDeCampo).forEach(([campo, mensaje]) => {
        if (campo in datos) {
          setError(campo as keyof DatosDuenoForm, {
            type: "server",
            message: mensaje,
          });
        }
      });

      if (!Object.keys(erroresDeCampo).length) {
        setErrorServidor(detalle.message);
      }
      logDevelopmentError("Error guardando dueño:", err);
    }
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!isSubmitting) onClose();
      }}
      className="max-w-lg"
      title="dueno-form-titulo"
    >
      <div className="px-6 pt-6 pb-2 pr-16 border-b border-gray-200 dark:border-gray-800">
        <h2
          id="dueno-form-titulo"
          className="text-lg font-bold text-gray-800 dark:text-white/90"
        >
          {esEdicion ? "Editar Dueño de Vehículos" : "Nuevo Dueño de Vehículos"}
        </h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {esEdicion
            ? "Actualiza los datos personales y de contacto del propietario."
            : "Registra a un nuevo propietario para asignarle vehículos y cuentas bancarias."}
        </p>
      </div>

      {cargandoDetalle ? (
        <div className="p-8 text-center text-sm text-gray-500">
          Cargando información del dueño...
        </div>
      ) : (
        <form onSubmit={enviar}>
          <div className="max-h-[70vh] overflow-y-auto px-6 py-4 space-y-4">
            {errorServidor && (
              <Alert
                variant="error"
                title="No fue posible guardar"
                message={errorServidor}
              />
            )}

            <div>
              <Label htmlFor="cedula">
                Cédula / NIT <span className="text-error-500">*</span>
              </Label>
              <Input
                id="cedula"
                placeholder="Ej. 1020304050"
                disabled={isSubmitting}
                error={Boolean(errors.cedula)}
                hint={errors.cedula?.message}
                {...register("cedula")}
              />
            </div>

            <div>
              <Label htmlFor="nombre">
                Nombre Completo o Razón Social <span className="text-error-500">*</span>
              </Label>
              <Input
                id="nombre"
                placeholder="Nombre del propietario"
                disabled={isSubmitting}
                error={Boolean(errors.nombre)}
                hint={errors.nombre?.message}
                {...register("nombre")}
              />
            </div>

            <div>
              <Label htmlFor="celular">
                Teléfono / Celular <span className="text-error-500">*</span>
              </Label>
              <Input
                id="celular"
                placeholder="Ej. 3001234567"
                disabled={isSubmitting}
                error={Boolean(errors.celular)}
                hint={errors.celular?.message}
                {...register("celular")}
              />
            </div>

            <div className="pt-2">
              <Controller
                name="activo"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="activo"
                    label="Propietario activo en la operación"
                    checked={field.value}
                    onChange={field.onChange}
                    disabled={isSubmitting}
                  />
                )}
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-800">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting || cargandoDetalle}
            >
              {isSubmitting
                ? "Guardando..."
                : esEdicion
                  ? "Actualizar Dueño"
                  : "Registrar Dueño"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
