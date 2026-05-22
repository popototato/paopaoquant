import { useMemo } from "react";
import { motion } from "framer-motion";
import { HEATMAP_BAND_PCT, heatmapPriceBounds } from "./mockData";
import type { HeatmapLevel } from "./types";

type LiqSide = "long" | "short";

/** Coinglass-style stops: dark blue/purple → green/cyan → yellow/orange peak */
const LONG_STOPS: [number, [number, number, number]][] = [
  [0, [22, 28, 52]],
  [0.22, [12, 68, 88]],
  [0.45, [13, 148, 116]],
  [0.68, [34, 211, 238]],
  [0.86, [250, 204, 21]],
  [1, [251, 146, 60]],
];

/** Warm scale: purple → red/orange → yellow/white peak */
const SHORT_STOPS: [number, [number, number, number]][] = [
  [0, [28, 22, 48]],
  [0.22, [88, 28, 135]],
  [0.45, [220, 38, 38]],
  [0.68, [249, 115, 22]],
  [0.86, [250, 204, 21]],
  [1, [255, 248, 220]],
];

function lerpChannel(a: number, b: number, t: number) {
  return Math.round(a + (b - a) * t);
}

function sampleStops(t: number, stops: [number, [number, number, number]][]): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, t));
  if (clamped <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (clamped <= stops[i][0]) {
      const [t0, c0] = stops[i - 1];
      const [t1, c1] = stops[i];
      const u = (t1 - t0) > 0 ? (clamped - t0) / (t1 - t0) : 1;
      return [
        lerpChannel(c0[0], c1[0], u),
        lerpChannel(c0[1], c1[1], u),
        lerpChannel(c0[2], c1[2], u),
      ];
    }
  }
  return stops[stops.length - 1][1];
}

/** Map normalized intensity (0–1) to Coinglass-like bar color for long/short side */
export function intensityToColor(intensity: number, side: LiqSide): string {
  const stops = side === "long" ? LONG_STOPS : SHORT_STOPS;
  const [r, g, b] = sampleStops(intensity, stops);
  const alpha = 0.42 + intensity * 0.58;
  return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(2)})`;
}

function intensityGlow(intensity: number, side: LiqSide): string | undefined {
  if (intensity < 0.72) return undefined;
  const stops = side === "long" ? LONG_STOPS : SHORT_STOPS;
  const [r, g, b] = sampleStops(intensity, stops);
  return `0 0 10px rgba(${r}, ${g}, ${b}, ${0.35 + (intensity - 0.72) * 1.2})`;
}

function formatPrice(n: number) {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatUsdM(n: number) {
  return `$${(n / 1e6).toFixed(1)}M`;
}

type Props = {
  levels: HeatmapLevel[];
  marketPrice: number;
  symbol?: string;
};

export default function Heatmap({ levels, marketPrice, symbol = "BTC/USDT" }: Props) {
  const { min: bandMin, max: bandMax } = heatmapPriceBounds(marketPrice);

  const bandLevels = useMemo(
    () =>
      levels
        .filter((l) => l.price >= bandMin && l.price <= bandMax)
        .sort((a, b) => b.price - a.price),
    [levels, bandMin, bandMax]
  );

  const maxIntensity = Math.max(
    ...bandLevels.flatMap((l) => [l.longIntensity, l.shortIntensity]),
    0.01
  );

  return (
    <div className="flex flex-col space-y-1">
      <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-wider text-liq-muted">
        <span>
          {symbol} · ±{(HEATMAP_BAND_PCT * 100).toFixed(0)}%
        </span>
        <span className="flex gap-3">
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-6 rounded-sm"
              style={{ background: intensityToColor(0.85, "long") }}
            />
            <span style={{ color: intensityToColor(0.75, "long") }}>Long liq</span>
          </span>
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-6 rounded-sm"
              style={{ background: intensityToColor(0.85, "short") }}
            />
            <span style={{ color: intensityToColor(0.75, "short") }}>Short liq</span>
          </span>
        </span>
      </div>
      <div className="mb-1 flex justify-between font-mono text-[9px] tabular-nums text-liq-muted/80">
        <span>{formatPrice(bandMax)}</span>
        <span className="text-liq-accent">{formatPrice(marketPrice)}</span>
        <span>{formatPrice(bandMin)}</span>
      </div>
      <div className="min-h-[calc(22*(1.25rem+0.5rem)+21*0.25rem)] space-y-0.5">
        {bandLevels.map((level, i) => {
          const isMarket = Math.abs(level.price - marketPrice) < marketPrice * 0.0003;
          const longW = (level.longIntensity / maxIntensity) * 100;
          const shortW = (level.shortIntensity / maxIntensity) * 100;
          const longNorm = level.longIntensity / maxIntensity;
          const shortNorm = level.shortIntensity / maxIntensity;
          const longColor = intensityToColor(longNorm, "long");
          const shortColor = intensityToColor(shortNorm, "short");

          return (
            <motion.div
              key={level.price}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.02, duration: 0.25 }}
              className={`grid grid-cols-[72px_1fr] items-center gap-2 rounded px-1 py-1 ${
                isMarket ? "bg-liq-border/30 ring-1 ring-liq-accent/40" : ""
              }`}
            >
              <span
                className={`font-mono text-[10px] tabular-nums ${
                  isMarket ? "font-semibold text-liq-accent" : "text-liq-muted"
                }`}
              >
                {formatPrice(level.price)}
              </span>
              <div className="flex h-5 items-stretch gap-0.5 overflow-hidden rounded-sm bg-[#0b0e14]/90">
                <motion.div
                  className="h-full rounded-l-sm"
                  style={{
                    width: `${longW}%`,
                    backgroundColor: longColor,
                    boxShadow: intensityGlow(longNorm, "long"),
                  }}
                  animate={{ width: `${longW}%` }}
                  transition={{ duration: 0.4 }}
                  title={`Long ${formatUsdM(level.longIntensity * 42e6)} est.`}
                />
                <motion.div
                  className="ml-auto h-full rounded-r-sm"
                  style={{
                    width: `${shortW}%`,
                    backgroundColor: shortColor,
                    boxShadow: intensityGlow(shortNorm, "short"),
                  }}
                  animate={{ width: `${shortW}%` }}
                  transition={{ duration: 0.4 }}
                  title={`Short ${formatUsdM(level.shortIntensity * 42e6)} est.`}
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
