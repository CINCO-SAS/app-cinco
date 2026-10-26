import { Metadata } from "next";
import KioscoView from "@/modules/transporte/operacion/kiosco/kioscoView";

export const metadata: Metadata = {
  title: "Kiosco de Despacho - CINCO SAS",
  description: "Terminal de despacho vehicular: identifique, valide y registre salidas de moviles desde el kiosco.",
};

const KioscoPage = () => {
  return <KioscoView />;
};

export default KioscoPage;
