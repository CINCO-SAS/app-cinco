// src/modules/transporte/flota/components/VehiculoFormModal.tsx
//
// Modal para Alta y Edición de Vehículos (F2 · §5.3 / §5.4).
//
// Formulario tipado con Zod, campos alineados a string/boolean para
// compatibilidad con react-hook-form y normalización en A_PAYLOAD.

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
import Select from "@/components/form/Select";
import Checkbox from "@/components/form/input/Checkbox";
import { Modal } from "@/components/ui/modal";
import { classifyError, extractValidationErrors } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import {
  CIUDADES_OPERACION,
  TIPOS_CONTRATO,
  TIPOS_VEHICULO,
  type CiudadOperacion,
  type ConductorListado,
  type TipoContrato,
  type TipoVehiculo,
  type VehiculoPayload,
} from "@/types/transporte.types";
import {
  ETIQUETAS_TIPO_CONTRATO,
  ETIQUETAS_TIPO_VEHICULO,
} from "../flotaView.utils";

const anioActual = new Date().getFullYear();

const EsquemaVehiculo = z.object({
  placa: z
    .string()
    .trim()
    .min(5, "La placa debe tener al menos 5 caracteres.")
    .max(10, "La placa no puede exceder 10 caracteres."),
  tipo_vehiculo: z.enum(TIPOS_VEHICULO),
  tipo_contrato: z.enum(TIPOS_CONTRATO),
  marca: z
    .string()
    .trim()
    .min(1, "La marca es obligatoria.")
    .max(50, "Máximo 50 caracteres."),
  referencia: z.string().trim().max(50, "Máximo 50 caracteres."),
  modelo_anio: z
    .string()
    .trim()
    .min(4, "Año de 4 dígitos.")
    .refine((val) => {
      const num = Number(val);
      return !isNaN(num) && num >= 1980 && num <= anioActual + 2;
    }, `El año debe estar entre 1980 y ${anioActual + 2}.`),
  color: z.string().trim().max(30, "Máximo 30 caracteres."),
  ciudad_operacion: z.string(),
  nombre_propietario: z
    .string()
    .trim()
    .min(1, "El nombre del propietario es obligatorio.")
    .max(150, "Máximo 150 caracteres."),
  cedula_propietario: z
    .string()
    .trim()
    .min(1, "La cédula del propietario es obligatoria.")
    .max(20, "Máximo 20 caracteres."),
  celular_propietario: z.string().trim().max(30, "Máximo 30 caracteres."),
  conductor_habitual: z.string(),
  fecha_ingreso: z.string(),
  fecha_soat: z.string(),
  fecha_cda: z.string(),
  valor_dia_base: z.string().refine((val) => {
    const num = Number(val);
    return !isNaN(num) && num >= 0;
  }, "El valor día debe ser un número mayor o igual a 0."),
  municipio_matricula: z.string().trim().max(100, "Máximo 100 caracteres."),
  numero_vin: z.string().trim().max(50, "Máximo 50 caracteres."),
  numero_motor: z.string().trim().max(50, "Máximo 50 caracteres."),
  tipo_combustible: z.string().trim().max(30, "Máximo 30 caracteres."),
  kilometraje: z.string().refine((val) => {
    if (!val) return true;
    const num = Number(val);
    return !isNaN(num) && num >= 0;
  }, "Kilometraje no válido."),
  cajon: z.boolean(),
  logos: z.boolean(),
});

type DatosVehiculoForm = z.infer<typeof EsquemaVehiculo>;

const VALORES_INICIALES: DatosVehiculoForm = {
  placa: "",
  tipo_vehiculo: "CAMIONETA",
  tipo_contrato: "PROPIO",
  marca: "",
  referencia: "",
  modelo_anio: String(anioActual),
  color: "",
  ciudad_operacion: "MEDELLIN",
  nombre_propietario: "",
  cedula_propietario: "",
  celular_propietario: "",
  conductor_habitual: "",
  fecha_ingreso: new Date().toISOString().slice(0, 10),
  fecha_soat: "",
  fecha_cda: "",
  valor_dia_base: "0",
  municipio_matricula: "",
  numero_vin: "",
  numero_motor: "",
  tipo_combustible: "DIESEL",
  kilometraje: "0",
  cajon: false,
  logos: false,
};

const A_PAYLOAD = (datos: DatosVehiculoForm): VehiculoPayload => ({
  placa: datos.placa.trim().toUpperCase(),
  tipo_vehiculo: datos.tipo_vehiculo,
  tipo_contrato: datos.tipo_contrato,
  marca: datos.marca.trim(),
  referencia: datos.referencia.trim() || null,
  modelo_anio: Number(datos.modelo_anio),
  color: datos.color.trim() || null,
  ciudad_operacion: (datos.ciudad_operacion as CiudadOperacion) || null,
  nombre_propietario: datos.nombre_propietario.trim(),
  cedula_propietario: datos.cedula_propietario.trim(),
  celular_propietario: datos.celular_propietario.trim() || null,
  conductor_habitual: datos.conductor_habitual ? Number(datos.conductor_habitual) : null,
  fecha_ingreso: datos.fecha_ingreso || null,
  fecha_soat: datos.fecha_soat || null,
  fecha_cda: datos.fecha_cda || null,
  valor_dia_base: datos.valor_dia_base ? String(Number(datos.valor_dia_base)) : "0",
  municipio_matricula: datos.municipio_matricula.trim() || null,
  numero_vin: datos.numero_vin.trim() || null,
  numero_motor: datos.numero_motor.trim() || null,
  tipo_combustible: datos.tipo_combustible.trim() || null,
  kilometraje: datos.kilometraje ? Number(datos.kilometraje) : null,
  cajon: datos.cajon,
  logos: datos.logos,
});

interface VehiculoFormModalProps {
  isOpen: boolean;
  vehiculoId: number | null;
  onClose: () => void;
  onGuardado: () => void;
}

export const VehiculoFormModal = ({
  isOpen,
  vehiculoId,
  onClose,
  onGuardado,
}: VehiculoFormModalProps) => {
  const esEdicion = vehiculoId !== null && vehiculoId > 0;
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [conductores, setConductores] = useState<ConductorListado[]>([]);

  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<DatosVehiculoForm>({
    resolver: zodResolver(EsquemaVehiculo),
    defaultValues: VALORES_INICIALES,
  });

  // Carga lista de conductores para asignar conductor habitual
  useEffect(() => {
    if (!isOpen) return;
    transporteService
      .getConductores({ activo: true })
      .then((datos) => setConductores(datos))
      .catch((err) => logDevelopmentError("Error cargando conductores en modal flota:", err));
  }, [isOpen]);

  // Carga inicial o datos del vehículo en caso de edición
  useEffect(() => {
    if (!isOpen) return;
    setErrorServidor(null);

    if (esEdicion && vehiculoId) {
      setCargandoDetalle(true);
      transporteService
        .getVehiculo(vehiculoId)
        .then((v) => {
          reset({
            placa: v.placa,
            tipo_vehiculo: v.tipo_vehiculo,
            tipo_contrato: v.tipo_contrato,
            marca: v.marca,
            referencia: v.referencia ?? "",
            modelo_anio: String(v.modelo_anio),
            color: v.color ?? "",
            ciudad_operacion: v.ciudad_operacion ?? "",
            nombre_propietario: v.nombre_propietario,
            cedula_propietario: v.cedula_propietario,
            celular_propietario: v.celular_propietario ?? "",
            conductor_habitual: v.conductor_habitual ? String(v.conductor_habitual) : "",
            fecha_ingreso: v.fecha_ingreso ?? "",
            fecha_soat: v.fecha_soat ?? "",
            fecha_cda: v.fecha_cda ?? "",
            valor_dia_base: v.valor_dia_base ?? "0",
            municipio_matricula: v.municipio_matricula ?? "",
            numero_vin: v.numero_vin ?? "",
            numero_motor: v.numero_motor ?? "",
            tipo_combustible: v.tipo_combustible ?? "",
            kilometraje: v.kilometraje != null ? String(v.kilometraje) : "0",
            cajon: Boolean(v.cajon),
            logos: Boolean(v.logos),
          });
        })
        .catch((err) => {
          const clasificado = classifyError(err);
          setErrorServidor(clasificado.message);
          logDevelopmentError("Error cargando vehículo a editar:", err);
        })
        .finally(() => setCargandoDetalle(false));
    } else {
      reset(VALORES_INICIALES);
    }
  }, [isOpen, esEdicion, vehiculoId, reset]);

  const enviar = handleSubmit(async (datos: DatosVehiculoForm) => {
    setErrorServidor(null);
    const payload = A_PAYLOAD(datos);

    try {
      if (esEdicion && vehiculoId) {
        await transporteService.actualizarVehiculo(vehiculoId, payload);
        toast.success(`Vehículo ${payload.placa} actualizado con éxito.`);
      } else {
        await transporteService.crearVehiculo(payload);
        toast.success(`Vehículo ${payload.placa} registrado con éxito.`);
      }
      onGuardado();
      onClose();
    } catch (err) {
      const detalle = classifyError(err);
      const erroresDeCampo = extractValidationErrors(detalle);

      Object.entries(erroresDeCampo).forEach(([campo, mensaje]) => {
        if (campo in datos) {
          setError(campo as keyof DatosVehiculoForm, {
            type: "server",
            message: mensaje,
          });
        }
      });

      if (!Object.keys(erroresDeCampo).length) {
        setErrorServidor(detalle.message);
      }
      logDevelopmentError("Error guardando vehículo:", err);
    }
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!isSubmitting) onClose();
      }}
      className="max-w-3xl"
      title="vehiculo-form-titulo"
    >
      <div className="px-6 pt-6 pb-2 pr-16 border-b border-gray-200 dark:border-gray-800">
        <h2
          id="vehiculo-form-titulo"
          className="text-lg font-bold text-gray-800 dark:text-white/90"
        >
          {esEdicion ? "Editar Vehículo" : "Nuevo Vehículo"}
        </h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {esEdicion
            ? "Actualiza la información técnica, documental o del propietario."
            : "Registra un nuevo vehículo en la flota vehicular (F2)."}
        </p>
      </div>

      {cargandoDetalle ? (
        <div className="p-8 text-center text-sm text-gray-500">
          Cargando información del vehículo...
        </div>
      ) : (
        <form onSubmit={enviar}>
          <div className="max-h-[72vh] overflow-y-auto px-6 py-4 space-y-6">
            {errorServidor && (
              <Alert
                variant="error"
                title="No fue posible guardar el vehículo"
                message={errorServidor}
              />
            )}

            {/* SECCIÓN 1: Identificación y Tipo */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400 mb-3">
                1. Datos Básicos del Vehículo
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="placa">
                    Placa <span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="placa"
                    placeholder="Ej. ABC123"
                    className="uppercase"
                    disabled={esEdicion || isSubmitting}
                    error={Boolean(errors.placa)}
                    hint={errors.placa?.message}
                    {...register("placa")}
                  />
                </div>

                <div>
                  <Label htmlFor="tipo_vehiculo">
                    Tipo de Vehículo <span className="text-error-500">*</span>
                  </Label>
                  <Controller
                    name="tipo_vehiculo"
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={TIPOS_VEHICULO.map((t) => ({
                          value: t,
                          label: ETIQUETAS_TIPO_VEHICULO[t] ?? t,
                        }))}
                        defaultValue={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                  {errors.tipo_vehiculo && (
                    <p className="text-xs text-error-500 mt-1">
                      {errors.tipo_vehiculo.message}
                    </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="tipo_contrato">
                    Tipo de Contrato <span className="text-error-500">*</span>
                  </Label>
                  <Controller
                    name="tipo_contrato"
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={TIPOS_CONTRATO.map((c) => ({
                          value: c,
                          label: ETIQUETAS_TIPO_CONTRATO[c] ?? c,
                        }))}
                        defaultValue={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                  {errors.tipo_contrato && (
                    <p className="text-xs text-error-500 mt-1">
                      {errors.tipo_contrato.message}
                    </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="marca">
                    Marca <span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="marca"
                    placeholder="Ej. Toyota, Chevrolet..."
                    disabled={isSubmitting}
                    error={Boolean(errors.marca)}
                    hint={errors.marca?.message}
                    {...register("marca")}
                  />
                </div>

                <div>
                  <Label htmlFor="referencia">Referencia / Línea</Label>
                  <Input
                    id="referencia"
                    placeholder="Ej. Hilux, D-Max..."
                    disabled={isSubmitting}
                    error={Boolean(errors.referencia)}
                    hint={errors.referencia?.message}
                    {...register("referencia")}
                  />
                </div>

                <div>
                  <Label htmlFor="modelo_anio">
                    Modelo (Año) <span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="modelo_anio"
                    type="number"
                    disabled={isSubmitting}
                    error={Boolean(errors.modelo_anio)}
                    hint={errors.modelo_anio?.message}
                    {...register("modelo_anio")}
                  />
                </div>

                <div>
                  <Label htmlFor="color">Color</Label>
                  <Input
                    id="color"
                    placeholder="Ej. Blanco, Gris..."
                    disabled={isSubmitting}
                    error={Boolean(errors.color)}
                    hint={errors.color?.message}
                    {...register("color")}
                  />
                </div>

                <div>
                  <Label htmlFor="ciudad_operacion">Ciudad de Operación</Label>
                  <Controller
                    name="ciudad_operacion"
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={[
                          { value: "", label: "Sin ciudad asignada" },
                          ...CIUDADES_OPERACION.map((ciud) => ({
                            value: ciud,
                            label: ciud,
                          })),
                        ]}
                        defaultValue={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                </div>
              </div>
            </div>

            {/* SECCIÓN 2: Propietario y Conductor Habitual */}
            <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400 mb-3">
                2. Propietario y Asignación
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="nombre_propietario">
                    Nombre Propietario <span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="nombre_propietario"
                    placeholder="Nombre completo"
                    disabled={isSubmitting}
                    error={Boolean(errors.nombre_propietario)}
                    hint={errors.nombre_propietario?.message}
                    {...register("nombre_propietario")}
                  />
                </div>

                <div>
                  <Label htmlFor="cedula_propietario">
                    Cédula / NIT Propietario <span className="text-error-500">*</span>
                  </Label>
                  <Input
                    id="cedula_propietario"
                    placeholder="Ej. 1020304050"
                    disabled={isSubmitting}
                    error={Boolean(errors.cedula_propietario)}
                    hint={errors.cedula_propietario?.message}
                    {...register("cedula_propietario")}
                  />
                </div>

                <div>
                  <Label htmlFor="celular_propietario">Celular Propietario</Label>
                  <Input
                    id="celular_propietario"
                    placeholder="Ej. 3001234567"
                    disabled={isSubmitting}
                    error={Boolean(errors.celular_propietario)}
                    hint={errors.celular_propietario?.message}
                    {...register("celular_propietario")}
                  />
                </div>

                <div className="sm:col-span-3">
                  <Label htmlFor="conductor_habitual">Conductor Habitual</Label>
                  <Controller
                    name="conductor_habitual"
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={[
                          { value: "", label: "Sin conductor habitual asignado" },
                          ...conductores.map((c) => ({
                            value: String(c.id),
                            label: `${c.nombre_completo} (${c.cedula}) - ${c.tipo_vinculacion}`,
                          })),
                        ]}
                        defaultValue={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Conductor asignado por defecto para agilizar los registros en el Kiosco.
                  </p>
                </div>
              </div>
            </div>

            {/* SECCIÓN 3: Fechas, Vigencias y Tarifas */}
            <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400 mb-3">
                3. Vigencias Documentales y Operación
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="fecha_soat">Vencimiento SOAT</Label>
                  <Input
                    id="fecha_soat"
                    type="date"
                    disabled={isSubmitting}
                    error={Boolean(errors.fecha_soat)}
                    hint={errors.fecha_soat?.message}
                    {...register("fecha_soat")}
                  />
                </div>

                <div>
                  <Label htmlFor="fecha_cda">Vencimiento CDA (Técnico-mecánica)</Label>
                  <Input
                    id="fecha_cda"
                    type="date"
                    disabled={isSubmitting}
                    error={Boolean(errors.fecha_cda)}
                    hint={errors.fecha_cda?.message}
                    {...register("fecha_cda")}
                  />
                </div>

                <div>
                  <Label htmlFor="fecha_ingreso">Fecha de Ingreso a Operación</Label>
                  <Input
                    id="fecha_ingreso"
                    type="date"
                    disabled={isSubmitting}
                    error={Boolean(errors.fecha_ingreso)}
                    hint={errors.fecha_ingreso?.message}
                    {...register("fecha_ingreso")}
                  />
                </div>

                <div>
                  <Label htmlFor="valor_dia_base">Valor Día Base ($ COP)</Label>
                  <Input
                    id="valor_dia_base"
                    type="number"
                    disabled={isSubmitting}
                    error={Boolean(errors.valor_dia_base)}
                    hint={errors.valor_dia_base?.message}
                    {...register("valor_dia_base")}
                  />
                </div>

                <div>
                  <Label htmlFor="kilometraje">Kilometraje Actual</Label>
                  <Input
                    id="kilometraje"
                    type="number"
                    disabled={isSubmitting}
                    error={Boolean(errors.kilometraje)}
                    hint={errors.kilometraje?.message}
                    {...register("kilometraje")}
                  />
                </div>

                <div className="flex items-center gap-6 pt-6">
                  <Controller
                    name="cajon"
                    control={control}
                    render={({ field }) => (
                      <Checkbox
                        id="cajon"
                        label="Tiene cajón"
                        checked={field.value}
                        onChange={field.onChange}
                        disabled={isSubmitting}
                      />
                    )}
                  />

                  <Controller
                    name="logos"
                    control={control}
                    render={({ field }) => (
                      <Checkbox
                        id="logos"
                        label="Tiene logos"
                        checked={field.value}
                        onChange={field.onChange}
                        disabled={isSubmitting}
                      />
                    )}
                  />
                </div>
              </div>
            </div>

            {/* SECCIÓN 4: Datos Técnicos Adicionales */}
            <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400 mb-3">
                4. Datos Técnicos (Opcional)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div>
                  <Label htmlFor="municipio_matricula">Municipio Matrícula</Label>
                  <Input
                    id="municipio_matricula"
                    placeholder="Ej. Envigado"
                    disabled={isSubmitting}
                    {...register("municipio_matricula")}
                  />
                </div>

                <div>
                  <Label htmlFor="numero_vin">Número VIN / Chasis</Label>
                  <Input
                    id="numero_vin"
                    placeholder="17 caracteres"
                    disabled={isSubmitting}
                    {...register("numero_vin")}
                  />
                </div>

                <div>
                  <Label htmlFor="numero_motor">Número Motor</Label>
                  <Input
                    id="numero_motor"
                    placeholder="Número serie motor"
                    disabled={isSubmitting}
                    {...register("numero_motor")}
                  />
                </div>

                <div>
                  <Label htmlFor="tipo_combustible">Combustible</Label>
                  <Input
                    id="tipo_combustible"
                    placeholder="Ej. Diesel, Gasolina"
                    disabled={isSubmitting}
                    {...register("tipo_combustible")}
                  />
                </div>
              </div>
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
                  ? "Actualizar Vehículo"
                  : "Registrar Vehículo"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
