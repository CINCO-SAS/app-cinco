import React from "react";
import SectionHeader from "../../common/SectionHeader";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import TextArea from "@/components/form/input/TextArea";
import { FormCapexTipologia5Data } from "./types";

interface Paso5PanoramicaPlanoProps {
  formData: FormCapexTipologia5Data;
  updateField: <K extends keyof FormCapexTipologia5Data>(
    field: K,
    value: FormCapexTipologia5Data[K],
  ) => void;
  onPhotoUpload: (field: keyof FormCapexTipologia5Data, file: File) => void;
  onPhotoRemove: (field: keyof FormCapexTipologia5Data) => void;
  onFotoDescripcion?: (
    campo: "foto_panoramica_preview" | "foto_plano_preview",
    valor: string,
  ) => void;
}

export const Paso5PanoramicaPlano: React.FC<Paso5PanoramicaPlanoProps> = ({
  formData,
  updateField,
  onPhotoUpload,
  onPhotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="4. PANORAMICA DE LA TORRE Y PLANOS DE TERRENO EB MANO ALZADA"
        description="Registro panorámico de la estación base tomado desde la torre, plano en mano alzada de las dimensiones de cableados de la intervención y recomendación del aliado."
      />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <FotoSlotWithDescripcion
          index={1}
          titulo="Foto Panorámica de la Estación Base"
          inputId="foto-panoramica-estacion"
          previewUrl={formData.foto_panoramica_preview}
          onUpload={(file) => file && onPhotoUpload("foto_panoramica_preview", file)}
          onRemove={() => onPhotoRemove("foto_panoramica_preview")}
          descripcion={formData.foto_panoramica_descripcion ?? ""}
          onDescripcionChange={(valor) =>
            onFotoDescripcion?.("foto_panoramica_preview", valor)
          }
          descripcionLabel="Descripción de la foto"
        />

        <FotoSlotWithDescripcion
          index={2}
          titulo="Plano / Croquis a Mano Alzada (Dimensiones de Cableado)"
          inputId="foto-plano-cableado"
          previewUrl={formData.foto_plano_preview}
          onUpload={(file) => file && onPhotoUpload("foto_plano_preview", file)}
          onRemove={() => onPhotoRemove("foto_plano_preview")}
          descripcion={formData.foto_plano_descripcion ?? ""}
          onDescripcionChange={(valor) =>
            onFotoDescripcion?.("foto_plano_preview", valor)
          }
          descripcionLabel="Descripción de la foto"
        />
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <Label className="font-semibold">Recomendación Aliado</Label>
        <TextArea
          rows={3}
          placeholder="Observaciones sobre el estado de la instalación, distribución de cableados y configuración final del sistema eléctrico..."
          value={formData.plano_recomendacion_aliado}
          onChange={(e) => updateField("plano_recomendacion_aliado", e.target.value)}
        />
      </div>
    </div>
  );
};
