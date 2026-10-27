import { Metadata } from "next";
import DuenosView from "@/modules/transporte/duenos/duenosView";

export const metadata: Metadata = {
  title: "Dueños de Vehículos - CINCO SAS",
  description:
    "Catálogo de dueños y propietarios de vehículos, asignación de flota vehicular y gestión de cuentas bancarias.",
};

const DuenosPage = () => {
  return <DuenosView />;
};

export default DuenosPage;
