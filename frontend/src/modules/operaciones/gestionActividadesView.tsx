"use client";

import { useEffect, useState } from "react";
import { PlusIcon } from "@/icons";
import ModalActividad from "./modalActividad";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/common/DataTable";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { ActividadFormData } from "@/schemas/actividades.schema";
import ESTADOS from "@/utils/estados";
import { useActividadStore } from "@/store/actividad.store";
import Button from "@/components/ui/button/Button";


const GestionActividadesView = () => {
    // const [actividades, setActividades] = useState<ActividadFormData[]>([]);
    const breadcrumbTitles = ["Operaciones", "Gestión de Actividades"];
    const { loadActividades, actividades } = useActividadStore();

    useEffect(() => {
        loadActividades();
    }, [loadActividades]);

    const handleEditarActividad = (id: any) => {
        alert(`Editar actividad ${id}`);
    }

    // const ESTADOS: Record<string, string> = {
    //     'pendiente': 'bg-yellow-400/50', // amarillo
    //     'en_progreso': 'bg-blue-500/50', // azul
    //     'completada': 'bg-green-500/50', // verde
    //     'cancelada': 'bg-red-500/50', // rojo
    //     'pausada': 'bg-yellow-700/50', // amarillo oscuro
    //     'reprogramada': 'bg-orange-500/50', // naranja
    // }

    // {
    //     "id": 3,
    //     "detalle": {
    //         "id": 3,
    //         "tipo_trabajo": "PRUEBA",
    //         "descripcion": "Esta es una actividad de prueba",
    //         "extra": null
    //     },
    //     "ubicacion": {
    //         "id": 3,
    //         "direccion": "Medellin",
    //         "coordenada_x": "000000000",
    //         "coordenada_y": "000000000",
    //         "zona": "SUR",
    //         "nodo": "N600"
    //     },
    //     "responsable_snapshot": {
    //         "nombre": "CARLOS ALBERTO",
    //         "area": "DEPARTAMENTO TI",
    //         "carpeta": "PROGRAMACION",
    //         "cargo": "LIDER DESARROLLADOR",
    //         "movil": "PROGRAM01"
    //     },
    //     "ot": "00003",
    //     "estado": "pendiente",
    //     "responsable_id": 2761,
    //     "fecha_inicio": "2026-02-17",
    //     "fecha_fin_estimado": "2026-02-19",
    //     "fecha_fin_real": "1900-01-01",
    //     "created_at": "2026-02-12T16:01:35.352362-05:00",
    //     "created_by": null,
    //     "updated_at": "2026-02-12T16:01:35.352362-05:00",
    //     "updated_by": null,
    //     "is_deleted": false,
    //     "deleted_at": null,
    //     "deleted_by": null
    // },

    const actividadesColumns: ColumnDef<ActividadFormData>[] = [
        {
            header: "ID",
            // accessorKey: "id",
            cell: ({ row }) => {
                const id = row.original.id;
                return (
                    <Button variant="primary" size="sm" onClick={() => handleEditarActividad(id)}>
                        editar
                    </Button>
                );

            }
        },
        {
            header: "OT",
            accessorKey: "ot",
        },
        {
            header: "ESTADO",
            accessorKey: "estado",
            cell: ({ row }) => {
                const estado = row.original.estado || "Sin estado";
                const color = ESTADOS[estado] || "bg-gray-400/50"; // color por defecto si el estado no está definido
                return (
                    <span
                        className={`px-2 py-1 rounded-full text-xs ${color}`}
                    >{estado || "Sin estado"}</span>
                );
            },
        },
        {
            header: "RESPONSABLE",
            accessorKey: "responsable_snapshot.nombre",
            cell: ({ row }) => {
                const responsable = row.original.responsable_snapshot?.nombre || "Sin responsable";
                return (<span>{responsable}</span>);
            },
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
                
                <ModalActividad iconButton={<PlusIcon />} textButton="Actividad" />

                <div className="mt-10">
                    <DataTable
                        data={actividades}
                        columns={actividadesColumns}
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