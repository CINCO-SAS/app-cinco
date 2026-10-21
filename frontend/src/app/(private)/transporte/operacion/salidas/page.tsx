import { Metadata } from "next";
import SalidasView from "@/modules/transporte/operacion/salidas/salidasView";

export const metadata: Metadata = {
  title: "Salidas - CINCO SAS",
  description: "Registro diario de salidas de móvil del módulo de Transporte.",
};

const SalidasPage = () => {
  return <SalidasView />;
};

export default SalidasPage;
