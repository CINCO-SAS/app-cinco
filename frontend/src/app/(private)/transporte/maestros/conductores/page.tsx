import { Metadata } from "next";
import ConductoresView from "@/modules/transporte/conductores/conductoresView";

export const metadata: Metadata = {
  title: "Conductores - CINCO SAS",
  description:
    "Catálogo de conductores del módulo de Transporte de CINCO SAS.",
};

const ConductoresPage = () => {
  return <ConductoresView />;
};

export default ConductoresPage;
