import React from "react";
import SectionHeader from "../../common/SectionHeader";
import AddItemButton from "../../common/AddItemButton";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import { Camera, ShieldCheck, Trash2 } from "lucide-react";
import { FormCapexTipologia1Data } from "./types";

interface Paso7FueraEstandarProps {
  formData: FormCapexTipologia1Data;
  updateField: <K extends keyof FormCapexTipologia1Data>(
    field: K,
    value: FormCapexTipologia1Data[K],
  ) => void;
  onAddJustificacion: () => void;
  onRemoveJustificacion: (id: string) => void;
  onJustificacionUpload: (id: string, file: File) => void;
  onJustificacionRemove: (id: string) => void;
  onJustificacionDescripcion?: (id: string, valor: string) => void;
  onPhotoUpload: (field: keyof FormCapexTipologia1Data, file: File) => void;
  onPhotoRemove: (field: keyof FormCapexTipologia1Data) => void;
  onFotoDescripcion?: (
    campo: "foto_soporte_matricula_preview",
    valor: string,
  ) => void;
}

export const Paso7FueraEstandar: React.FC<Paso7FueraEstandarProps> = ({
  formData,
  updateField,
  onAddJustificacion,
  onRemoveJustificacion,
  onJustificacionUpload,
  onJustificacionRemove,
  onJustificacionDescripcion,
  onPhotoUpload,
  onPhotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="6. RESULTADOS DE OTRAS ACTIVIDADES APROBADAS POR FUERA DEL ESTANDAR"
        description="Registro de actividades no estandarizadas con justificación técnica, soportes de matrícula profesional (CONTE) e informes fotográficos."
        action={<AddItemButton label="Agregar Foto Justificación" onClick={onAddJustificacion} />}
      />

      {/* Actividades adicionales y justificación */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
          Actividades Adicionales Realizadas
        </h4>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <Label>Actividad Adicional 1</Label>
            <Input
              placeholder="Detalle de actividad adicional..."
              value={formData.otras_actividades_1}
              onChange={(e) => updateField("otras_actividades_1", e.target.value)}
            />
          </div>

          <div>
            <Label>Actividad Adicional 2</Label>
            <Input
              placeholder="Detalle de actividad adicional..."
              value={formData.otras_actividades_2}
              onChange={(e) => updateField("otras_actividades_2", e.target.value)}
            />
          </div>

          <div>
            <Label>Actividad Adicional 3</Label>
            <Input
              placeholder="Detalle de actividad adicional..."
              value={formData.otras_actividades_3}
              onChange={(e) => updateField("otras_actividades_3", e.target.value)}
            />
          </div>
        </div>

        <div className="mt-4">
          <Label>TEXTO JUSTIFICACIÓN:</Label>
          <TextArea
            rows={3}
            placeholder="Explicación detallada y justificación técnica que ameritó la ejecución por fuera de alcance estándar..."
            value={formData.texto_justificacion_otras_actividades}
            onChange={(e) => updateField("texto_justificacion_otras_actividades", e.target.value)}
          />
        </div>
      </div>

      {/* Informes Fotográficos de Justificación */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-brand-500" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
              Informes Fotográficos de Justificación
            </h4>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {formData.fotos_justificacion.map((just, idx) => (
            <div key={just.id} className="relative flex flex-col justify-between">
              {formData.fotos_justificacion.length > 1 && (
                <button
                  type="button"
                  onClick={() => onRemoveJustificacion(just.id)}
                  className="absolute right-2 top-2 z-10 rounded-md p-1 text-gray-400 hover:bg-error-50 hover:text-error-500 dark:hover:bg-error-500/10"
                  title="Eliminar este slot"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
              <FotoSlotWithDescripcion
                index={idx + 1}
                titulo={`Justificación ${idx + 1}`}
                inputId={`foto-justificacion-${just.id}`}
                previewUrl={just.previewUrl}
                onUpload={(file) => file && onJustificacionUpload(just.id, file)}
                onRemove={() => onJustificacionRemove(just.id)}
                descripcion={just.descripcion ?? ""}
                onDescripcionChange={(valor) =>
                  onJustificacionDescripcion?.(just.id, valor)
                }
                descripcionLabel="Descripción de la foto"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Soporte de Matrícula Profesional CONTE */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-4 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-brand-500" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            Soporte de Matrícula Profesional / Tarjeta Técnica (CONTE / Técnico Electricista)
          </h4>
        </div>

        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:col-span-8">
            <div className="sm:col-span-2">
              <Label>Nombre Titular Tarjeta / Matrícula</Label>
              <Input
                placeholder="Nombre del titular"
                value={formData.matricula_nombre}
                onChange={(e) => updateField("matricula_nombre", e.target.value)}
              />
            </div>

            <div>
              <Label>Número de Matrícula / Registro</Label>
              <Input
                value={formData.matricula_numero}
                onChange={(e) => updateField("matricula_numero", e.target.value)}
              />
            </div>

            <div>
              <Label>Fecha de Expedición</Label>
              <Input
                type="date"
                value={formData.matricula_fecha}
                onChange={(e) => updateField("matricula_fecha", e.target.value)}
              />
            </div>
          </div>

          <div className="w-full lg:col-span-4">
            <Label>Foto Soporte Tarjeta Profesional</Label>
            <FotoSlotWithDescripcion
              index={1}
              titulo="Tarjeta Profesional CONTE"
              inputId="foto-soporte-matricula"
              previewUrl={formData.foto_soporte_matricula_preview}
              onUpload={(file) => file && onPhotoUpload("foto_soporte_matricula_preview", file)}
              onRemove={() => onPhotoRemove("foto_soporte_matricula_preview")}
              descripcion={formData.foto_soporte_matricula_descripcion ?? ""}
              onDescripcionChange={(valor) =>
                onFotoDescripcion?.("foto_soporte_matricula_preview", valor)
              }
              descripcionLabel="Descripción de la foto"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
