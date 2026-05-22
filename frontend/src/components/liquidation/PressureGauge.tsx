import { motion } from "framer-motion";
import type { PressureState } from "./types";

const LABELS: Record<PressureState, string> = {
  neutral: "Neutral",
  high_long_risk: "High Long Risk",
  high_short_risk: "High Short Risk",
};

const COLORS: Record<PressureState, string> = {
  neutral: "#64748b",
  high_long_risk: "#22c55e",
  high_short_risk: "#ef4444",
};

type Props = {
  state: PressureState;
  score: number;
  longBias: number;
  shortBias: number;
  symbol?: string;
  compact?: boolean;
};

export default function PressureGauge({
  state,
  score,
  longBias,
  shortBias,
  symbol = "BTC/USDT",
  compact = false,
}: Props) {
  const needleDeg = -90 + shortBias * 180;
  const rad = (needleDeg * Math.PI) / 180;
  const needleLen = compact ? 52 : 68;
  const tipX = 100 + needleLen * Math.cos(rad);
  const tipY = 100 + needleLen * Math.sin(rad);
  const color = COLORS[state];
  const gradId = compact ? "gaugeGradCompact" : "gaugeGrad";

  return (
    <div className={`flex flex-col items-center ${compact ? "py-0.5" : ""}`}>
      <div
        className={`relative w-full ${compact ? "h-[58px] max-w-[148px]" : "h-[88px] max-w-[200px]"}`}
      >
        <svg viewBox="0 0 200 110" className="h-full w-full overflow-visible">
          <defs>
            <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#22c55e" />
              <stop offset="50%" stopColor="#64748b" />
              <stop offset="100%" stopColor="#ef4444" />
            </linearGradient>
          </defs>
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={`url(#${gradId})`}
            strokeWidth={compact ? 7 : 10}
            strokeLinecap="round"
            opacity={0.85}
          />
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1e293b"
            strokeWidth={compact ? 9 : 12}
            strokeLinecap="round"
            opacity={0.4}
          />
          <motion.line
            x1={100}
            y1={100}
            initial={false}
            animate={{ x2: tipX, y2: tipY }}
            transition={{ type: "spring", stiffness: 80, damping: 14 }}
            stroke={color}
            strokeWidth={compact ? "2" : "2.5"}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
          <circle cx="100" cy="100" r={compact ? 4 : 5} fill={color} />
        </svg>
      </div>
      <motion.p
        key={state}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className={`text-center font-semibold tracking-wide ${
          compact ? "mt-0.5 text-[10px]" : "mt-1 text-xs"
        }`}
        style={{ color }}
      >
        {LABELS[state]}
      </motion.p>
      <p
        className={`font-mono tabular-nums text-liq-muted ${
          compact ? "mt-0 text-[9px]" : "mt-0.5 text-[10px]"
        }`}
      >
        {symbol} · {score} · L {(longBias * 100).toFixed(0)}% / S{" "}
        {(shortBias * 100).toFixed(0)}%
      </p>
    </div>
  );
}
