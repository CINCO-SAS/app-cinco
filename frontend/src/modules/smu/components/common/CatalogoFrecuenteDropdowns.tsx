"use client";

import React, { useState } from "react";
import { Check, ChevronDown, X } from "lucide-react";
import {
  catalogChipKey,
  CatalogChipLike,
  CatalogChipStatus,
  useFormCatalogStore,
} from "@/store/formCatalog.store";

interface CatalogoFrecuenteDropdownsProps<T extends CatalogChipLike> {
  /** Ej: "Catálogo Frecuente SPT (Autocompletar 1-clic)". */
  title: string;
  /** Catálogo completo de chips. */
  items: T[];
  /** Id de la tarjeta dueña de los chips (ej: insumo.id). */
  cardId: string;
  /** Se ejecuta al hacer clic en un chip: aplica la plantilla a la tarjeta. */
  onApply: (item: T) => void;
}

interface DropdownPanelProps {
  label: string;
  count: number;
  tone: "pending" | "completed";
  isOpen: boolean;
  onToggle: () => void;
  emptyText: string;
  children: React.ReactNode;
}

const CHIP_STYLES: Record<CatalogChipStatus, string> = {
  pending:
    "border-gray-200 bg-white hover:border-brand-300 dark:border-gray-700 dark:bg-white/5 dark:hover:border-brand-500",
  used: "border-brand-300 bg-brand-50 ring-1 ring-brand-500/30 dark:border-brand-500/40 dark:bg-brand-500/10",
  completed:
    "border-success-200 bg-success-50 opacity-80 dark:border-success-500/30 dark:bg-success-500/10",
};

/**
 * Panel desplegable reutilizable del catálogo. "Pendientes" arranca abierto y
 * "Completados" cerrado para ganar espacio en mobile.
 */
const DropdownPanel: React.FC<DropdownPanelProps> = ({
  label,
  count,
  tone,
  isOpen,
  onToggle,
  emptyText,
  children,
}) => {
  const toneStyles =
    tone === "pending"
      ? "border-brand-200 bg-brand-50/30 dark:border-brand-500/30 dark:bg-brand-500/5"
      : "border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.02]";

  const badgeStyles =
    tone === "pending"
      ? "bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300"
      : "bg-success-100 text-success-700 dark:bg-success-500/20 dark:text-success-400";

  return (
    <div className={`rounded-lg border ${toneStyles}`}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left"
      >
        <span className="flex items-center gap-1.5">
          <span className="text-[10px] font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
            {label}
          </span>
          <span
            className={`inline-flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[9px] font-bold ${badgeStyles}`}
          >
            {count}
          </span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-gray-400 transition-transform duration-200 dark:text-gray-500 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {isOpen && (
        <div className="flex max-h-44 flex-wrap justify-center gap-1 overflow-y-auto border-t border-dashed border-gray-200 p-1.5 dark:border-gray-800">
          {count === 0 ? (
            <span className="px-0.5 text-[10px] text-gray-400 dark:text-gray-500">
              {emptyText}
            </span>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Contenedor del catálogo frecuente con dos dropdowns: "Pendientes" (los chips
 * que faltan por usar + los recién aplicados) y "Completados" (los chips ya
 * consolidados). La agrupación la deriva del estado global `formCatalog`.
 */
export function CatalogoFrecuenteDropdowns<T extends CatalogChipLike>({
  title,
  items,
  cardId,
  onApply,
}: CatalogoFrecuenteDropdownsProps<T>) {
  const cardStatuses = useFormCatalogStore(
    (state) => state.statusesByCard[cardId],
  );
  const markUsed = useFormCatalogStore((state) => state.markUsed);
  const resetChip = useFormCatalogStore((state) => state.resetChip);

  const [openPending, setOpenPending] = useState(true);
  const [openCompleted, setOpenCompleted] = useState(false);

  const statusOf = (item: T): CatalogChipStatus =>
    cardStatuses?.[catalogChipKey(item)] ?? "pending";

  const pendingItems = items.filter((item) => statusOf(item) !== "completed");
  const completedItems = items.filter((item) => statusOf(item) === "completed");

  const handleChipClick = (item: T) => {
    onApply(item);
    markUsed(cardId, catalogChipKey(item));
  };

  const renderChip = (item: T) => {
    const status = statusOf(item);

    return (
      <span
        key={catalogChipKey(item)}
        title={`${item.codigo_sap} - ${item.texto_sap}`}
        className={`inline-flex w-[calc(50%_-_0.125rem)] max-w-full items-center justify-center rounded-md border px-0.5 transition-all sm:w-[calc(33.333%_-_0.167rem)] lg:w-[calc(25%_-_0.188rem)] ${CHIP_STYLES[status]}`}
      >
        <button
          type="button"
          onClick={() => handleChipClick(item)}
          className="flex min-w-0 items-center justify-center gap-1 px-1.5 py-0.5 text-center text-[10px] font-medium text-gray-700 dark:text-gray-300"
        >
          <span className="text-brand-600 dark:text-brand-400 shrink-0 font-semibold">
            {item.codigo_sap}
          </span>
          <span className="min-w-0 truncate">{item.texto_sap}</span>
        </button>

        {status === "used" && (
          <button
            type="button"
            onClick={() => resetChip(cardId, catalogChipKey(item))}
            title="Deshacer: volver a pendiente"
            className="text-brand-500 hover:bg-brand-100 dark:hover:bg-brand-500/20 rounded p-0.5 transition-all"
          >
            <X className="h-3 w-3" />
          </button>
        )}

        {status === "completed" && (
          <Check className="text-success-500 mr-1 h-3 w-3 shrink-0" />
        )}
      </span>
    );
  };

  return (
    <div className="mb-3 rounded-xl border border-dashed border-gray-200 bg-gray-50/50 p-2.5 dark:border-gray-800 dark:bg-white/[0.01]">
      <span className="text-[11px] font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
        {title}
      </span>

      <div className="mt-1.5 space-y-1.5">
        <DropdownPanel
          label="Pendientes"
          count={pendingItems.length}
          tone="pending"
          isOpen={openPending}
          onToggle={() => setOpenPending((prev) => !prev)}
          emptyText="No hay chips pendientes."
        >
          {pendingItems.map(renderChip)}
        </DropdownPanel>

        <DropdownPanel
          label="Completados"
          count={completedItems.length}
          tone="completed"
          isOpen={openCompleted}
          onToggle={() => setOpenCompleted((prev) => !prev)}
          emptyText="Los chips aparecen aquí al guardar o cambiar de paso."
        >
          {completedItems.map(renderChip)}
        </DropdownPanel>
      </div>
    </div>
  );
}

export default CatalogoFrecuenteDropdowns;
