import type { ReactNode } from "react";
import { useState } from "react";
import { motion } from "framer-motion";
import { symbolDisplayLabel } from "./mockData";
import { useLiquidationData } from "./useLiquidationData";
import { useJin10News } from "./useJin10News";
import Heatmap from "./Heatmap";
import MajorLevels from "./MajorLevels";
import PressureGauge from "./PressureGauge";
import FinancialNewsPanel from "./FinancialNewsPanel";

type Props = {
  symbol?: string;
  /** Live spot from chart; falls back to mock per symbol when absent */
  marketPrice?: number | null;
};

function ModuleCard({
  title,
  children,
  className = "",
  growContent = true,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  /** When false, content keeps natural height (heatmap / major levels) */
  growContent?: boolean;
}) {
  return (
    <motion.section
      layout
      className={`flex flex-col rounded-lg border border-liq-border bg-liq-card/80 p-3 shadow-liq-card backdrop-blur-sm ${className}`}
    >
      <h3 className="mb-2.5 shrink-0 text-[10px] font-semibold uppercase tracking-[0.12em] text-liq-muted">
        {title}
      </h3>
      <div className={growContent ? "min-h-0 flex-1" : ""}>{children}</div>
    </motion.section>
  );
}

export default function LiquidationZonePanel({
  symbol = "BTCUSDT",
  marketPrice = null,
}: Props) {
  const [newsRefreshTick, setNewsRefreshTick] = useState(0);
  const [newsPanelVisible, setNewsPanelVisible] = useState(true);
  const { data, refreshing, refresh } = useLiquidationData(symbol, marketPrice);
  const {
    items: newsItems,
    source: newsSource,
    sourceLabel: newsSourceLabel,
    loading: newsLoading,
    lastUpdatedAt: newsLastUpdatedAt,
    pollSeconds: newsPollSeconds,
    autoRefreshEnabled: newsAutoRefresh,
  } = useJin10News(symbol, marketPrice, newsRefreshTick, {
    visible: newsPanelVisible,
  });

  const handleRefresh = () => {
    refresh();
    setNewsRefreshTick((n) => n + 1);
  };

  if (!data) {
    return (
      <section className="flex w-full max-w-none shrink-0 items-center justify-center border-t border-liq-border bg-liq-bg px-4 py-8">
        <span className="animate-pulse text-xs text-liq-muted">
          加载 12H 清算区…
        </span>
      </section>
    );
  }

  const pairLabel = symbolDisplayLabel(data.symbol);

  const updatedLabel = new Date(data.updatedAt).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <section className="flex w-full max-w-none shrink-0 flex-col border-t border-liq-border bg-liq-bg">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-liq-border px-2 py-2.5">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-liq-text">
              Liquidation Zone
            </h2>
            <span className="rounded border border-liq-accent/40 bg-liq-accent/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-liq-accent">
              Mock · 12H
            </span>
          </div>
          <p className="mt-0.5 font-mono text-[10px] tabular-nums text-liq-muted">
            {pairLabel} · 市价{" "}
            <span className="text-liq-accent">
              {data.marketPrice.toLocaleString()}
            </span>
            <span className="mx-1 text-liq-border">·</span>
            过去 {data.windowHours} 小时聚合快照
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="rounded border border-liq-border bg-liq-card px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-liq-text transition hover:border-liq-accent/50 hover:text-liq-accent disabled:opacity-50"
        >
          {refreshing ? "刷新中…" : "手动刷新"}
        </button>
      </header>

      <motion.div
        className="grid w-full grid-cols-1 items-stretch gap-2 p-2 lg:grid-cols-[1fr_1fr] lg:min-h-[720px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.35 }}
      >
        {/* Left: heatmap + major (natural height) + pressure */}
        <div className="flex w-full min-w-0 flex-col gap-2">
          <div className="grid shrink-0 grid-cols-1 gap-2 sm:grid-cols-2 sm:items-stretch">
            <ModuleCard
              title={`12H Liquidation Heatmap · ${pairLabel}`}
              className="flex w-full min-w-0 flex-col"
              growContent={false}
            >
              <Heatmap
                levels={data.heatmap}
                marketPrice={data.marketPrice}
                symbol={pairLabel}
              />
            </ModuleCard>

            <ModuleCard
              title={`12H Major Liquidation Levels · ${pairLabel}`}
              className="flex w-full min-w-0 flex-col"
              growContent={false}
            >
              <MajorLevels levels={data.majorLevels} symbol={pairLabel} />
            </ModuleCard>
          </div>

          <ModuleCard
            title={`12H Liquidation Pressure · ${pairLabel}`}
            className="flex w-full min-w-0 shrink-0 flex-col justify-center p-2"
            growContent={false}
          >
            <PressureGauge
              compact
              state={data.pressure.state}
              score={data.pressure.score}
              longBias={data.pressure.longBias}
              shortBias={data.pressure.shortBias}
              symbol={pairLabel}
            />
          </ModuleCard>
        </div>

        {/* Right: financial news full height */}
        <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
          <ModuleCard
            title="金十 · 全球快讯"
            className="flex h-full min-h-0 min-w-0 flex-1 flex-col p-2.5"
          >
            <FinancialNewsPanel
              items={newsItems}
              source={newsSource}
              sourceLabel={newsSourceLabel}
              loading={newsLoading}
              activeSymbol={pairLabel}
              lastUpdatedAt={newsLastUpdatedAt}
              pollSeconds={newsPollSeconds}
              autoRefreshEnabled={newsAutoRefresh}
              onVisibleChange={setNewsPanelVisible}
            />
          </ModuleCard>
        </div>
      </motion.div>

      <footer className="border-t border-liq-border px-2 py-1.5 text-center text-[9px] text-liq-muted">
        12H 静态快照 · Mock 数据 · 更新于 {updatedLabel}
      </footer>
    </section>
  );
}
