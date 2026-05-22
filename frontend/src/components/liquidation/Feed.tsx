import { AnimatePresence, motion } from "framer-motion";
import type { LiquidationFeedItem } from "./types";

function formatPrice(n: number) {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatAmount(n: number) {
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${(n / 1e3).toFixed(0)}K`;
}

type Props = {
  items: LiquidationFeedItem[];
  symbol?: string;
};

const COLS =
  "grid grid-cols-[minmax(4.25rem,5rem)_minmax(2.5rem,2.75rem)_minmax(0,1fr)_minmax(3.75rem,4.75rem)] items-center gap-x-2";

export default function Feed({ items, symbol = "BTC/USDT" }: Props) {
  return (
    <div className="max-h-[168px] min-w-0 overflow-y-auto pr-0.5 scrollbar-thin">
      <p className="mb-1.5 text-[9px] text-liq-muted">
        {symbol} · 过去 12 小时内清算事件（聚合快照，非实时推送）
      </p>
      <div
        className={`${COLS} mb-1 text-[9px] uppercase tracking-wider text-liq-muted`}
      >
        <span className="min-w-0 truncate">Time</span>
        <span className="min-w-0 truncate">Side</span>
        <span className="min-w-0 truncate">Amount</span>
        <span className="min-w-0 truncate text-right">Price</span>
      </div>
      <AnimatePresence initial={false} mode="popLayout">
        {items.map((item) => {
          const isLong = item.side === "LONG";
          return (
            <motion.div
              key={item.id}
              layout
              initial={{ opacity: 0, height: 0, y: -8 }}
              animate={{ opacity: 1, height: "auto", y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.22 }}
              className={`${COLS} border-b border-liq-border/50 py-1.5 text-[10px] last:border-0`}
            >
              <span className="min-w-0 truncate font-mono tabular-nums text-liq-muted">
                {item.time}
              </span>
              <span
                className={`min-w-0 truncate font-bold ${
                  isLong ? "text-liq-long" : "text-liq-short"
                }`}
              >
                {item.side}
              </span>
              <span className="min-w-0 truncate font-mono tabular-nums text-liq-text">
                {formatAmount(item.amountUsd)}
              </span>
              <span className="min-w-0 truncate text-right font-mono tabular-nums text-liq-text">
                {formatPrice(item.price)}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
