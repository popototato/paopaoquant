import type { Candle, LinePoint, HistogramPoint, TradeMarker } from "../types";

export function computeEMA(closes: number[], period: number): (number | null)[] {
  const result: (number | null)[] = new Array(closes.length).fill(null);
  if (closes.length < period) return result;

  let sum = 0;
  for (let i = 0; i < period; i++) sum += closes[i];
  let ema = sum / period;
  result[period - 1] = ema;

  const k = 2 / (period + 1);
  for (let i = period; i < closes.length; i++) {
    ema = closes[i] * k + ema * (1 - k);
    result[i] = ema;
  }
  return result;
}

export function computeRSI(closes: number[], period = 14): (number | null)[] {
  const result: (number | null)[] = new Array(closes.length).fill(null);
  if (closes.length <= period) return result;

  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const change = closes[i] - closes[i - 1];
    if (change >= 0) avgGain += change;
    else avgLoss -= change;
  }
  avgGain /= period;
  avgLoss /= period;

  const rsiAt = (g: number, l: number) =>
    l === 0 ? 100 : 100 - 100 / (1 + g / l);

  result[period] = rsiAt(avgGain, avgLoss);

  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? -change : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    result[i] = rsiAt(avgGain, avgLoss);
  }
  return result;
}

export interface MacdResult {
  macd: (number | null)[];
  signal: (number | null)[];
  histogram: (number | null)[];
}

export function computeMACD(
  closes: number[],
  fast = 12,
  slow = 26,
  signalPeriod = 9
): MacdResult {
  const emaFast = computeEMA(closes, fast);
  const emaSlow = computeEMA(closes, slow);
  const len = closes.length;
  const macd: (number | null)[] = new Array(len).fill(null);
  const macdValues: number[] = [];

  for (let i = 0; i < len; i++) {
    if (emaFast[i] != null && emaSlow[i] != null) {
      macd[i] = emaFast[i]! - emaSlow[i]!;
      macdValues.push(macd[i]!);
    }
  }

  const signalEma = computeEMA(macdValues, signalPeriod);
  const signal: (number | null)[] = new Array(len).fill(null);
  const histogram: (number | null)[] = new Array(len).fill(null);

  let sigIdx = 0;
  for (let i = 0; i < len; i++) {
    if (macd[i] == null) continue;
    const sig = signalEma[sigIdx];
    if (sig != null) {
      signal[i] = sig;
      histogram[i] = macd[i]! - sig;
    }
    sigIdx++;
  }

  return { macd, signal, histogram };
}

export function toLineSeries(
  candles: Candle[],
  values: (number | null)[]
): LinePoint[] {
  const out: LinePoint[] = [];
  for (let i = 0; i < candles.length; i++) {
    if (values[i] != null) {
      out.push({ time: candles[i].time, value: values[i]! });
    }
  }
  return out;
}

export function toMacdHistogram(
  candles: Candle[],
  histogram: (number | null)[]
): HistogramPoint[] {
  const out: HistogramPoint[] = [];
  for (let i = 0; i < candles.length; i++) {
    if (histogram[i] != null) {
      const v = histogram[i]!;
      out.push({
        time: candles[i].time,
        value: v,
        color: v >= 0 ? "rgba(8, 153, 129, 0.65)" : "rgba(242, 54, 69, 0.65)",
      });
    }
  }
  return out;
}

/** Demo buy/sell markers from EMA20 / EMA50 cross. */
export function computeEmaCrossMarkers(
  candles: Candle[],
  ema20: (number | null)[],
  ema50: (number | null)[]
): TradeMarker[] {
  const markers: TradeMarker[] = [];
  for (let i = 1; i < candles.length; i++) {
    const p20 = ema20[i - 1];
    const c20 = ema20[i];
    const p50 = ema50[i - 1];
    const c50 = ema50[i];
    if (p20 == null || c20 == null || p50 == null || c50 == null) continue;

    const prevDiff = p20 - p50;
    const currDiff = c20 - c50;
    if (prevDiff <= 0 && currDiff > 0) {
      markers.push({
        time: candles[i].time,
        position: "belowBar",
        color: "#10b981",
        shape: "arrowUp",
        text: "EB",
      });
    } else if (prevDiff >= 0 && currDiff < 0) {
      markers.push({
        time: candles[i].time,
        position: "aboveBar",
        color: "#ef4444",
        shape: "arrowDown",
        text: "ES",
      });
    }
  }
  return markers;
}
