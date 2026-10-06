import React from "react";
import SectionHeader from "../../common/SectionHeader";
import AddItemButton from "../../common/AddItemButton";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import TextArea from "@/components/form/input/TextArea";
import { Camera, Trash2 } from "lucide-react";
import { FormCapexTipologia5Data } from "./types";

interface Paso6FueraEstandarProps {
  formData: FormCapexTipologia5Data;
  updateField: <K extends keyof FormCapexTipologia5Data>(
    field: K,
    value: FormCapexTipologia5Data[K],
  ) => void;
  onAddJustificacion: () => void;
  onRemoveJustificacion: (id: string) => void;
  onJustificacionUpload: (id: string, file: File) => void;
  onJustificacionRemove: (id: string) => void;
  onJustificacionDescripcion?: (id: string, valor: string) => void;
}

export const Paso6FueraEstandar: React.FC<Paso6FueraEstandarProps> = ({
  formData,
  updateField,
  onAddJustificacion,
  onRemoveJustificacion,
  onJustificacionUpload,
  onJustificacionRemove,
  onJustificacionDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="5. RESULTADOS DE OTRAS ACTIVIDADES APROBADAS POR FUERA DEL ESTANDAR"
        description="Justificación técnica de actividades ejecutadas por fuera del alcance estándar con sus respectivos informes fotográficos."
        action={<AddItemButton label="Agregar Foto Justificación" onClick={onAddJustificacion} />}
      />

      {/* Texto de justificación */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mt-1 mb-3">
          <Label className="font-semibold">Texto Justificación:</Label>
        </div>
        <TextArea
          rows={4}
          placeholder="Explicación detallada y justificación técnica que ameritó la ejecución por fuera de alcance estándar..."
          value={formData.texto_justificacion}
          onChange={(e) => updateField("texto_justificacion", e.target.value)}
        />
      </div>

      {/* Informes Fotográficos de Justificación */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-4 flex items-center gap-2">
          <Camera className="h-4 w-4 text-brand-500" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            Informes Fotográficos de Justificación
          </h4>
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
                titulo={`Informe Fotográfico Justificación ${idx + 1}`}
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
    </div>
  );
};
