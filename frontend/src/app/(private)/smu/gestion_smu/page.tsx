import { Metadata } from "next";
import GestionSmuView from "@/modules/smu/gestion_smu/GestionSmuView";

export const metadata: Metadata = {
  title: "Gestión SMU - CINCO SAS",
  description:
    "Gestión y supervisión de los formularios SMU de CINCO SAS.",
};

const GestionSmuPage = () => {
  return <GestionSmuView />;
};

export default GestionSmuPage;
