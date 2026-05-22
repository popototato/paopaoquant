import { motion } from "framer-motion";
import type { MajorLevel } from "./types";

function formatPrice(n: number) {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatSize(n: number) {
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  return `$${(n / 1e6).toFixed(1)}M`;
}

type Props = {
  levels: MajorLevel[];
  symbol?: string;
};

export default function MajorLevels({ levels, symbol = "BTC/USDT" }: Props) {
  const sorted = [...levels].sort((a, b) => {
    const sideRank = (side: MajorLevel["side"]) => (side === "SHORT" ? 0 : 1);
    const bySide = sideRank(a.side) - sideRank(b.side);
    if (bySide !== 0) return bySide;
    return Math.abs(b.distancePct) - Math.abs(a.distancePct);
  });

  return (
    <div className="flex flex-col">
      <p className="mb-2 text-[9px] uppercase tracking-wider text-liq-muted">
        {symbol} · Major clusters
      </p>
      <div className="space-y-1.5">
      {sorted.map((lvl, i) => {
        const isShort = lvl.side === "SHORT";
        return (
          <motion.div
            key={lvl.id}
            layout
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className={`rounded-md border border-liq-border/80 bg-liq-card/60 px-2.5 py-2.5 ${
              isShort ? "shadow-liq-glow-short" : "shadow-liq-glow-long"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <span
                  className={`text-[9px] font-bold uppercase tracking-wider ${
                    isShort ? "text-liq-short" : "text-liq-long"
                  }`}
                >
                  {lvl.side}
                </span>
                <p className="text-[11px] font-medium leading-tight text-liq-text">
                  {lvl.label}
                </p>
              </div>
              <span className="font-mono text-[11px] tabular-nums text-liq-text">
                {formatPrice(lvl.price)}
              </span>
            </div>
            <div className="mt-1.5 flex justify-between text-[10px] text-liq-muted">
              <span>
                Size{" "}
                <span className="font-mono tabular-nums text-liq-text">
                  {formatSize(lvl.sizeUsd)}
                </span>
              </span>
              <span>
                Dist{" "}
                <span
                  className={`font-mono tabular-nums ${
                    lvl.distancePct > 0 ? "text-liq-short" : "text-liq-long"
                  }`}
                >
                  {lvl.distancePct > 0 ? "+" : ""}
                  {lvl.distancePct.toFixed(2)}%
                </span>
              </span>
            </div>
          </motion.div>
        );
      })}
      </div>
    </div>
  );
}
