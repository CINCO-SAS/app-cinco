import { Metadata } from "next";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { ConfiguracionesView } from "@/modules/configuraciones/components/ConfiguracionesView";

export const metadata: Metadata = {
  title: "Configuraciones - CINCO SAS",
  description: "Configuración de perfil y seguridad de la cuenta.",
};

export default function ConfiguracionesPage() {
  return (
    <div>
      <PageBreadcrumb pageTitle={["Inicio", "Configuraciones"]} />
      <ConfiguracionesView />
    </div>
  );
}
