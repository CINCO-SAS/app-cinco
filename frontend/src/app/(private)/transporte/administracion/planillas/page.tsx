// src/app/(private)/transporte/administracion/planillas/page.tsx

import { Metadata } from "next";
import PlanillasView from "@/modules/transporte/planillas/planillasView";

export const metadata: Metadata = {
  title: "Planilla Oficial F-104 - CINCO SAS",
  description:
    "Planilla Oficial de Salida vehicular F-104 para control de despacho físico en portería.",
};

/**
 * Ruta de la pantalla de Planilla Oficial F-104 (§5.6 / S5), dentro de Transporte / Administración.
 * Servidor que monta la vista cliente.
 */
const PlanillasPage = () => {
  return <PlanillasView />;
};

export default PlanillasPage;
