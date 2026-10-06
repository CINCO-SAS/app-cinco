import React from "react";
import SectionHeader from "../../common/SectionHeader";
import DynamicItemCard from "../../common/DynamicItemCard";
import AddItemButton from "../../common/AddItemButton";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import CatalogoFrecuenteDropdowns from "../../common/CatalogoFrecuenteDropdowns";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import { ActividadMOItem } from "./types";
import { CATALOGO_ACTIVIDADES_FRECUENTES } from "./constants";

interface Paso3ActividadesMOProps {
  actividades: ActividadMOItem[];
  onAddActividad: () => void;
  onRemoveActividad: (id: string) => void;
  onUpdateActividad: (id: string, field: keyof ActividadMOItem, value: string) => void;
  onApplyTemplate: (id: string, item: (typeof CATALOGO_ACTIVIDADES_FRECUENTES)[0]) => void;
  onFotoUpload: (
    id: string,
    field: "foto_antes_preview" | "foto_despues_preview",
    file: File,
  ) => void;
  onFotoRemove: (
    id: string,
    field: "foto_antes_preview" | "foto_despues_preview",
  ) => void;
  onFotoDescripcion?: (
    id: string,
    parte: "antes" | "despues",
    valor: string,
  ) => void;
}

export const Paso3ActividadesMO: React.FC<Paso3ActividadesMOProps> = ({
  actividades,
  onAddActividad,
  onRemoveActividad,
  onUpdateActividad,
  onApplyTemplate,
  onFotoUpload,
  onFotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="2.- MO - ACTIVIDADES ESTANDARIZADAS"
        description="Registro de actividades de mano de obra con descripción técnica y registro fotográfico comparativo antes / después (mismo ángulo)."
        action={<AddItemButton label="Agregar Actividad MO" onClick={onAddActividad} />}
      />

      <div className="space-y-5">
        {actividades.map((actividad, idx) => (
          <DynamicItemCard
            key={actividad.id}
            label={`ACTIVIDAD MO #${idx + 1}`}
            onRemove={actividades.length > 1 ? () => onRemoveActividad(actividad.id) : undefined}
          >
            {/* Plantillas rápidas de 1-click, agrupadas en dos dropdowns */}
            <CatalogoFrecuenteDropdowns
              title="Catálogo MO Frecuente MT/BT (Autocompletar 1-clic)"
              items={CATALOGO_ACTIVIDADES_FRECUENTES}
              cardId={actividad.id}
              onApply={(item) => onApplyTemplate(actividad.id, item)}
            />

            {/* Layout en 2 columnas: Datos (7 cols) + Comparativo Antes/Después (5 cols) */}
            <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
              {/* Datos de la actividad */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:col-span-7">
                <div className="sm:col-span-2">
                  <Label>Texto SAP</Label>
                  <Input
                    placeholder="Descripción de la actividad"
                    value={actividad.texto_sap}
                    onChange={(e) => onUpdateActividad(actividad.id, "texto_sap", e.target.value)}
                  />
                </div>

                <div>
                  <Label>Código SAP</Label>
                  <Input
                    placeholder="Código SAP"
                    value={actividad.codigo_sap}
                    onChange={(e) => onUpdateActividad(actividad.id, "codigo_sap", e.target.value)}
                  />
                </div>

                <div>
                  <Label>Comentarios de Proceso</Label>
                  <Input
                    placeholder="Comentario del proceso"
                    value={actividad.comentarios}
                    onChange={(e) => onUpdateActividad(actividad.id, "comentarios", e.target.value)}
                  />
                </div>

                <div className="sm:col-span-2">
                  <Label>Alcance de la Mano de Obra</Label>
                  <TextArea
                    rows={3}
                    placeholder="Detalle técnico del alcance de la mano de obra..."
                    value={actividad.alcance}
                    onChange={(e) => onUpdateActividad(actividad.id, "alcance", e.target.value)}
                  />
                </div>

                <div className="sm:col-span-2">
                  <Label>Descripción</Label>
                  <TextArea
                    rows={2}
                    placeholder="Descripción de la actividad ejecutada..."
                    value={actividad.descripcion}
                    onChange={(e) => onUpdateActividad(actividad.id, "descripcion", e.target.value)}
                  />
                </div>
              </div>

              {/* Registro Fotográfico Comparativo (Antes y Después) */}
              <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 lg:col-span-5 dark:border-gray-800 dark:bg-white/[0.01]">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
                    Evidencias Antes y Después
                  </span>
                  <span className="text-[10px] text-gray-400 italic">Mismo ángulo</span>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <FotoSlotWithDescripcion
                    index={1}
                    titulo="Foto ANTES"
                    inputId={`foto-antes-${actividad.id}`}
                    previewUrl={actividad.foto_antes_preview}
                    onUpload={(file) => file && onFotoUpload(actividad.id, "foto_antes_preview", file)}
                    onRemove={() => onFotoRemove(actividad.id, "foto_antes_preview")}
                    descripcion={actividad.foto_antes_descripcion ?? ""}
                    onDescripcionChange={(valor) =>
                      onFotoDescripcion?.(actividad.id, "antes", valor)
                    }
                    descripcionLabel="Descripción de la foto"
                  />

                  <FotoSlotWithDescripcion
                    index={2}
                    titulo="Foto DESPUÉS"
                    inputId={`foto-despues-${actividad.id}`}
                    previewUrl={actividad.foto_despues_preview}
                    onUpload={(file) => file && onFotoUpload(actividad.id, "foto_despues_preview", file)}
                    onRemove={() => onFotoRemove(actividad.id, "foto_despues_preview")}
                    descripcion={actividad.foto_despues_descripcion ?? ""}
                    onDescripcionChange={(valor) =>
                      onFotoDescripcion?.(actividad.id, "despues", valor)
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
