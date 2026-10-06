import React from "react";
import SectionHeader from "../../common/SectionHeader";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import TextArea from "@/components/form/input/TextArea";
import { Layers } from "lucide-react";
import { FormCapexTipologia1Data } from "./types";
import { ELEMENTOS_PLANO_SPT } from "./constants";

interface Paso6PanoramicaPlanoProps {
  formData: FormCapexTipologia1Data;
  updateField: <K extends keyof FormCapexTipologia1Data>(
    field: K,
    value: FormCapexTipologia1Data[K],
  ) => void;
  onPhotoUpload: (field: keyof FormCapexTipologia1Data, file: File) => void;
  onPhotoRemove: (field: keyof FormCapexTipologia1Data) => void;
  onFotoDescripcion?: (
    campo: "foto_panoramica_preview" | "foto_plano_preview",
    valor: string,
  ) => void;
}

export const Paso6PanoramicaPlano: React.FC<Paso6PanoramicaPlanoProps> = ({
  formData,
  updateField,
  onPhotoUpload,
  onPhotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="5. PANORAMICA DE LA TORRE Y PLANOS DE TERRENO EB MANO ALZADA"
        description="Registro panorámico de la estación base, croquis / plano esquemático del sistema de puesta a tierra y referencias técnicas."
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
          titulo="Plano / Croquis de Puesta a Tierra a Mano Alzada"
          inputId="foto-plano-puesta-tierra"
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

      {/* Elementos de Referencia Técnica del Plano */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-3 flex items-center gap-2">
          <Layers className="h-4 w-4 text-brand-500" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            Elementos Técnicos de Referencia del Plano y Distribución
          </h4>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {ELEMENTOS_PLANO_SPT.map((elem, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-xl border border-gray-100 bg-gray-50/50 p-2.5 text-xs text-gray-700 dark:border-gray-800 dark:bg-white/[0.01] dark:text-gray-300"
            >
              <div className="h-1.5 w-1.5 rounded-full bg-brand-500" />
              <span>{elem}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <Label className="font-semibold">Recomendación Aliado</Label>
        <TextArea
          rows={3}
          placeholder="Observaciones respecto a la distribución geométrica de los anillos, bajantes, electrodos y configuración final..."
          value={formData.plano_recomendacion_aliado}
          onChange={(e) => updateField("plano_recomendacion_aliado", e.target.value)}
        />
      </div>
    </div>
  );
};
