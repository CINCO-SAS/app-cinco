import React from "react";
import SectionHeader from "../../common/SectionHeader";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import Select from "@/components/form/Select";
import { Camera } from "lucide-react";
import { FormCapexTipologia1Data } from "./types";
import { OPCIONES_TIPO_TRANSPORTE } from "./constants";

interface Paso4TransportesProps {
  formData: FormCapexTipologia1Data;
  updateField: <K extends keyof FormCapexTipologia1Data>(
    field: K,
    value: FormCapexTipologia1Data[K],
  ) => void;
  onPhotoUpload: (field: keyof FormCapexTipologia1Data, file: File) => void;
  onPhotoRemove: (field: keyof FormCapexTipologia1Data) => void;
  onFotoDescripcion?: (
    campo:
      | "transporte_foto_antes"
      | "transporte_foto_durante"
      | "transporte_foto_despues",
    valor: string,
  ) => void;
}

export const Paso4Transportes: React.FC<Paso4TransportesProps> = ({
  formData,
  updateField,
  onPhotoUpload,
  onPhotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="3. TRANSPORTES"
        description="Registro de traslados, tipo de vehículo, kilometraje, tiempo de recorrido y registro fotográfico (Antes, Durante y Después)."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
        <div>
          <Label>Tipo de Transporte</Label>
          <Select
            options={OPCIONES_TIPO_TRANSPORTE}
            value={formData.transporte_tipo}
            onChange={(val) => updateField("transporte_tipo", val)}
          />
        </div>

        <div>
          <Label>Código SAP Transporte</Label>
          <Input
            placeholder="Código SAP de transporte"
            value={formData.transporte_codigo_sap}
            onChange={(e) => updateField("transporte_codigo_sap", e.target.value)}
          />
        </div>

        <div>
          <Label>Distancia Recorrida (km)</Label>
          <Input
            type="number"
            min="0"
            step="0.1"
            value={formData.transporte_distancia_km}
            onChange={(e) => updateField("transporte_distancia_km", e.target.value)}
          />
        </div>

        <div>
          <Label>Tiempo de Desplazamiento</Label>
          <Input
            placeholder="Tiempo de recorrido"
            value={formData.transporte_tiempo_desplazamiento}
            onChange={(e) => updateField("transporte_tiempo_desplazamiento", e.target.value)}
          />
        </div>

        <div className="sm:col-span-2 md:col-span-4">
          <Label>Descripción y/o Características del Transporte</Label>
          <TextArea
            rows={2}
            placeholder="Detalles de llegada, condiciones de acceso y ruta..."
            value={formData.transporte_descripcion}
            onChange={(e) => updateField("transporte_descripcion", e.target.value)}
          />
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-4 flex items-center gap-2">
          <Camera className="h-4 w-4 text-brand-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            Registro Fotográfico de Traslado
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FotoSlotWithDescripcion
            index={1}
            titulo="FOTO ANTES (Salida)"
            inputId="foto-transporte-antes"
            previewUrl={formData.transporte_foto_antes}
            onUpload={(file) => file && onPhotoUpload("transporte_foto_antes", file)}
            onRemove={() => onPhotoRemove("transporte_foto_antes")}
            descripcion={formData.transporte_foto_antes_descripcion ?? ""}
            onDescripcionChange={(valor) =>
              onFotoDescripcion?.("transporte_foto_antes", valor)
            }
            descripcionLabel="Descripción de la foto"
          />

          <FotoSlotWithDescripcion
            index={2}
            titulo="FOTO DURANTE (En Ruta)"
            inputId="foto-transporte-durante"
            previewUrl={formData.transporte_foto_durante}
            onUpload={(file) => file && onPhotoUpload("transporte_foto_durante", file)}
            onRemove={() => onPhotoRemove("transporte_foto_durante")}
            descripcion={formData.transporte_foto_durante_descripcion ?? ""}
            onDescripcionChange={(valor) =>
              onFotoDescripcion?.("transporte_foto_durante", valor)
            }
            descripcionLabel="Descripción de la foto"
          />

          <FotoSlotWithDescripcion
            index={3}
            titulo="FOTO DESPUÉS (Llegada a Sitio)"
            inputId="foto-transporte-despues"
            previewUrl={formData.transporte_foto_despues}
            onUpload={(file) => file && onPhotoUpload("transporte_foto_despues", file)}
            onRemove={() => onPhotoRemove("transporte_foto_despues")}
            descripcion={formData.transporte_foto_despues_descripcion ?? ""}
            onDescripcionChange={(valor) =>
              onFotoDescripcion?.("transporte_foto_despues", valor)
            }
            descripcionLabel="Descripción de la foto"
          />
        </div>
      </div>
    </div>
  );
};
