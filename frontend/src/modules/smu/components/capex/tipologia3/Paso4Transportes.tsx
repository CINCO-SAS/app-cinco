import React from "react";
import SectionHeader from "../../common/SectionHeader";
import DynamicItemCard from "../../common/DynamicItemCard";
import AddItemButton from "../../common/AddItemButton";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import Select from "@/components/form/Select";
import { TransporteItem } from "./types";
import { OPCIONES_TIPO_TRANSPORTE } from "./constants";

interface Paso4TransportesProps {
  transportes: TransporteItem[];
  onAddTransporte: () => void;
  onRemoveTransporte: (id: string) => void;
  onUpdateTransporte: (id: string, field: keyof TransporteItem, value: string) => void;
  onFotoUpload: (
    id: string,
    field: "foto_antes_preview" | "foto_durante_preview" | "foto_despues_preview",
    file: File,
  ) => void;
  onFotoRemove: (
    id: string,
    field: "foto_antes_preview" | "foto_durante_preview" | "foto_despues_preview",
  ) => void;
  onFotoDescripcion?: (
    id: string,
    parte: "antes" | "durante" | "despues",
    valor: string,
  ) => void;
}

export const Paso4Transportes: React.FC<Paso4TransportesProps> = ({
  transportes,
  onAddTransporte,
  onRemoveTransporte,
  onUpdateTransporte,
  onFotoUpload,
  onFotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="3. TRANSPORTES"
        description="Registro de traslados (4x4/camión, coteros o semovientes) con código SAP, descripción y registro fotográfico Antes, Durante y Después. Agregue un registro por cada modalidad utilizada."
        action={<AddItemButton label="Agregar Transporte" onClick={onAddTransporte} />}
      />

      <div className="space-y-5">
        {transportes.map((transporte, idx) => (
          <DynamicItemCard
            key={transporte.id}
            label={`TRANSPORTE #${idx + 1}`}
            onRemove={transportes.length > 1 ? () => onRemoveTransporte(transporte.id) : undefined}
          >
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <Label>Tipo de Transporte</Label>
                  <Select
                    options={OPCIONES_TIPO_TRANSPORTE}
                    value={transporte.tipo}
                    onChange={(val) => onUpdateTransporte(transporte.id, "tipo", val)}
                  />
                </div>

                <div>
                  <Label>Código SAP Transporte</Label>
                  <Input
                    placeholder="Código SAP de transporte"
                    value={transporte.codigo_sap}
                    onChange={(e) => onUpdateTransporte(transporte.id, "codigo_sap", e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label>Descripción del Transporte</Label>
                <TextArea
                  rows={2}
                  placeholder="Detalles de llegada, condiciones de acceso y ruta..."
                  value={transporte.descripcion}
                  onChange={(e) => onUpdateTransporte(transporte.id, "descripcion", e.target.value)}
                />
              </div>

              <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/[0.01]">
                <span className="mb-3 block text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
                  Registro Fotográfico del Traslado
                </span>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <FotoSlotWithDescripcion
                    index={1}
                    titulo="FOTO ANTES (Salida)"
                    inputId={`foto-trans-antes-${transporte.id}`}
                    previewUrl={transporte.foto_antes_preview}
                    onUpload={(file) => file && onFotoUpload(transporte.id, "foto_antes_preview", file)}
                    onRemove={() => onFotoRemove(transporte.id, "foto_antes_preview")}
                    descripcion={transporte.foto_antes_descripcion ?? ""}
                    onDescripcionChange={(valor) =>
                      onFotoDescripcion?.(transporte.id, "antes", valor)
                    }
                    descripcionLabel="Descripción de la foto"
                  />

                  <FotoSlotWithDescripcion
                    index={2}
                    titulo="FOTO DURANTE (En Ruta)"
                    inputId={`foto-trans-durante-${transporte.id}`}
                    previewUrl={transporte.foto_durante_preview}
                    onUpload={(file) => file && onFotoUpload(transporte.id, "foto_durante_preview", file)}
                    onRemove={() => onFotoRemove(transporte.id, "foto_durante_preview")}
                    descripcion={transporte.foto_durante_descripcion ?? ""}
                    onDescripcionChange={(valor) =>
                      onFotoDescripcion?.(transporte.id, "durante", valor)
                    }
                    descripcionLabel="Descripción de la foto"
                  />

                  <FotoSlotWithDescripcion
                    index={3}
                    titulo="FOTO DESPUÉS (Llegada a Sitio)"
                    inputId={`foto-trans-despues-${transporte.id}`}
                    previewUrl={transporte.foto_despues_preview}
                    onUpload={(file) => file && onFotoUpload(transporte.id, "foto_despues_preview", file)}
                    onRemove={() => onFotoRemove(transporte.id, "foto_despues_preview")}
                    descripcion={transporte.foto_despues_descripcion ?? ""}
                    onDescripcionChange={(valor) =>
                      onFotoDescripcion?.(transporte.id, "despues", valor)
                    }
                    descripcionLabel="Descripción de la foto"
                  />
                </div>
              </div>
            </div>
          </DynamicItemCard>
        ))}
      </div>
    </div>
  );
};
