import type { Candle, LinePoint, TradeMarker } from "../types";

/** Pine `max_bars_back` — Gaussian coef window (i = 0..499). */
export const MAX_LOOKBACK = 500;
/** LuxAlgo `ta.sma(..., 499)` when enough history is available. */
export const MAE_PERIOD_MAX = 499;
const MAE_PERIOD_FLOOR = 50;
/** Keep at least this many bars of visible envelope on short fetches (300–500). */
const ENVELOPE_TAIL_BARS = 80;

/** Adaptive MAE window: full 499 when n is large; shorter on typical Binance limits. */
export function resolveMaePeriod(barCount: number): number {
  if (barCount <= 1) return 1;
  if (barCount >= MAE_PERIOD_MAX + ENVELOPE_TAIL_BARS) {
    return MAE_PERIOD_MAX;
  }
  return Math.max(
    MAE_PERIOD_FLOOR,
    Math.min(MAE_PERIOD_MAX, barCount - ENVELOPE_TAIL_BARS)
  );
}

/** LuxAlgo: gauss(x, h) = exp(-(x²) / (h² × 2)). */
export function gaussianKernel(x: number, h: number): number {
  const hh = Math.max(1e-9, h);
  return Math.exp(-(x * x) / (hh * hh * 2));
}

function buildGaussianCoefs(h: number): {
  coefs: Float64Array;
  prefixDen: Float64Array;
} {
  const coefs = new Float64Array(MAX_LOOKBACK);
  const prefixDen = new Float64Array(MAX_LOOKBACK);
  let acc = 0;
  for (let i = 0; i < MAX_LOOKBACK; i++) {
    const w = gaussianKernel(i, h);
    coefs[i] = w;
    acc += w;
    prefixDen[i] = acc > 0 ? acc : 1;
  }
  return { coefs, prefixDen };
}

export interface NwPoint {
  time: number;
  value: number;
}

function sourceClose(candle: Candle): number {
  return candle.close;
}

export interface LuxNwSeries {
  nw: (NwPoint | null)[];
  upper: (number | null)[];
  lower: (number | null)[];
}

export interface NadarayaWatsonChartData {
  center: (NwPoint | null)[];
  upper: LinePoint[];
  lower: LinePoint[];
}

/**
 * LuxAlgo non-repaint endpoint NWE (`repaint = false`):
 * - out[t] = Σ close[t−i]·gauss(i,h) / Σ gauss(i,h), i = 0..min(499,t)
 * - mae = ta.sma(|close − out|, 499) × mult
 * - upper/lower = out ± mae
 *
 * Repaint mode (LuxAlgo `barstate.islast` loop) is not implemented here;
 * use this series for chart + plotshape-equivalent markers.
 */
export function computeLuxNadarayaWatson(
  candles: Candle[],
  bandwidth: number,
  mult: number
): LuxNwSeries {
  const n = candles.length;
  const nw: (NwPoint | null)[] = new Array(n).fill(null);
  const upper: (number | null)[] = new Array(n).fill(null);
  const lower: (number | null)[] = new Array(n).fill(null);
  if (n === 0) return { nw, upper, lower };

  const h = Math.max(1e-9, bandwidth);
  const envelopeMult = Math.max(0, mult);
  const { coefs, prefixDen } = buildGaussianCoefs(h);
  const outVals = new Float64Array(n);
  const absDev = new Float64Array(n);

  for (let t = 0; t < n; t++) {
    const maxLag = Math.min(MAX_LOOKBACK - 1, t);
    let sum = 0;
    for (let lag = 0; lag <= maxLag; lag++) {
      sum += sourceClose(candles[t - lag]) * coefs[lag];
    }
    const out = sum / prefixDen[maxLag];
    outVals[t] = out;
    absDev[t] = Math.abs(sourceClose(candles[t]) - out);
    nw[t] = { time: candles[t].time, value: out };
  }

  const maePeriod = resolveMaePeriod(n);
  let maeSum = 0;
  for (let t = 0; t < n; t++) {
    maeSum += absDev[t];
    if (t >= maePeriod) {
      maeSum -= absDev[t - maePeriod];
    }
    if (t >= maePeriod - 1) {
      const mae = (maeSum / maePeriod) * envelopeMult;
      upper[t] = outVals[t] + mae;
      lower[t] = outVals[t] - mae;
    }
  }

  return { nw, upper, lower };
}

export function computeNwEnvelopeBands(
  candles: Candle[],
  upper: (number | null)[],
  lower: (number | null)[]
): { upper: LinePoint[]; lower: LinePoint[] } {
  const upperPts: LinePoint[] = [];
  const lowerPts: LinePoint[] = [];
  for (let i = 0; i < candles.length; i++) {
    const u = upper[i];
    const l = lower[i];
    if (u == null || l == null) continue;
    upperPts.push({ time: candles[i].time, value: u });
    lowerPts.push({ time: candles[i].time, value: l });
  }
  return { upper: upperPts, lower: lowerPts };
}

export function nwToLineSeries(nw: (NwPoint | null)[]): LinePoint[] {
  const pts: LinePoint[] = [];
  for (const p of nw) {
    if (p) pts.push({ time: p.time, value: p.value });
  }
  return pts;
}

/** Chart-ready Lux NWE: center + MAE upper/lower bands. */
export function computeNadarayaWatson(
  candles: Candle[],
  bandwidth: number,
  mult: number
): NadarayaWatsonChartData {
  const { nw, upper, lower } = computeLuxNadarayaWatson(candles, bandwidth, mult);
  const bands = computeNwEnvelopeBands(candles, upper, lower);
  return { center: nw, upper: bands.upper, lower: bands.lower };
}

export const NW_CENTER_COLOR = "#26a69a";
export const NW_UP_COLOR = "#089981";
export const NW_DOWN_COLOR = "#f23645";

/** LuxAlgo plotshape: ▲ teal buy, ▼ red sell. */
export const NW_BUY_MARKER_COLOR = "#26a69a";
export const NW_SELL_MARKER_COLOR = "#f23645";

export const NW_ENVELOPE_UPPER_COLOR = "rgba(38, 166, 154, 0.72)";
export const NW_ENVELOPE_LOWER_COLOR = "rgba(242, 54, 69, 0.72)";

export const NW_DEFAULT_BANDWIDTH = 8;
export const NW_DEFAULT_MULT = 3;

/**
 * LuxAlgo non-repaint plotshape (`repaint = false`):
 * Buy ▲: ta.crossunder(close, lower)
 * Sell ▼: ta.crossover(close, upper)
 */
export function detectBuySellSignals(
  candles: Candle[],
  upper: (number | null)[],
  lower: (number | null)[]
): TradeMarker[] {
  const markers: TradeMarker[] = [];

  for (let i = 1; i < candles.length; i++) {
    const prevUpper = upper[i - 1];
    const currUpper = upper[i];
    const prevLower = lower[i - 1];
    const currLower = lower[i];
    if (
      prevUpper == null ||
      currUpper == null ||
      prevLower == null ||
      currLower == null
    ) {
      continue;
    }

    const prevClose = candles[i - 1].close;
    const currClose = candles[i].close;

    const crossUnderLower =
      prevClose >= prevLower && currClose < currLower;
    const crossOverUpper =
      prevClose <= prevUpper && currClose > currUpper;

    if (crossUnderLower) {
      markers.push({
        time: candles[i].time,
        position: "belowBar",
        color: NW_BUY_MARKER_COLOR,
        shape: "arrowUp",
        text: "Buy",
      });
    } else if (crossOverUpper) {
      markers.push({
        time: candles[i].time,
        position: "aboveBar",
        color: NW_SELL_MARKER_COLOR,
        shape: "arrowDown",
        text: "Sell",
      });
    }
  }
  return markers;
}
