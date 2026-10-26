// src/app/(private)/transporte/administracion/liquidaciones/page.tsx

import { Metadata } from "next";
import LiquidacionesView from "@/modules/transporte/liquidaciones/liquidacionesView";

export const metadata: Metadata = {
  title: "Liquidaciones Financieras - CINCO SAS",
  description:
    "Sábana de liquidación financiera mensual, pronto pago, cuentas de cobro y registro de pagos a vehículos.",
};

/**
 * Ruta de Liquidaciones Financieras (A2 / D3 / D4 / Tab 3), dentro de Transporte / Administración.
 * Server component que monta la vista cliente.
 */
const LiquidacionesPage = () => {
  return <LiquidacionesView />;
};

export default LiquidacionesPage;
