"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { AgendaHeaderTabs, AgendaActiveTab } from "./components/AgendaHeaderTabs";
import { AgendaFiltrosTab } from "./components/AgendaFiltrosTab";
import { AgendaFormularioTab } from "./components/AgendaFormularioTab";
import { AgendaImportarCsvTab } from "./components/AgendaImportarCsvTab";
import { AgendaPanelTecnicos } from "./components/AgendaPanelTecnicos";
import { AgendaCalendarioGrid } from "./components/AgendaCalendarioGrid";
import {
  AgendaItem,
  FiltrosAgendaState,
  TecnicoActivoAgenda,
} from "@/types/agenda.types";
import { agendaService } from "@/services/agenda.service";

export const AgendaModule: React.FC = () => {
  const hoy = new Date();
  const mesActual = String(hoy.getMonth() + 1).padStart(2, "0");
  const anioActual = String(hoy.getFullYear());

  const [activeTab, setActiveTab] = useState<AgendaActiveTab>("filtro");
  const [panelTecnicosCollapsed, setPanelTecnicosCollapsed] = useState<boolean>(false);

  // Estado de Filtros
  const [filtros, setFiltros] = useState<FiltrosAgendaState>({
    sede: "",
    mes: mesActual,
    yyyy: anioActual,
    cedula: "",
    actividad: "",
    nombre: "",
    area: "",
    carpeta: "",
  });

  // Datos
  const [agendamientosAll, setAgendamientosAll] = useState<AgendaItem[]>([]);
  const [tecnicos, setTecnicos] = useState<TecnicoActivoAgenda[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Cargar técnicos activos
  const cargarTecnicos = useCallback(async () => {
    try {
      const data = await agendaService.getTecnicosActivos();
      setTecnicos(data || []);
    } catch (error: any) {
      console.error("Error al cargar técnicos activos:", error?.message || error?.detail || error);
    }
  }, []);

  // Cargar agendamientos del mes
  const cargarAgendasMes = useCallback(async (mes: string, yyyy: string) => {
    setIsLoading(true);
    try {
      const rawData = await agendaService.getAgendasMes(mes, yyyy);
      const listaPlana: AgendaItem[] = [];

      if (Array.isArray(rawData)) {
        rawData.forEach((item: any) => {
          if (item && (item.id || item.actividad_id || item.fecha_inicio)) {
            // Formato relacional moderno
            const tipoTrabajo = item.tipo_trabajo || item.nombre_act || item.ot || "";
            listaPlana.push({
              id: item.id,
              actividad_id: item.actividad_id,
              empleado_id: item.responsable_id,
              cedula: String(item.responsable_cedula || item.cedula || item.responsable_id || ""),
              fecha: item.fecha_inicio,
              fecha_inicio: item.fecha_inicio,
              fecha_fin: item.fecha_fin,
              sede: item.sede,
              area: item.responsable_area || "",
              carpeta: item.responsable_carpeta || "",
              nombre_act: tipoTrabajo,
              tipo_trabajo: tipoTrabajo,
              nombre: item.responsable_nombre || "",
              responsable_nombre: item.responsable_nombre || "",
              responsable_link_foto: item.responsable_link_foto || item.link_foto || "",
              link_foto: item.responsable_link_foto || item.link_foto || "",
              actividad: item.ot || "",
              ot: item.ot || "",
              estado: item.actividad_estado || "PROGRAMADO",
              color: item.color_hex || "#66bb6a",
              ubicacion_direccion: item.direccion || "",
              direccion: item.direccion || "",
              ubicacion_zona: item.zona || "",
              zona: item.zona || "",
              ubicacion_nodo: item.nodo || "",
              nodo: item.nodo || "",
              latitud: item.latitud || "",
              longitud: item.longitud || "",
              detalle_descripcion: item.descripcion || item.observacion || "",
              observacion: item.observacion || item.descripcion || "",
              datos: {
                legacy_responsable_nombre: item.responsable_nombre,
                nombre_act: tipoTrabajo,
                color: item.color_hex,
                ubicacion_direccion: item.direccion,
                ubicacion_zona: item.zona,
                ubicacion_nodo: item.nodo,
                latitud: item.latitud,
                longitud: item.longitud,
              },
            });
          } else if (typeof item === "object" && item !== null) {
            // Manejo de compatibilidad legacy si viniera agrupado por días
            Object.values(item).forEach((diaItems) => {
              if (Array.isArray(diaItems)) {
                diaItems.forEach((legacyItem: any) => {
                  if (legacyItem && (legacyItem.cedula || legacyItem.empleado_id)) {
                    listaPlana.push(legacyItem);
                  }
                });
              }
            });
          }
        });
      }

      setAgendamientosAll(listaPlana);
    } catch (error: any) {
      console.error("Error al cargar agendamientos:", error?.message || error?.detail || error);
      setAgendamientosAll([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarTecnicos();
  }, [cargarTecnicos]);

  useEffect(() => {
    cargarAgendasMes(filtros.mes, filtros.yyyy);
  }, [filtros.mes, filtros.yyyy, cargarAgendasMes]);

  const refrescarDatosCompletos = useCallback(() => {
    cargarTecnicos();
    cargarAgendasMes(filtros.mes, filtros.yyyy);
  }, [cargarTecnicos, cargarAgendasMes, filtros.mes, filtros.yyyy]);

  // Áreas y Carpetas disponibles en base a los agendamientos y técnicos cargados
  const areasDisponibles = useMemo(() => {
    const setAreas = new Set<string>();
    tecnicos.forEach((t) => t.area && setAreas.add(t.area));
    agendamientosAll.forEach((a) => a.area && setAreas.add(a.area));
    return Array.from(setAreas).sort();
  }, [tecnicos, agendamientosAll]);

  const carpetasDisponibles = useMemo(() => {
    const setCarpetas = new Set<string>();
    tecnicos.forEach((t) => t.carpeta && setCarpetas.add(t.carpeta));
    agendamientosAll.forEach((a) => a.carpeta && setCarpetas.add(a.carpeta));
    return Array.from(setCarpetas).sort();
  }, [tecnicos, agendamientosAll]);

  // Filtrar los agendamientos según los filtros activos
  const agendamientosFiltrados = useMemo(() => {
    return agendamientosAll.filter((item) => {
      if (filtros.sede && item.sede?.toLowerCase() !== filtros.sede.toLowerCase()) {
        return false;
      }
      if (filtros.cedula && String(item.cedula) !== String(filtros.cedula)) {
        return false;
      }
      if (
        filtros.actividad &&
        !item.actividad?.toLowerCase().includes(filtros.actividad.toLowerCase()) &&
        !item.ot?.toLowerCase().includes(filtros.actividad.toLowerCase())
      ) {
        return false;
      }
      if (
        filtros.nombre &&
        !item.nombre_act?.toLowerCase().includes(filtros.nombre.toLowerCase()) &&
        !item.nombre?.toLowerCase().includes(filtros.nombre.toLowerCase())
      ) {
        return false;
      }
      if (
        filtros.area &&
        (item.area || "").trim().toLowerCase() !== filtros.area.trim().toLowerCase()
      ) {
        return false;
      }
      if (
        filtros.carpeta &&
        (item.carpeta || "").trim().toLowerCase() !== filtros.carpeta.trim().toLowerCase()
      ) {
        return false;
      }
      return true;
    });
  }, [agendamientosAll, filtros]);

  // Filtrar técnicos a mostrar en las filas del cronograma
  const tecnicosParaCalendario = useMemo(() => {
    // Mapa base con los técnicos obtenidos del servicio
    const mapaTec = new Map<string, TecnicoActivoAgenda>();
    tecnicos.forEach((t) => {
      if (t.cedula) mapaTec.set(String(t.cedula), t);
    });

    // Añadir técnicos que tengan agendamientos en el mes actual si no estaban en la lista
    agendamientosAll.forEach((a) => {
      const cedKey = String(a.cedula || "");
      if (cedKey && !mapaTec.has(cedKey)) {
        const numId = typeof a.id === "number" ? a.id : Number(a.id) || null;
        const numEmpId = typeof a.empleado_id === "number" ? a.empleado_id : Number(a.empleado_id) || null;
        mapaTec.set(cedKey, {
          id: numId,
          empleado_id: numEmpId,
          cedula: cedKey,
          nombre: a.nombre || a.datos?.legacy_responsable_nombre || `Técnico ${cedKey}`,
          sede: a.sede || "",
          area: a.area || "",
          carpeta: a.carpeta || "",
          link_foto: a.responsable_link_foto || a.link_foto || "",
        });
      }
    });

    const listaUnificada = Array.from(mapaTec.values());
    return listaUnificada.filter((t) => {
      if (filtros.sede && t.sede && t.sede.toLowerCase() !== filtros.sede.toLowerCase()) {
        return false;
      }
      if (filtros.cedula && String(t.cedula) !== String(filtros.cedula)) {
        return false;
      }
      if (
        filtros.area &&
        (t.area || "").trim().toUpperCase() !== filtros.area.trim().toUpperCase()
      ) {
        return false;
      }
      if (
        filtros.carpeta &&
        (t.carpeta || "").trim().toUpperCase() !== filtros.carpeta.trim().toUpperCase()
      ) {
        return false;
      }
      return true;
    });
  }, [tecnicos, agendamientosAll, filtros]);

  const handleLimpiarFiltros = () => {
    setFiltros((prev) => ({
      ...prev,
      sede: "",
      cedula: "",
      actividad: "",
      nombre: "",
      area: "",
      carpeta: "",
    }));
  };

  const handleSeleccionarFiltroEnPanel = (params: {
    area?: string;
    carpeta?: string;
    cedula?: string;
  }) => {
    setFiltros((prev) => ({
      ...prev,
      area: params.area !== undefined ? params.area : prev.area,
      carpeta: params.carpeta !== undefined ? params.carpeta : prev.carpeta,
      cedula: params.cedula !== undefined ? params.cedula : prev.cedula,
    }));
  };

  return (
    <div className="w-full min-w-0 space-y-4">
      {/* Indicador de navegación y título estándar */}
      <PageBreadcrumb pageTitle={["Operaciones", "Agenda de Trabajos"]} />

      <div className="flex flex-col h-[calc(100vh-145px)] w-full overflow-hidden bg-gray-100 dark:bg-gray-950 rounded-xl border border-gray-200 dark:border-gray-800 shadow-xs">
        {/* Pestañas Superiores */}
        <AgendaHeaderTabs activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Contenido según pestaña activa */}
        {activeTab === "filtro" && (
          <AgendaFiltrosTab
            filtros={filtros}
            setFiltros={setFiltros}
            tecnicos={tecnicos}
            areasDisponibles={areasDisponibles}
            carpetasDisponibles={carpetasDisponibles}
            onBuscar={() => cargarAgendasMes(filtros.mes, filtros.yyyy)}
            onLimpiar={handleLimpiarFiltros}
            isLoading={isLoading}
          />
        )}

        {activeTab === "agendar" && (
          <AgendaFormularioTab
            tecnicos={tecnicos}
            onAgendaGuardada={refrescarDatosCompletos}
            sedeDefault={filtros.sede || "medellin"}
          />
        )}

        {activeTab === "importar" && (
          <AgendaImportarCsvTab
            onImportacionFinalizada={refrescarDatosCompletos}
          />
        )}

        {/* Área Principal: Panel Lateral de Técnicos + Calendario Grid */}
        <div className="flex flex-1 overflow-hidden">
          <AgendaPanelTecnicos
            tecnicos={tecnicos}
            filtroArea={filtros.area}
            filtroCarpeta={filtros.carpeta}
            cedulaSeleccionada={filtros.cedula}
            onSeleccionarFiltro={handleSeleccionarFiltroEnPanel}
            isCollapsed={panelTecnicosCollapsed}
            onToggleCollapse={() => setPanelTecnicosCollapsed(!panelTecnicosCollapsed)}
          />

          <AgendaCalendarioGrid
            mes={filtros.mes}
            yyyy={filtros.yyyy}
            agendamientos={agendamientosFiltrados}
            tecnicos={tecnicosParaCalendario}
            isLoading={isLoading}
            onAgendaActualizada={refrescarDatosCompletos}
          />
        </div>
      </div>
    </div>
  );
};
