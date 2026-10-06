import { Metadata } from "next";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import SmuDashboard from "@/modules/smu/components/SmuDashboard";

export const metadata: Metadata = {
  title: "SMU - CINCO SAS",
  description: "Panel principal del módulo SMU de CINCO SAS.",
};

const SmuPage = () => {
  return (
    <div>
      <PageBreadcrumb pageTitle={["Inicio", "SMU"]} />
      <SmuDashboard />
    </div>
  );
};

export default SmuPage;
