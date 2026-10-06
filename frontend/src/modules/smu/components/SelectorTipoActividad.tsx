"use client";

import React from "react";
import RadioCardGroup from "./RadioCardGroup";
import type { GrupoActividad } from "../types/smu.types";

interface SelectorTipoActividadProps {
  value: GrupoActividad | null;
  onChange: (grupo: GrupoActividad) => void;
}

const opciones = [
  {
    value: "preventivos" as GrupoActividad,
    label: "Preventivos",
    descripcion: "Mantenimiento preventivo programado",
  },
  {
    value: "correctivos_capex" as GrupoActividad,
    label: "Correctivos CAPEX",
    descripcion: "Intervención con inversión de capital",
  },
  {
    value: "emergencia_correctivos" as GrupoActividad,
    label: "Emergencia / Correctivos",
    descripcion: "Atención de fallas e incidentes",
  },
];

const SelectorTipoActividad: React.FC<SelectorTipoActividadProps> = ({
  value,
  onChange,
}) => {
  return (
    <RadioCardGroup
      name="grupo_actividad"
      label="Tipo de actividad"
      options={opciones}
      value={value}
      onChange={onChange}
      cols={3}
    />
  );
};

export default SelectorTipoActividad;
