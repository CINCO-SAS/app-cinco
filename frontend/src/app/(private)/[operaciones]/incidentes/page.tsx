import { Metadata } from "next";
import IncidentesView from "@/modules/operaciones/incidentes/IncidentesView";

export const metadata: Metadata = {
  title: "Incidentes - Operaciones - CINCO SAS",
  description: "Consulta de incidentes en SharePoint del módulo de Operaciones de CINCO SAS.",
};

export default function IncidentesPage() {
  return <IncidentesView />;
}
