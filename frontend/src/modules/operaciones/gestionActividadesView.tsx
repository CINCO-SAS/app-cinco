"use client";

import { DataTable } from "@/components/common/DataTable";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { ColumnDef } from "@tanstack/react-table";
import ModalAgregarActividad from "./modalAgregarActividad";

interface User {
    id: number;
    name: string;
    email: string;
    role: "Admin" | "Editor" | "Viewer";
    status: "Active" | "Inactive" | "Pending";
    dateCreated?: string;
    editedBy?: string;
    functions?: string[];
    comments?: string;
    tags?: string[];
}

const GestionActividadesView = () => {
    const breadcrumbTitles = ["Operaciones", "Gestión de Actividades"];

    const userData: User[] = [
        {
            id: 1,
            name: "Carlos Restrepo",
            email: "carlos@example.com",
            role: "Admin",
            status: "Active",
            dateCreated: "2024-01-15",
            editedBy: "Maria Lopez",
            functions: ["Create", "Edit", "Delete"],
            comments: "Usuario con permisos completos.",
            tags: ["priority", "internal"],
        },
        {
            id: 2,
            name: "Ana Gómez",
            email: "ana@example.com",
            role: "Editor",
            status: "Pending",
            dateCreated: "2024-02-20",
            editedBy: "Luis Fernandez",
            functions: ["Edit"],
            comments: "Usuario en espera de aprobación.",
            tags: ["review"],
        },
        {
            id: 3,
            name: "Jorge Martínez",
            email: "jorge@example.com",
            role: "Viewer",
            status: "Inactive",
            dateCreated: "2024-03-10",
            editedBy: "Sofia Ramirez",
            functions: ["View"],
            comments: "Usuario inactivo.",
            tags: ["archived"],
        },
        {
            id: 4,
            name: "Lindsey Curtis",
            email: "lindsey@example.com",
            role: "Editor",
            status: "Active",
            dateCreated: "2024-04-05",
            editedBy: "Carlos Mendoza",
            functions: ["Edit", "View"],
            comments: "Editor activo con permisos limitados.",
            tags: ["active", "editor"],
        },
        {
            id: 5,
            name: "Jorge Martínez",
            email: "jorge@example.com",
            role: "Viewer",
            status: "Inactive",
            dateCreated: "2024-05-12",
            editedBy: "Ana Torres",
            functions: ["View"],
            comments: "Usuario inactivo.",
            tags: ["archived"],
        },
        {
            id: 6,
            name: "Lindsey Curtis",
            email: "lindsey@example.com",
            role: "Editor",
            status: "Active",
            dateCreated: "2024-06-01",
            editedBy: "Michael Scott",
            functions: ["Edit", "View"],
            comments: "Editor activo con permisos limitados.",
            tags: ["active", "editor"],
        },
        {
            id: 7,
            name: "Jorge Martínez",
            email: "jorge@example.com",
            role: "Viewer",
            status: "Inactive",
            dateCreated: "2024-06-15",
            editedBy: "Pam Beesly",
            functions: ["View"],
            comments: "Usuario inactivo.",
            tags: ["archived"],
        },
        {
            id: 8,
            name: "Lindsey Curtis",
            email: "lindsey@example.com",
            role: "Editor",
            status: "Active",
            dateCreated: "2024-06-20",
            editedBy: "Jim Halpert",
            functions: ["Edit", "View"],
            comments: "Editor activo con permisos limitados.",
            tags: ["active", "editor"],
        },
        {
            id: 9,
            name: "Jorge Martínez",
            email: "jorge@example.com",
            role: "Viewer",
            status: "Inactive",
            dateCreated: "2024-06-25",
            editedBy: "Dwight Schrute",
            functions: ["View"],
            comments: "Usuario inactivo.",
            tags: ["archived"],
        },
        {
            id: 10,
            name: "Lindsey Curtis",
            email: "lindsey@example.com",
            role: "Editor",
            status: "Active",
            dateCreated: "2024-06-30",
            editedBy: "Stanley Hudson",
            functions: ["Edit", "View"],
            comments: "Editor activo con permisos limitados.",
            tags: ["active", "editor"],
        },
        {
            id: 11,
            name: "Jorge Martínez",
            email: "jorge@example.com",
            role: "Viewer",
            status: "Inactive",
            dateCreated: "2024-07-05",
            editedBy: "Phyllis Vance",
            functions: ["View"],
            comments: "Usuario inactivo.",
            tags: ["archived"],
        },
        {
            id: 12,
            name: "Lindsey Curtis",
            email: "lindsey@example.com",
            role: "Editor",
            status: "Active",
            dateCreated: "2024-07-10",
            editedBy: "Kevin Malone",
            functions: ["Edit", "View"],
            comments: "Editor activo con permisos limitados.",
            tags: ["active", "editor"],
        },
    ];

    const userColumns: ColumnDef<User>[] = [
        {
            header: "ID",
            accessorKey: "id",
        },
        {
            header: "Name",
            accessorKey: "name",
        },
        {
            header: "Email",
            accessorKey: "email",
        },
        {
            header: "Role",
            accessorKey: "role",
        },
        {
            header: "Status",
            cell: ({ row }) => {
                const status = row.original.status;
                const color =
                    status === "Active" ? "green" : status === "Pending" ? "yellow" : "red";

                return (
                    <span
                        className={`px-2 py-1 rounded-full text-white text-xs bg-${color}-500`}
                    >
                        {status}
                    </span>
                );
            },
        },
        {
            header: "Date Created",
            accessorKey: "dateCreated",
        },
        {
            header: "Edited By",
            accessorKey: "editedBy",
        },
        {
            header: "Functions",
            cell: ({ row }) => row.original.functions?.join(", "),
        },
        {
            header: "Comments",
            accessorKey: "comments",
        },
        {
            header: "Tags",
            cell: ({ row }) => row.original.tags?.join(", "),
        },
    ];

    return (
        <div>
            <PageBreadcrumb pageTitle={breadcrumbTitles} />
            <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-5 py-7 dark:border-gray-800 dark:bg-white/3 xl:px-10 xl:py-12 overflow-auto relative">
                <div className="mx-auto w-full max-w-157.5 text-center">
                    <h3 className="mb-4 font-semibold text-gray-800 text-theme-xl dark:text-white/90 sm:text-2xl">
                        Modulo de Gestión de Actividades
                    </h3>

                    <p className="text-gray-600 dark:text-white/70">
                        Aquí podrás gestionar todas las actividades relacionadas con las operaciones de CINCO SAS.
                    </p>
                </div>
                
                <ModalAgregarActividad />

                <div className="mt-10">
                    <DataTable
                        data={userData}
                        columns={userColumns}
                        enablePagination={true}
                        pageSize={6}
                        emptyMessage="No hay actividades para mostrar."
                        enableGlobalFilter={true}
                        enableSorting={true}
                        enableColumnFilters={true}
                        pageSizeOptions={[5, 10, 25, 50, 100]}
                    />
                </div>
            </div>
        </div>
    )

}

export default GestionActividadesView;