import { Metadata } from "next";
import { InformesView } from "@/modules/transporte/informes/informesView";

export const metadata: Metadata = {
  title: "Informes - CINCO SAS",
  description:
    "Sábana de informes de transporte de CINCO SAS: transporte por día y por mes, con desglose por área y carpeta.",
};

/**
 * Ruta de la pantalla de Informes (F5), dentro de Transporte / Administración.
 *
 * Es un Server Component que solo monta la vista (que sí es cliente), igual
 * que el resto de pantallas del módulo. El contenido vive en el módulo.
 */
const InformesPage = () => {
  return <InformesView />;
};

export default InformesPage;
