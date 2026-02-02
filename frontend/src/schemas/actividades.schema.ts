import { z } from "zod";

export const ActividadSchema = z.object({
  id: z.number().optional(),

  fecha_actividad: z
    .string()
    .min(1, "La fecha es requerida")
    .refine((v) => !isNaN(Date.parse(v)), {
      message: "Fecha inválida",
    }),

  descripcion: z.string().min(1, "La descripción es requerida"),

  tipo_actividad: z.string().min(1, "El tipo de actividad es requerido"),

  fecha_inicio: z
    .string()
    .min(1, "La fecha de inicio es requerida")
    .refine((v) => !isNaN(Date.parse(v)), {
      message: "Fecha de inicio inválida",
    }),
});

export type ActividadFormData = z.infer<typeof ActividadSchema>;
