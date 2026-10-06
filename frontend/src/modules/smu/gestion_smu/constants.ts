// src/modules/smu/gestion_smu/constants.ts
//
// Configuración y catálogos del módulo de gestión/supervisión SMU
// (`/smu/gestion_smu`).
//
// Los catálogos son espejo de los `*_CHOICES` de `SmuActividad` en el backend
// (`backend/apps/smu/models/smu_actividades.py`): si cambian allá, cambian acá.

export const GESTION_SMU_CONFIG = {
  breadcrumbTitles: ["Inicio", "SMU", "Gestión SMU"],
  title: "Gestión y supervisión de formularios SMU",
  description:
    "Historial de los formularios SMU con los datos clave para supervisarlos, filtrarlos y exportarlos.",
  csvFileName: "gestion_smu.csv",
  emptyMessage: "No hay formularios que coincidan con la búsqueda o el filtro.",
  pageSizeOptions: [10, 25, 50, 100],
  defaultPageSize: 25,
} as const;

export interface OpcionFiltro {
  valor: string;
  etiqueta: string;
}

export const CATEGORIAS_SMU: OpcionFiltro[] = [
  { valor: "preventivos", etiqueta: "Preventivos" },
  { valor: "correctivos", etiqueta: "Correctivos" },
  { valor: "emergencias", etiqueta: "Emergencias" },
  { valor: "correctivos_capex", etiqueta: "Correctivos CAPEX" },
];

export const TIPOS_FORMULARIO_SMU: OpcionFiltro[] = [
  { valor: "aire_acondicionado", etiqueta: "Aire acondicionado" },
  { valor: "planta", etiqueta: "Planta eléctrica" },
  { valor: "estandar", etiqueta: "Estándar" },
  { valor: "tipologia1", etiqueta: "Tipología 1" },
  { valor: "tipologia3", etiqueta: "Tipología 3" },
  { valor: "tipologia5", etiqueta: "Tipología 5" },
];

export const ESTADOS_SMU: OpcionFiltro[] = [
  { valor: "borrador", etiqueta: "Borrador" },
  { valor: "enviado", etiqueta: "Enviado" },
  { valor: "aprobado", etiqueta: "Aprobado" },
  { valor: "rechazado", etiqueta: "Rechazado" },
];
