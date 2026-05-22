import { useCallback, useEffect, useRef, useState } from "react";
import {
  createMockJin10News,
  refreshJin10Timestamps,
} from "./jin10MockData";
import { getMarketPriceForSymbol } from "./mockData";
import type { Jin10DataSource, Jin10NewsItem } from "./types";

/** Default auto-refresh interval when the news panel is visible (ms). */
export const JIN10_POLL_INTERVAL_MS = 10_000;

/**
 * Jin10 flash API is not reliably callable from the browser: responses often
 * fail CORS unless the page is served with a same-origin proxy. Auto-refresh
 * still retries on this interval; for stable live data in Streamlit, add a
 * minimal server proxy (e.g. jin10_proxy.py) rather than depending on direct fetch.
 */
const JIN10_FLASH_API =
  "https://flash-api.jin10.com/get_flash_list?channel=-8200&vip=1";

type FlashApiRow = {
  id?: string | number;
  time?: string;
  data?: { content?: string; title?: string };
  important?: number | boolean;
};

export type UseJin10NewsOptions = {
  /** Poll interval in ms; defaults to {@link JIN10_POLL_INTERVAL_MS}. */
  pollIntervalMs?: number;
  /** When false, polling pauses (e.g. panel off-screen). */
  visible?: boolean;
};

function parseFlashTime(raw?: string): string {
  if (!raw?.trim()) return "--:--";
  const match = raw.match(/(\d{1,2}):(\d{2})/);
  if (match) {
    return `${match[1].padStart(2, "0")}:${match[2]}`;
  }
  const parsed = Date.parse(raw);
  if (!Number.isNaN(parsed)) {
    const d = new Date(parsed);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }
  return "--:--";
}

function normalizeTitle(raw?: string): string {
  const text = raw?.replace(/\s+/g, " ").trim();
  return text && text.length > 0 ? text : "财经要闻";
}

async function tryFetchJin10Live(): Promise<Jin10NewsItem[] | null> {
  try {
    const res = await fetch(JIN10_FLASH_API, {
      headers: {
        "x-app-id": "1",
        "x-version": "1.0.0",
      },
      mode: "cors",
    });
    if (!res.ok) return null;
    const json = (await res.json()) as { data?: FlashApiRow[] };
    const rows = json.data;
    if (!Array.isArray(rows) || rows.length === 0) return null;

    const mapped = rows.slice(0, 16).map((row, i) => {
      const title = normalizeTitle(row.data?.content ?? row.data?.title);
      const important =
        row.important === 1 ||
        row.important === true ||
        /【|紧急|突发|特朗普|美联储|比特币|BTC|ETH/i.test(title);

      return {
        id: String(row.id ?? `live-${i}`),
        time: parseFlashTime(row.time),
        title,
        category: inferCategory(title),
        importance: important ? "important" : "normal",
        symbolTag: inferSymbolTag(title),
      } satisfies Jin10NewsItem;
    });

    return mapped.filter((item) => item.title.length > 0);
  } catch {
    return null;
  }
}

function inferCategory(title: string): Jin10NewsItem["category"] {
  if (/特朗普|Trump|白宫/i.test(title)) return "特朗普";
  if (/比特币|BTC|以太坊|ETH|币圈|加密|ETF.*BTC/i.test(title))
    return "币圈";
  if (/原油|WTI|布伦特|OPEC/i.test(title)) return "原油";
  if (/美元|欧元|日元|外汇|DXY|央行/i.test(title)) return "外汇";
  if (/纳指|标普|道指|A50|股指|PMI|PCE|美联储|通胀|GDP/i.test(title))
    return "宏观";
  if (/股|期货|指数/i.test(title)) return "股市";
  return "宏观";
}

function inferSymbolTag(title: string): "BTC" | "ETH" | undefined {
  if (/以太坊|ETH/i.test(title)) return "ETH";
  if (/比特币|BTC/i.test(title)) return "BTC";
  return undefined;
}

export function useJin10News(
  symbol = "BTCUSDT",
  marketPrice?: number | null,
  refreshTick = 0,
  options?: UseJin10NewsOptions
) {
  const pollIntervalMs = options?.pollIntervalMs ?? JIN10_POLL_INTERVAL_MS;
  const visible = options?.visible ?? true;

  const resolvedPrice =
    marketPrice != null && marketPrice > 0
      ? marketPrice
      : getMarketPriceForSymbol(symbol);

  const [items, setItems] = useState<Jin10NewsItem[]>(() =>
    createMockJin10News(symbol, resolvedPrice)
  );
  const [source, setSource] = useState<Jin10DataSource>("mock");
  const [loading, setLoading] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

  const sourceRef = useRef(source);
  sourceRef.current = source;

  const loadMock = useCallback(() => {
    const next = createMockJin10News(symbol, resolvedPrice);
    setItems(next);
    setSource("mock");
  }, [symbol, resolvedPrice]);

  const refreshTimestamps = useCallback(() => {
    setItems((prev) =>
      prev.length > 0
        ? refreshJin10Timestamps(prev)
        : createMockJin10News(symbol, resolvedPrice)
    );
  }, [symbol, resolvedPrice]);

  const applyLiveOrMockFallback = useCallback(
    (live: Jin10NewsItem[] | null, opts?: { allowMockRecreate?: boolean }) => {
      if (live && live.length > 0) {
        setItems(live);
        setSource("live");
        setLastUpdatedAt(new Date());
        return;
      }

      if (sourceRef.current === "mock") {
        setItems((prev) =>
          prev.length > 0
            ? refreshJin10Timestamps(prev)
            : opts?.allowMockRecreate
              ? createMockJin10News(symbol, resolvedPrice)
              : prev
        );
      }
      setLastUpdatedAt(new Date());
    },
    [symbol, resolvedPrice]
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    (async () => {
      const live = await tryFetchJin10Live();
      if (cancelled) return;
      if (live && live.length > 0) {
        setItems(live);
        setSource("live");
      } else {
        loadMock();
      }
      setLastUpdatedAt(new Date());
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [symbol, resolvedPrice, loadMock]);

  useEffect(() => {
    if (refreshTick <= 0) return;

    if (source === "mock") {
      refreshTimestamps();
      setLastUpdatedAt(new Date());
      return;
    }

    let cancelled = false;
    setLoading(true);
    (async () => {
      const live = await tryFetchJin10Live();
      if (cancelled) return;
      if (live && live.length > 0) {
        setItems(live);
      } else {
        loadMock();
      }
      setLastUpdatedAt(new Date());
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshTick, source, refreshTimestamps, loadMock]);

  useEffect(() => {
    if (!visible || pollIntervalMs <= 0) return;

    let cancelled = false;

    const tick = async () => {
      const live = await tryFetchJin10Live();
      if (cancelled) return;
      applyLiveOrMockFallback(live);
    };

    const id = window.setInterval(tick, pollIntervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [visible, pollIntervalMs, applyLiveOrMockFallback]);

  const sourceLabel =
    source === "live" ? "金十 · 实时" : "金十数据 · Mock";

  const pollSeconds = Math.round(pollIntervalMs / 1000);

  return {
    items,
    source,
    sourceLabel,
    loading,
    refreshTimestamps,
    lastUpdatedAt,
    pollIntervalMs,
    pollSeconds,
    autoRefreshEnabled: visible && pollIntervalMs > 0,
  };
}
