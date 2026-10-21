import { Metadata } from "next";
import ReporteFotoView from "@/modules/transporte/operacion/reporte-fotografico/reporteFotoView";

export const metadata: Metadata = {
  title: "Reporte Fotográfico - CINCO SAS",
  description:
    "Reporte fotográfico diario del móvil del módulo de Transporte (F3/B3).",
};

const ReporteFotoPage = () => {
  return <ReporteFotoView />;
};

export default ReporteFotoPage;
