import { Metadata } from "next";
import FlotaView from "@/modules/transporte/flota/flotaView";

export const metadata: Metadata = {
  title: "Flota Vehicular - CINCO SAS",
  description:
    "Catálogo de flota vehicular del módulo de Transporte de CINCO SAS.",
};

const FlotaPage = () => {
  return <FlotaView />;
};

export default FlotaPage;
