// src/app/(private)/transporte/administracion/gestion/page.tsx

import { Metadata } from "next";
import GestionView from "@/modules/transporte/gestion/gestionView";

export const metadata: Metadata = {
  title: "Gestión de Salidas - CINCO SAS",
  description:
    "Panel de supervisión, aprobación masiva, control de novedades y cierres de área del módulo de Transporte.",
};

/**
 * Ruta de Gestión de Salidas / Backoffice (F4 / B4), dentro de Transporte / Administración.
 * Server component que monta la vista cliente.
 */
const GestionPage = () => {
  return <GestionView />;
};

export default GestionPage;
