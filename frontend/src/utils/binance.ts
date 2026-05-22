import type { Candle } from "../types";

export type Symbol = "ETHUSDT" | "BTCUSDT";
export type Interval = "1m" | "5m";

const REST_BASE = "https://api.binance.com/api/v3/klines";
const WS_BASE = "wss://stream.binance.com:9443/ws";

export function symbolLabel(symbol: Symbol): string {
  return symbol === "ETHUSDT" ? "ETH/USDT" : "BTC/USDT";
}

/** Binance kline row: [openTime, o, h, l, c, volume, ...] */
export async function fetchKlines(
  symbol: Symbol,
  interval: Interval,
  limit = 1000
): Promise<Candle[]> {
  const url = `${REST_BASE}?symbol=${symbol}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Binance API ${res.status}: ${res.statusText}`);
  }
  const raw: (string | number)[][] = await res.json();
  const candles: Candle[] = raw.map((row) => ({
    time: Math.floor(Number(row[0]) / 1000),
    open: parseFloat(String(row[1])),
    high: parseFloat(String(row[2])),
    low: parseFloat(String(row[3])),
    close: parseFloat(String(row[4])),
  }));
  candles.sort((a, b) => a.time - b.time);
  return candles;
}

/** @deprecated use fetchKlines */
export async function fetchEthUsdt5mKlines(): Promise<Candle[]> {
  return fetchKlines("ETHUSDT", "5m");
}

interface BinanceKlinePayload {
  t: number;
  o: string;
  h: string;
  l: string;
  c: string;
  x: boolean;
}

interface BinanceKlineMessage {
  e?: string;
  k?: BinanceKlinePayload;
}

export function parseKlinePayload(k: BinanceKlinePayload): Candle {
  return {
    time: Math.floor(k.t / 1000),
    open: parseFloat(k.o),
    high: parseFloat(k.h),
    low: parseFloat(k.l),
    close: parseFloat(k.c),
  };
}

export function applyKlineUpdate(candles: Candle[], candle: Candle): Candle[] {
  if (candles.length === 0) return [candle];
  const last = candles[candles.length - 1];
  if (last.time === candle.time) {
    return [...candles.slice(0, -1), candle];
  }
  if (candle.time > last.time) {
    return [...candles, candle];
  }
  return candles;
}

const WS_RECONNECT_BASE_MS = 1000;
const WS_RECONNECT_MAX_MS = 30000;

export function subscribeKlineStream(
  symbol: Symbol,
  interval: Interval,
  onKline: (candle: Candle, isClosed: boolean) => void
): () => void {
  const stream = `${symbol.toLowerCase()}@kline_${interval}`;
  let ws: WebSocket | null = null;
  let disposed = false;
  let reconnectAttempt = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const clearReconnectTimer = () => {
    if (reconnectTimer != null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const scheduleReconnect = () => {
    if (disposed) return;
    clearReconnectTimer();
    const delay = Math.min(
      WS_RECONNECT_BASE_MS * 2 ** reconnectAttempt,
      WS_RECONNECT_MAX_MS
    );
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  };

  const connect = () => {
    if (disposed) return;
    clearReconnectTimer();
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      ws = null;
    }

    ws = new WebSocket(`${WS_BASE}/${stream}`);
    ws.onopen = () => {
      reconnectAttempt = 0;
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data)) as BinanceKlineMessage;
        if (msg.e !== "kline" || !msg.k) return;
        onKline(parseKlinePayload(msg.k), msg.k.x);
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onerror = () => {
      /* onclose handles reconnect */
    };
    ws.onclose = () => {
      ws = null;
      if (!disposed) scheduleReconnect();
    };
  };

  connect();

  return () => {
    disposed = true;
    clearReconnectTimer();
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      ws = null;
    }
  };
}
