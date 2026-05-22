import type {
  HeatmapLevel,
  LiquidationData,
  LiquidationSide,
  MajorLevel,
  PressureState,
} from "./types";

/** Reference spot prices — May 2026 ballpark */
export const BTC_MARKET_PRICE = 105_420;
export const ETH_MARKET_PRICE = 3_840;

/** Heatmap shows liquidation levels within ±5% of market price */
export const HEATMAP_BAND_PCT = 0.05;
export const HEATMAP_LEVEL_COUNT = 22;

/** Regenerate mock snapshot when live price moves beyond this fraction. */
export const MARKET_REGEN_THRESHOLD_PCT = 0.005;

export type LiquidationSymbol = "BTCUSDT" | "ETHUSDT";

const WINDOW_HOURS = 12;

/**
 * Stable mock seeding: PRNG is keyed by symbol + rounded price bucket so small
 * ticks and manual refresh do not reshuffle heatmap / levels / pressure.
 * Bucket: BTC nearest 50, ETH nearest 5.
 */
export function marketPriceBucket(
  symbol: LiquidationSymbol,
  price: number
): number {
  if (symbol === "ETHUSDT") {
    return Math.round(price / 5) * 5;
  }
  return Math.round(price / 50) * 50;
}

export function stableSeedKey(symbol: string, marketPrice: number): string {
  const sym = normalizeLiquidationSymbol(symbol);
  return `${sym}:${marketPriceBucket(sym, marketPrice)}`;
}

function hashSeedKey(key: string): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Mulberry32 — deterministic [0, 1) from integer seed. */
function createSeededRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function createRngForSeedKey(seedKey: string): () => number {
  return createSeededRng(hashSeedKey(seedKey));
}

export function normalizeLiquidationSymbol(symbol: string): LiquidationSymbol {
  return symbol === "ETHUSDT" ? "ETHUSDT" : "BTCUSDT";
}

export function getMarketPriceForSymbol(symbol: string): number {
  return normalizeLiquidationSymbol(symbol) === "ETHUSDT"
    ? ETH_MARKET_PRICE
    : BTC_MARKET_PRICE;
}

export function symbolDisplayLabel(symbol: string): string {
  return normalizeLiquidationSymbol(symbol) === "ETHUSDT"
    ? "ETH/USDT"
    : "BTC/USDT";
}

type Rng = () => number;

function rand(rng: Rng, min: number, max: number) {
  return min + rng() * (max - min);
}

export function heatmapPriceBounds(market: number) {
  return {
    min: market * (1 - HEATMAP_BAND_PCT),
    max: market * (1 + HEATMAP_BAND_PCT),
  };
}

function intensityAtPrice(
  rng: Rng,
  price: number,
  market: number
): Pick<HeatmapLevel, "longIntensity" | "shortIntensity"> {
  const dist = Math.abs(price - market) / market;
  const shortIntensity =
    price > market ? rand(rng, 0.35, 1) * (1 - dist * 8) : rand(rng, 0.05, 0.35);
  const longIntensity =
    price < market ? rand(rng, 0.35, 1) * (1 - dist * 8) : rand(rng, 0.05, 0.35);
  return {
    longIntensity: Math.max(0.08, Math.min(1, longIntensity)),
    shortIntensity: Math.max(0.08, Math.min(1, shortIntensity)),
  };
}

function generateHeatmap(rng: Rng, market: number): HeatmapLevel[] {
  const { min, max } = heatmapPriceBounds(market);
  const steps = HEATMAP_LEVEL_COUNT;
  const levels: HeatmapLevel[] = [];
  for (let i = 0; i < steps; i++) {
    const price = min + ((max - min) * i) / (steps - 1);
    levels.push({
      price: Math.round(price),
      ...intensityAtPrice(rng, price, market),
    });
  }
  return levels.sort((a, b) => b.price - a.price);
}

/** Keep only levels in ±5% band; re-bin evenly if too few remain. */
export function filterHeatmapToBand(
  levels: HeatmapLevel[],
  market: number,
  minLevels = HEATMAP_LEVEL_COUNT,
  rng?: Rng
): HeatmapLevel[] {
  const { min, max } = heatmapPriceBounds(market);
  const filtered = levels.filter((l) => l.price >= min && l.price <= max);
  if (filtered.length >= minLevels) {
    return filtered.sort((a, b) => b.price - a.price);
  }
  const fallbackRng = rng ?? createRngForSeedKey(`fallback:${market}`);
  return generateHeatmap(fallbackRng, market);
}

function generateMajorLevels(rng: Rng, market: number): MajorLevel[] {
  const specs: { side: LiquidationSide; label: string }[] = [
    { side: "SHORT", label: "Top Short Squeeze" },
    { side: "SHORT", label: "Short Cluster" },
    { side: "SHORT", label: "Upper Gamma Wall" },
    { side: "SHORT", label: "Gamma Wall" },
    { side: "LONG", label: "Top Long Liq" },
    { side: "LONG", label: "Long Cascade" },
    { side: "LONG", label: "Deep Long Pocket" },
    { side: "LONG", label: "Support Liq Zone" },
  ];

  return specs.map((spec, i) => {
    const price =
      spec.side === "SHORT"
        ? market * (1 + rand(rng, 0.004, 0.022))
        : market * (1 - rand(rng, 0.004, 0.022));
    const rounded = Math.round(price);
    const distancePct = ((rounded - market) / market) * 100;
    return {
      id: `lvl-${i}`,
      side: spec.side,
      label: spec.label,
      price: rounded,
      sizeUsd: Math.round(rand(rng, 12, 180) * 1e6),
      distancePct: Number(distancePct.toFixed(2)),
    };
  });
}

function derivePressure(
  heatmap: HeatmapLevel[],
  market: number
): { state: PressureState; score: number; longBias: number; shortBias: number } {
  let longSum = 0;
  let shortSum = 0;
  for (const h of heatmap) {
    if (h.price < market) longSum += h.longIntensity;
    else shortSum += h.shortIntensity;
  }
  const total = longSum + shortSum || 1;
  const longBias = longSum / total;
  const shortBias = shortSum / total;
  const score = Math.round(Math.abs(longBias - shortBias) * 100);

  let state: PressureState = "neutral";
  if (longBias > 0.58) state = "high_long_risk";
  else if (shortBias > 0.58) state = "high_short_risk";

  return { state, score, longBias, shortBias };
}

export function shouldRegenerateLiquidationSnapshot(
  prev: { seedKey: string; marketPrice: number } | null,
  symbol: string,
  marketPrice: number
): boolean {
  if (!prev) return true;
  const seedKey = stableSeedKey(symbol, marketPrice);
  if (seedKey !== prev.seedKey) return true;
  const base = prev.marketPrice > 0 ? prev.marketPrice : marketPrice;
  if (base <= 0) return true;
  return (
    Math.abs(marketPrice - prev.marketPrice) / base > MARKET_REGEN_THRESHOLD_PCT
  );
}

export function createMockLiquidationData(
  symbol = "BTCUSDT",
  marketPriceOverride?: number | null
): LiquidationData {
  const sym = normalizeLiquidationSymbol(symbol);
  const fallback = getMarketPriceForSymbol(sym);
  const displayMarket =
    marketPriceOverride != null && marketPriceOverride > 0
      ? Math.round(marketPriceOverride)
      : Math.round(fallback);
  const anchorMarket = marketPriceBucket(sym, displayMarket);
  const rng = createRngForSeedKey(stableSeedKey(sym, displayMarket));
  const heatmap = filterHeatmapToBand(
    generateHeatmap(rng, anchorMarket),
    displayMarket,
    HEATMAP_LEVEL_COUNT,
    rng
  );
  const majorLevels = generateMajorLevels(rng, anchorMarket);
  const pressure = derivePressure(heatmap, displayMarket);

  return {
    symbol: sym,
    windowHours: WINDOW_HOURS,
    marketPrice: displayMarket,
    updatedAt: Date.now(),
    heatmap,
    majorLevels,
    pressure,
  };
}
