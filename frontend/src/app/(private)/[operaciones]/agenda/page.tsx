import { Metadata } from "next";
import { AgendaModule } from "@/modules/operaciones/agenda/AgendaModule";

export const metadata: Metadata = {
  title: "Agenda de Trabajos - CINCO SAS",
  description: "Módulo de Agenda y Planificación de Trabajos de CINCO SAS.",
};

export default function AgendaPage() {
  return <AgendaModule />;
}
