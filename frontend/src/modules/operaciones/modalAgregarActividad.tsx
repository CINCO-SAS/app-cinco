"use client";

import { useForm, Controller } from "react-hook-form";
import { useModal } from "@/hooks/useModal";
import { Modal } from "@/components/ui/modal";
import Button from "@/components/ui/button/Button";
import { zodResolver } from "@hookform/resolvers/zod";
import { ActividadSchema, ActividadFormData } from "@/schemas/actividades.schema";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import DatePicker from "@/components/form/date-picker";
import Form from "@/components/form/Form";

const ModalAgregarActividad = () => {
    const { isOpen, openModal, closeModal } = useModal();

    const {
        register,
        control,
        handleSubmit,
        formState: { errors },
    } = useForm<ActividadFormData>({
        resolver: zodResolver(ActividadSchema),
        defaultValues: {
            descripcion: "",
            tipo_actividad: "",
            fecha_actividad: new Date().toISOString().split("T")[0],
            fecha_inicio: "",
        },
    });

    const { submit, isLoading, error } = useFormSubmit<ActividadFormData>();

    const onSubmit = async (data: ActividadFormData) => {
        console.log("DATA VALIDADA:", data);
        // alert("Funcionalidad de creación de actividad no implementada aún.");

        await submit(data, {
            endpoint: "/actividades",
            onSuccess: (response) => console.log("Actividad creada", response),
            onError: (err) => alert("Error al crear la actividad " + err.message),
        });
    };

    return (
        <>
            <Button
                className="absolute right-10 top-7.5 -translate-y-1/2 cursor-pointer"
                size="sm"
                variant="primary"
                onClick={openModal}
            >
                Nueva Actividad
            </Button>

            <Modal
                isOpen={isOpen}
                onClose={closeModal}
                className="max-w-150 p-5 lg:p-10"
            >
                <div className="mb-6 text-lg font-medium text-gray-800 dark:text-white/90">
                    Crear Nueva Actividad
                </div>

                <Form<ActividadFormData>
                    handleSubmit={handleSubmit}
                    onSubmit={onSubmit}
                    className="space-y-6"
                >
                    <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
                        {/* Fecha de Actividad */}
                        <div className="col-span-1">
                            <Label htmlFor="fecha_actividad">Fecha de Actividad</Label>
                            <Controller
                                name="fecha_actividad"
                                control={control}
                                render={({ field }) => (
                                    <DatePicker
                                        id="fecha_actividad"
                                        placeholder="Selecciona una fecha"
                                        defaultDate={field.value}
                                        onChange={(dates: Date[] | Date) => {
                                            const value = Array.isArray(dates) ? dates[0] : dates;
                                            field.onChange(value ? value.toISOString().split("T")[0] : "");
                                        }}
                                        error={!!errors.fecha_actividad}
                                        hint={errors.fecha_actividad ? errors.fecha_actividad.message : undefined}
                                    />
                                )}
                            />
                        </div>

                        {/* Descripción */}
                        <div className="col-span-1">
                            <Label htmlFor="descripcion">Descripción</Label>
                            <Controller
                                name="descripcion"
                                control={control}
                                render={({ field }) => (
                                    <Input
                                        {...field}
                                        type="text"
                                        id="descripcion"
                                        name="descripcion"
                                        placeholder="Descripción de la actividad"
                                        error={!!errors.descripcion}
                                        hint={errors.descripcion ? errors.descripcion.message : undefined}
                                    />
                                )}
                            />
                        </div>

                        {/* Tipo de Actividad */}
                        <div className="col-span-1">
                            <Label htmlFor="tipo_actividad">Tipo de Actividad</Label>
                            <Controller
                                name="tipo_actividad"
                                control={control}
                                render={({ field }) => (
                                    <Input
                                        {...field}
                                        type="text"
                                        id="tipo_actividad"
                                        name="tipo_actividad"
                                        placeholder="Tipo de actividad"
                                        error={!!errors.tipo_actividad}
                                        hint={errors.tipo_actividad ? errors.tipo_actividad.message : undefined}
                                    />
                                )}
                            />
                        </div>

                        {/* Fecha de Inicio */}
                        <div className="col-span-1">
                            <Label htmlFor="fecha_inicio">Fecha de Inicio</Label>
                            <Controller
                                name="fecha_inicio"
                                control={control}
                                render={({ field }) => (
                                    <DatePicker
                                        {...field}
                                        id="fecha_inicio"
                                        placeholder="Selecciona una fecha"
                                        onChange={(dates: Date[] | Date) => {
                                            const value = Array.isArray(dates) ? dates[0] : dates;
                                            field.onChange(value ? value.toISOString().split("T")[0] : "");
                                        }}
                                        error={!!errors.fecha_inicio}
                                        hint={errors.fecha_inicio ? errors.fecha_inicio.message : undefined}
                                    />
                                )}
                            />
                        </div>
                    </div>

                    {/* Botones */}
                    <div className="flex items-center justify-end w-full gap-3 mt-6">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={closeModal}
                        >Cerrar</Button>
                        <Button
                            type="submit"
                            size="sm"
                            disabled={isLoading}
                        >Guardar</Button>
                    </div>
                </Form>
            </Modal>
        </>
    );
};

export default ModalAgregarActividad;
