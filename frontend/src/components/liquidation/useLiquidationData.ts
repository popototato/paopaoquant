import { useCallback, useEffect, useRef, useState } from "react";
import {
  createMockLiquidationData,
  shouldRegenerateLiquidationSnapshot,
  stableSeedKey,
} from "./mockData";
import type { LiquidationData } from "./types";

export function useLiquidationData(
  symbol = "BTCUSDT",
  marketPrice?: number | null
) {
  const [data, setData] = useState<LiquidationData | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const snapshotRef = useRef<{
    seedKey: string;
    marketPrice: number;
  } | null>(null);

  const resolvedMarket =
    marketPrice != null && marketPrice > 0 ? Math.round(marketPrice) : null;

  const applySnapshot = useCallback((next: LiquidationData) => {
    snapshotRef.current = {
      seedKey: stableSeedKey(next.symbol, next.marketPrice),
      marketPrice: next.marketPrice,
    };
    setData(next);
  }, []);

  const load = useCallback(
    (sym: string, liveMarket: number | null, force = false) => {
      const raw = createMockLiquidationData(sym, liveMarket);
      const meta = {
        seedKey: stableSeedKey(raw.symbol, raw.marketPrice),
        marketPrice: raw.marketPrice,
      };

      if (
        !force &&
        !shouldRegenerateLiquidationSnapshot(snapshotRef.current, sym, raw.marketPrice)
      ) {
        setData((prev) =>
          prev
            ? {
                ...prev,
                marketPrice: raw.marketPrice,
                updatedAt: Date.now(),
              }
            : raw
        );
        snapshotRef.current = meta;
        return;
      }

      applySnapshot(raw);
    },
    [applySnapshot]
  );

  const refresh = useCallback(() => {
    setRefreshing(true);
    setData((prev) => {
      if (!prev) return prev;
      return { ...prev, updatedAt: Date.now() };
    });
    window.setTimeout(() => setRefreshing(false), 280);
  }, []);

  useEffect(() => {
    load(symbol, resolvedMarket);
  }, [symbol, resolvedMarket, load]);

  return { data, refreshing, refresh };
}
