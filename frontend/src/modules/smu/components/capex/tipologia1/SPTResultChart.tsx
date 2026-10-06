import React from "react";
import { Activity } from "lucide-react";
import { FilaMedidaSPT } from "./types";

interface SPTResultChartProps {
  filas: FilaMedidaSPT[];
}

export const SPTResultChart: React.FC<SPTResultChartProps> = ({ filas }) => {
  const puntos = filas
    .map((f) => ({ x: Number(f.distancia), y: Number(f.medida_ohmio) }))
    .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y) && p.x >= 0 && p.y >= 0)
    .sort((a, b) => a.x - b.x);

  if (puntos.length < 2) {
    return (
      <div className="flex h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-gray-200 bg-gray-50/50 p-6 text-center dark:border-gray-800 dark:bg-white/[0.02]">
        <Activity className="mb-2 h-8 w-8 text-gray-400 dark:text-gray-600" />
        <p className="text-xs font-medium text-gray-600 dark:text-gray-400">
          Curva de Resistividad de Reforma SPT
        </p>
        <p className="mt-1 text-[11px] text-gray-400 dark:text-gray-500">
          Ingrese al menos dos lecturas de distancia y ohmios para visualizar el gráfico en tiempo real.
        </p>
      </div>
    );
  }

  const maxX = Math.max(...puntos.map((p) => p.x), 1);
  const maxY = Math.max(...puntos.map((p) => p.y), 0.01);
  const W = 420;
  const H = 200;
  const padX = 50;
  const padY = 30;

  const sx = (x: number) => padX + (x / maxX) * (W - padX - 20);
  const sy = (y: number) => H - padY - (y / maxY) * (H - padY - 20);

  const path = puntos
    .map((p, i) => `${i === 0 ? "M" : "L"} ${sx(p.x).toFixed(1)} ${sy(p.y).toFixed(1)}`)
    .join(" ");

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white p-5 transition-all dark:border-gray-800 dark:bg-white/[0.02]">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-brand-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            Gráfico de Resultados Obtenidos — Reforma SPT
          </span>
        </div>
        <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-[11px] font-semibold text-brand-600 dark:bg-brand-500/10 dark:text-brand-400">
          Distancia (m) vs Ohmios (Ω)
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="h-52 w-full" role="img" aria-label="Curva de resultados SPT">
        {/* Ejes */}
        <line x1={padX} y1={20} x2={padX} y2={H - padY} stroke="currentColor" strokeWidth="1" className="text-gray-200 dark:text-gray-800" />
        <line x1={padX} y1={H - padY} x2={W - 10} y2={H - padY} stroke="currentColor" strokeWidth="1" className="text-gray-200 dark:text-gray-800" />
        
        {/* Guías intermedias */}
        <line x1={padX} y1={(H - padY + 20) / 2} x2={W - 10} y2={(H - padY + 20) / 2} stroke="currentColor" strokeWidth="0.5" strokeDasharray="3 3" className="text-gray-200 dark:text-gray-800" />

        {/* Área sombreada */}
        <path
          d={`${path} L ${sx(puntos[puntos.length - 1].x).toFixed(1)} ${H - padY} L ${sx(puntos[0].x).toFixed(1)} ${H - padY} Z`}
          fill="currentColor"
          className="text-brand-500/10 dark:text-brand-400/10"
        />

        {/* Línea principal */}
        <path d={path} fill="none" stroke="#465fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Nodos */}
        {puntos.map((p, i) => {
          const cx = sx(p.x);
          const cy = sy(p.y);
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r="4.5" fill="#ffffff" stroke="#465fff" strokeWidth="2.5" />
              <text x={cx} y={cy - 8} textAnchor="middle" className="fill-gray-700 text-[10px] font-bold dark:fill-gray-200">
                {p.y.toFixed(2)} Ω
              </text>
              <text x={cx} y={H - padY + 14} textAnchor="middle" className="fill-gray-500 text-[9px] dark:fill-gray-400">
                {p.x}m
              </text>
            </g>
          );
        })}

        {/* Etiquetas de los ejes */}
        <text x={W / 2} y={H - 4} textAnchor="middle" className="fill-gray-400 text-[9px] font-medium dark:fill-gray-500">
          Distancia (Metros)
        </text>
        <text x={12} y={H / 2} textAnchor="middle" transform={`rotate(-90 12 ${H / 2})`} className="fill-gray-400 text-[9px] font-medium dark:fill-gray-500">
          Resistencia (Ohmios Ω)
        </text>
      </svg>
    </div>
  );
};
