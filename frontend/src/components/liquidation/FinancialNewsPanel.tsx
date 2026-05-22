import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Jin10DataSource, Jin10NewsItem } from "./types";

const CATEGORY_COLORS: Record<Jin10NewsItem["category"], string> = {
  币圈: "border-liq-accent/50 text-liq-accent bg-liq-accent/10",
  特朗普: "border-red-500/50 text-red-400 bg-red-500/10",
  宏观: "border-liq-border text-liq-muted bg-liq-bg/60",
  外汇: "border-amber-500/40 text-amber-300/90 bg-amber-500/10",
  原油: "border-orange-500/40 text-orange-300/90 bg-orange-500/10",
  股市: "border-violet-500/40 text-violet-300/90 bg-violet-500/10",
};

type Props = {
  items: Jin10NewsItem[];
  sourceLabel: string;
  source: Jin10DataSource;
  loading?: boolean;
  activeSymbol?: string;
  lastUpdatedAt?: Date | null;
  pollSeconds?: number;
  autoRefreshEnabled?: boolean;
  onVisibleChange?: (visible: boolean) => void;
};

function formatUpdatedAt(d: Date | null | undefined): string | null {
  if (!d) return null;
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function FinancialNewsPanel({
  items,
  sourceLabel,
  source,
  loading = false,
  activeSymbol = "BTC/USDT",
  lastUpdatedAt = null,
  pollSeconds = 10,
  autoRefreshEnabled = false,
  onVisibleChange,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const base = activeSymbol.split("/")[0];
  const visibleItems = items.slice(0, 20);
  const updatedLabel = formatUpdatedAt(lastUpdatedAt);

  useEffect(() => {
    const el = rootRef.current;
    if (!el || !onVisibleChange) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        onVisibleChange(entry?.isIntersecting ?? false);
      },
      { root: null, threshold: 0.12 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [onVisibleChange]);

  return (
    <div
      ref={rootRef}
      className="flex h-full min-h-0 w-full min-w-0 flex-col"
    >
      <div className="mb-2 flex shrink-0 flex-wrap items-center justify-between gap-1.5">
        <div className="min-w-0 flex flex-col gap-0.5">
          <p className="text-[9px] leading-snug text-liq-muted">
            实时财经要闻 · 金十数据源
          </p>
          {(updatedLabel || autoRefreshEnabled) && (
            <p className="text-[8px] leading-snug text-liq-muted/90">
              {updatedLabel ? <>更新于 {updatedLabel}</> : null}
              {updatedLabel && autoRefreshEnabled ? (
                <span className="mx-1 text-liq-border">·</span>
              ) : null}
              {autoRefreshEnabled ? (
                <span className="text-liq-muted/80">
                  每 {pollSeconds}s 自动刷新
                </span>
              ) : null}
            </p>
          )}
        </div>
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wider ${
            source === "live"
              ? "border border-red-500/40 bg-red-500/10 text-red-400"
              : "border border-liq-border text-liq-muted"
          }`}
        >
          {sourceLabel}
        </span>
      </div>

      {source === "mock" && autoRefreshEnabled ? (
        <p className="mb-1.5 shrink-0 text-[8px] leading-snug text-liq-muted/75">
          直连金十 API 受浏览器 CORS 限制，当前为 Mock；自动刷新会重试接口并更新时间戳，稳定真数据需服务端代理。
        </p>
      ) : null}

      <div className="min-h-[140px] min-w-0 flex-1 overflow-y-auto overscroll-contain pr-0.5">
        {loading && visibleItems.length === 0 ? (
          <p className="animate-pulse py-6 text-center text-[10px] text-liq-muted">
            加载快讯…
          </p>
        ) : visibleItems.length === 0 ? (
          <p className="py-6 text-center text-[10px] text-liq-muted">
            暂无快讯，请稍后刷新
          </p>
        ) : (
          <ul className="flex min-w-0 flex-col gap-1.5">
            <AnimatePresence initial={false} mode="popLayout">
              {visibleItems.map((item) => {
                const isImportant = item.importance === "important";
                const highlightSymbol =
                  item.symbolTag != null && item.symbolTag === base;

                return (
                  <motion.li
                    key={item.id}
                    layout
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18 }}
                    className={`min-w-0 list-none rounded border px-2 py-1.5 ${
                      isImportant
                        ? "border-red-500/35 border-l-[3px] border-l-red-500 bg-red-950/20"
                        : "border-liq-border/60 bg-liq-bg/40"
                    }`}
                  >
                    <div className="mb-0.5 flex min-w-0 flex-wrap items-center gap-1">
                      <time className="shrink-0 font-mono text-[9px] tabular-nums text-liq-muted">
                        {item.time}
                      </time>
                      <span
                        className={`shrink-0 rounded border px-1 py-px text-[8px] font-semibold uppercase tracking-wide ${CATEGORY_COLORS[item.category]}`}
                      >
                        {item.category}
                      </span>
                      {item.symbolTag ? (
                        <span
                          className={`shrink-0 rounded border px-1 py-px font-mono text-[8px] font-bold ${
                            highlightSymbol
                              ? "border-liq-accent/60 bg-liq-accent/15 text-liq-accent"
                              : "border-liq-border text-liq-muted"
                          }`}
                        >
                          {item.symbolTag}
                        </span>
                      ) : null}
                      {isImportant ? (
                        <span className="shrink-0 text-[8px] font-bold uppercase tracking-wider text-red-400">
                          重要
                        </span>
                      ) : null}
                    </div>
                    <p
                      className={`line-clamp-3 break-words text-[10px] leading-snug ${
                        isImportant ? "font-medium text-red-50" : "text-liq-text"
                      }`}
                    >
                      {item.title}
                    </p>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </div>
  );
}
