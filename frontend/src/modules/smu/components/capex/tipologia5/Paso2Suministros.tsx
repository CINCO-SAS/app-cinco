import React from "react";
import SectionHeader from "../../common/SectionHeader";
import DynamicItemCard from "../../common/DynamicItemCard";
import AddItemButton from "../../common/AddItemButton";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import CatalogoFrecuenteDropdowns from "../../common/CatalogoFrecuenteDropdowns";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import Select from "@/components/form/Select";
import { InsumoSAPItem } from "./types";
import {
  CATALOGO_SUMINISTROS_FRECUENTES,
  OPCIONES_UNIDAD_MEDIDA,
} from "./constants";

interface Paso2SuministrosProps {
  insumos: InsumoSAPItem[];
  onAddInsumo: () => void;
  onRemoveInsumo: (id: string) => void;
  onUpdateInsumo: (
    id: string,
    field: keyof InsumoSAPItem,
    value: string,
  ) => void;
  onApplyTemplate: (
    id: string,
    item: (typeof CATALOGO_SUMINISTROS_FRECUENTES)[0],
  ) => void;
  onFotoUpload: (id: string, file: File) => void;
  onFotoRemove: (id: string) => void;
  onFotoDescripcion?: (id: string, valor: string) => void;
}

export const Paso2Suministros: React.FC<Paso2SuministrosProps> = ({
  insumos,
  onAddInsumo,
  onRemoveInsumo,
  onUpdateInsumo,
  onApplyTemplate,
  onFotoUpload,
  onFotoRemove,
  onFotoDescripcion,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="1.- INVENTARIO DE SUMINISTROS"
        description="Registro de códigos SAP, cantidades estándar, cantidades reales utilizadas, alcance y evidencia fotográfica por ítem."
        action={
          <AddItemButton label="Agregar Suministro" onClick={onAddInsumo} />
        }
      />

      <div className="space-y-5">
        {insumos.map((insumo, idx) => (
          <DynamicItemCard
            key={insumo.id}
            label={`SUMINISTRO #${idx + 1}`}
            onRemove={
              insumos.length > 1 ? () => onRemoveInsumo(insumo.id) : undefined
            }
          >
            {/* Plantillas rápidas de 1-click, agrupadas en dos dropdowns */}
            <CatalogoFrecuenteDropdowns
              title="Catálogo Frecuente MT/BT (Autocompletar 1-clic)"
              items={CATALOGO_SUMINISTROS_FRECUENTES}
              cardId={insumo.id}
              onApply={(item) => onApplyTemplate(insumo.id, item)}
            />

            {/* Layout balanceado: Campos (8 cols) + Foto proporcionada (4 cols) */}
            <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-12">
              {/* Bloque de datos del suministro */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:col-span-8">
                <div className="sm:col-span-2 md:col-span-3">
                  <Label>Texto SAP</Label>
                  <Input
                    placeholder="Descripción del suministro"
                    value={insumo.texto_sap}
                    onChange={(e) =>
                      onUpdateInsumo(insumo.id, "texto_sap", e.target.value)
                    }
                  />
                </div>

                <div>
                  <Label>Código SAP</Label>
                  <Input
                    placeholder="Código SAP"
                    value={insumo.codigo_sap}
                    onChange={(e) =>
                      onUpdateInsumo(insumo.id, "codigo_sap", e.target.value)
                    }
                  />
                </div>

                <div>
                  <Label>Unidad de Medida</Label>
                  <Select
                    options={OPCIONES_UNIDAD_MEDIDA}
                    value={insumo.unidad_medida}
                    onChange={(val) =>
                      onUpdateInsumo(insumo.id, "unidad_medida", val)
                    }
                  />
                </div>

                <div>
                  <Label>Cant. Estándar</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={insumo.cantidad_estandar}
                    onChange={(e) =>
                      onUpdateInsumo(
                        insumo.id,
                        "cantidad_estandar",
                        e.target.value,
                      )
                    }
                  />
                </div>

                <div>
                  <Label>Cant. Real</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={insumo.cantidad_real}
                    onChange={(e) =>
                      onUpdateInsumo(insumo.id, "cantidad_real", e.target.value)
                    }
                  />
                </div>

                <div className="sm:col-span-2 md:col-span-3">
                  <Label>Alcance</Label>
                  <TextArea
                    rows={2}
                    placeholder="Alcance del suministro..."
                    value={insumo.alcance}
                    onChange={(e) =>
                      onUpdateInsumo(insumo.id, "alcance", e.target.value)
                    }
                  />
                </div>

                <div className="sm:col-span-2 md:col-span-3">
                  <Label>Comentarios</Label>
                  <TextArea
                    rows={2}
                    placeholder="Observaciones de instalación, configuración o trazado..."
                    value={insumo.comentarios}
                    onChange={(e) =>
                      onUpdateInsumo(insumo.id, "comentarios", e.target.value)
                    }
                  />
                </div>
              </div>

              {/* Bloque de foto bien proporcionado */}
              <div className="w-full lg:col-span-4">
                <Label>Evidencia del Suministro</Label>
                <FotoSlotWithDescripcion
                  index={idx + 1}
                  titulo={`Foto Suministro #${idx + 1}`}
                  inputId={`foto-insumo-${insumo.id}`}
                  previewUrl={insumo.foto_preview}
                  onUpload={(file) => file && onFotoUpload(insumo.id, file)}
                  onRemove={() => onFotoRemove(insumo.id)}
                  descripcion={insumo.foto_descripcion ?? ""}
                  onDescripcionChange={(valor) =>
                    onFotoDescripcion?.(insumo.id, valor)
                  }
                  descripcionLabel="Descripción de la foto"
                />
              </div>
            </div>
          </DynamicItemCard>
        ))}
      </div>
    </div>
  );
};
