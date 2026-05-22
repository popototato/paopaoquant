import { useCallback, useEffect, useRef, useState } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  CrosshairMode,
  ColorType,
} from "lightweight-charts";
import {
  fetchKlines,
  subscribeKlineStream,
  applyKlineUpdate,
  symbolLabel,
  type Symbol,
  type Interval,
} from "../utils/binance";
import {
  computeEMA,
  computeRSI,
  computeMACD,
  toLineSeries,
  toMacdHistogram,
  computeEmaCrossMarkers,
} from "../utils/indicators";
import {
  computeLuxNadarayaWatson,
  computeNwEnvelopeBands,
  nwToLineSeries,
  detectBuySellSignals,
  NW_CENTER_COLOR,
  NW_UP_COLOR,
  NW_DOWN_COLOR,
  NW_BUY_MARKER_COLOR,
  NW_SELL_MARKER_COLOR,
  NW_ENVELOPE_UPPER_COLOR,
  NW_ENVELOPE_LOWER_COLOR,
  NW_DEFAULT_BANDWIDTH,
  NW_DEFAULT_MULT,
} from "../utils/nadarayaWatson";
import type { Candle, TradeMarker } from "../types";
import {
  formatBeijingDateTime,
  formatChartTime,
  formatChartTickMark,
} from "../utils/timezone";
import LiquidationZonePanel from "./liquidation/LiquidationZonePanel";
import {
  readSoundEnabled,
  writeSoundEnabled,
  signalSound,
} from "../utils/signalSound";

const CHART_OPTS = {
  layout: {
    background: { type: ColorType.Solid, color: "#131722" },
    textColor: "#d1d4dc",
  },
  grid: {
    vertLines: { color: "#2a2e39" },
    horzLines: { color: "#2a2e39" },
  },
  crosshair: { mode: CrosshairMode.Normal },
  rightPriceScale: { borderColor: "#2a2e39" },
  localization: {
    locale: "zh-CN",
    dateFormat: "yyyy-MM-dd",
    timeFormatter: formatChartTime,
  },
  timeScale: {
    borderColor: "#2a2e39",
    timeVisible: true,
    secondsVisible: false,
    tickMarkFormatter: formatChartTickMark,
  },
};

const EMA20_COLOR = "#2962ff";
const EMA50_COLOR = "#ff6d00";
const DEFAULT_BANDWIDTH = NW_DEFAULT_BANDWIDTH;
const DEFAULT_ALPHA = NW_DEFAULT_MULT;

type ChartBundle = {
  mainChart: IChartApi;
  rsiChart: IChartApi;
  macdChart: IChartApi;
  candleSeries: ISeriesApi<"Candlestick">;
  ema20Series: ISeriesApi<"Line">;
  ema50Series: ISeriesApi<"Line">;
  rsiSeries: ISeriesApi<"Line">;
  macdLine: ISeriesApi<"Line">;
  signalLine: ISeriesApi<"Line">;
  histSeries: ISeriesApi<"Histogram">;
  nwCenterSeries: ISeriesApi<"Line">;
  nwUpperSeries: ISeriesApi<"Line">;
  nwLowerSeries: ISeriesApi<"Line">;
};

function formatPrice(n: number) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatTime(ts: number) {
  return formatBeijingDateTime(ts, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const SYMBOLS: Symbol[] = ["BTCUSDT", "ETHUSDT"];
const INTERVALS: Interval[] = ["1m", "5m"];

const SEGMENT_BASE =
  "rounded border px-2 py-0.5 text-xs font-medium transition-colors";
const SEGMENT_ACTIVE =
  "border-tv-accent bg-tv-accent/20 text-tv-text";
const SEGMENT_INACTIVE =
  "border-tv-border bg-tv-panel text-tv-muted hover:border-tv-muted hover:text-tv-text";

function mergeMarkers(...groups: TradeMarker[][]): TradeMarker[] {
  return groups.flat().sort((a, b) => a.time - b.time);
}

function nwSignalKey(marker: TradeMarker): string {
  const side = marker.text === "Buy" ? "buy" : "sell";
  return `${marker.time}-${side}`;
}

/** Main + sub chart heights; clamped for readability across viewports. */
function getChartHeights() {
  if (typeof window === "undefined") {
    return { mainH: 520, subH: 120 };
  }
  const vh = window.innerHeight;
  const mainH = Math.min(560, Math.max(480, Math.round(vh * 0.42)));
  const subH = Math.min(130, Math.max(110, Math.round(vh * 0.1)));
  return { mainH, subH };
}

function applyChartData(
  bundle: ChartBundle,
  candles: Candle[],
  bandwidth: number,
  alpha: number
) {
  const closes = candles.map((c) => c.close);
  const ema20 = computeEMA(closes, 20);
  const ema50 = computeEMA(closes, 50);
  const rsi = computeRSI(closes, 14);
  const { macd, signal, histogram } = computeMACD(closes);
  const emaMarkers = computeEmaCrossMarkers(candles, ema20, ema50);

  const luxNw = computeLuxNadarayaWatson(candles, bandwidth, alpha);
  const { upper, lower } = computeNwEnvelopeBands(
    candles,
    luxNw.upper,
    luxNw.lower
  );
  const centerLine = nwToLineSeries(luxNw.nw);
  const nwMarkers = detectBuySellSignals(candles, luxNw.upper, luxNw.lower);
  const markers = mergeMarkers(emaMarkers, nwMarkers);

  bundle.candleSeries.setData(candles as CandlestickData[]);
  bundle.candleSeries.setMarkers(markers);
  bundle.ema20Series.setData(toLineSeries(candles, ema20));
  bundle.ema50Series.setData(toLineSeries(candles, ema50));
  bundle.rsiSeries.setData(toLineSeries(candles, rsi));
  bundle.macdLine.setData(toLineSeries(candles, macd));
  bundle.signalLine.setData(toLineSeries(candles, signal));
  bundle.histSeries.setData(toMacdHistogram(candles, histogram));

  bundle.nwCenterSeries.setData(centerLine.length >= 2 ? centerLine : []);
  bundle.nwUpperSeries.setData(upper.length >= 2 ? upper : []);
  bundle.nwLowerSeries.setData(lower.length >= 2 ? lower : []);
}

export default function TradingPanel() {
  const mainRef = useRef<HTMLDivElement>(null);
  const rsiRef = useRef<HTMLDivElement>(null);
  const macdRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);
  const bundleRef = useRef<ChartBundle | null>(null);

  const [symbol, setSymbol] = useState<Symbol>("BTCUSDT");
  const [interval, setInterval] = useState<Interval>("5m");
  const [bandwidth, setBandwidth] = useState(DEFAULT_BANDWIDTH);
  const [alpha, setAlpha] = useState(DEFAULT_ALPHA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [live, setLive] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(readSoundEnabled);

  const seenNwSignalsRef = useRef<Set<string>>(new Set());
  const nwSignalsSeededRef = useRef(false);

  const destroyCharts = useCallback(() => {
    chartsRef.current.forEach((c) => c.remove());
    chartsRef.current = [];
    bundleRef.current = null;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setCandles([]);
    setLive(false);

    (async () => {
      try {
        const data = await fetchKlines(symbol, interval);
        if (!cancelled) {
          setCandles(data);
          setLastPrice(data[data.length - 1]?.close ?? null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [symbol, interval]);

  useEffect(() => {
    seenNwSignalsRef.current = new Set();
    nwSignalsSeededRef.current = false;
  }, [symbol, interval]);

  const toggleSound = useCallback(async () => {
    if (!soundEnabled) {
      await signalSound.unlock();
      setSoundEnabled(true);
      writeSoundEnabled(true);
    } else {
      setSoundEnabled(false);
      writeSoundEnabled(false);
    }
  }, [soundEnabled]);

  const handleNwSignalAlerts = useCallback(
    (nwMarkers: TradeMarker[]) => {
      if (!nwSignalsSeededRef.current) {
        for (const m of nwMarkers) {
          seenNwSignalsRef.current.add(nwSignalKey(m));
        }
        nwSignalsSeededRef.current = true;
        return;
      }

      for (const m of nwMarkers) {
        const key = nwSignalKey(m);
        if (seenNwSignalsRef.current.has(key)) continue;
        seenNwSignalsRef.current.add(key);
        if (!soundEnabled) continue;
        if (m.text === "Buy") signalSound.playBuy();
        else signalSound.playSell();
      }
    },
    [soundEnabled]
  );

  const handleNwSignalAlertsRef = useRef(handleNwSignalAlerts);
  handleNwSignalAlertsRef.current = handleNwSignalAlerts;

  useEffect(() => {
    if (loading || error) return;

    const unsubscribe = subscribeKlineStream(symbol, interval, (candle) => {
      setLive(true);
      setLastPrice(candle.close);
      setCandles((prev) => applyKlineUpdate(prev, candle));
    });

    return unsubscribe;
  }, [symbol, interval, loading, error]);

  useEffect(() => {
    if (
      loading ||
      !candles.length ||
      !mainRef.current ||
      !rsiRef.current ||
      !macdRef.current
    ) {
      return;
    }

    destroyCharts();

    const { mainH, subH } = getChartHeights();

    const mainChart = createChart(mainRef.current, {
      ...CHART_OPTS,
      width: mainRef.current.clientWidth,
      height: mainH,
    });
    const rsiChart = createChart(rsiRef.current, {
      ...CHART_OPTS,
      width: rsiRef.current.clientWidth,
      height: subH,
    });
    const macdChart = createChart(macdRef.current, {
      ...CHART_OPTS,
      width: macdRef.current.clientWidth,
      height: subH,
    });

    chartsRef.current = [mainChart, rsiChart, macdChart];

    const candleSeries = mainChart.addCandlestickSeries({
      upColor: NW_UP_COLOR,
      downColor: NW_DOWN_COLOR,
      borderVisible: false,
      wickUpColor: NW_UP_COLOR,
      wickDownColor: NW_DOWN_COLOR,
    });

    const ema20Series = mainChart.addLineSeries({
      color: EMA20_COLOR,
      lineWidth: 2,
      title: "",
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const ema50Series = mainChart.addLineSeries({
      color: EMA50_COLOR,
      lineWidth: 2,
      title: "",
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const rsiSeries = rsiChart.addLineSeries({
      color: "#7e57c2",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    rsiSeries.createPriceLine({
      price: 70,
      color: NW_DOWN_COLOR,
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "70",
    });
    rsiSeries.createPriceLine({
      price: 30,
      color: NW_UP_COLOR,
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "30",
    });
    rsiChart.priceScale("right").applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.1 },
    });

    const macdLine = macdChart.addLineSeries({
      color: EMA20_COLOR,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const signalLine = macdChart.addLineSeries({
      color: EMA50_COLOR,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const histSeries = macdChart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });

    const nwUpperSeries = mainChart.addLineSeries({
      color: NW_ENVELOPE_UPPER_COLOR,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const nwLowerSeries = mainChart.addLineSeries({
      color: NW_ENVELOPE_LOWER_COLOR,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const nwCenterSeries = mainChart.addLineSeries({
      color: NW_CENTER_COLOR,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const bundle: ChartBundle = {
      mainChart,
      rsiChart,
      macdChart,
      candleSeries,
      ema20Series,
      ema50Series,
      rsiSeries,
      macdLine,
      signalLine,
      histSeries,
      nwCenterSeries,
      nwUpperSeries,
      nwLowerSeries,
    };
    bundleRef.current = bundle;
    const luxNw = computeLuxNadarayaWatson(candles, bandwidth, alpha);
    const nwMarkers = detectBuySellSignals(
      candles,
      luxNw.upper,
      luxNw.lower
    );
    handleNwSignalAlertsRef.current(nwMarkers);
    applyChartData(bundle, candles, bandwidth, alpha);

    mainChart.timeScale().fitContent();
    rsiChart.timeScale().fitContent();
    macdChart.timeScale().fitContent();

    const sync = (source: IChartApi, targets: IChartApi[]) => {
      source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (!range) return;
        targets.forEach((t) => t.timeScale().setVisibleLogicalRange(range));
      });
    };
    sync(mainChart, [rsiChart, macdChart]);
    sync(rsiChart, [mainChart, macdChart]);
    sync(macdChart, [mainChart, rsiChart]);

    const applyChartSize = () => {
      const { mainH: mh, subH: sh } = getChartHeights();
      if (mainRef.current) {
        mainChart.applyOptions({
          width: mainRef.current.clientWidth,
          height: mh,
        });
      }
      if (rsiRef.current) {
        rsiChart.applyOptions({
          width: rsiRef.current.clientWidth,
          height: sh,
        });
      }
      if (macdRef.current) {
        macdChart.applyOptions({
          width: macdRef.current.clientWidth,
          height: sh,
        });
      }
    };

    const ro = new ResizeObserver(applyChartSize);
    [mainRef, rsiRef, macdRef].forEach((r) => {
      if (r.current) ro.observe(r.current);
    });
    window.addEventListener("resize", applyChartSize);

    return () => {
      ro.disconnect();
      window.removeEventListener("resize", applyChartSize);
      destroyCharts();
    };
  }, [loading, symbol, interval, destroyCharts]);

  useEffect(() => {
    if (!bundleRef.current || !candles.length || loading) return;

    const luxNw = computeLuxNadarayaWatson(candles, bandwidth, alpha);
    const nwMarkers = detectBuySellSignals(
      candles,
      luxNw.upper,
      luxNw.lower
    );
    handleNwSignalAlerts(nwMarkers);
    applyChartData(bundleRef.current, candles, bandwidth, alpha);
  }, [candles, loading, bandwidth, alpha, handleNwSignalAlerts]);

  const first = candles[0];
  const last = candles[candles.length - 1];

  return (
    <div className="flex min-h-0 w-full flex-col bg-tv-bg text-tv-text">
      <div className="sticky top-0 z-30 shrink-0 bg-tv-bg">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-tv-border px-4 py-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">
              {symbolLabel(symbol)}
            </h1>
            {live && (
              <span className="flex items-center gap-1 rounded bg-tv-up/15 px-2 py-0.5 text-xs font-medium text-tv-up">
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-tv-up" />
                实时
              </span>
            )}
            <span className="text-xs text-tv-muted">Binance 现货</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <button
              type="button"
              aria-pressed={soundEnabled}
              aria-label={
                soundEnabled ? "关闭 NW 买卖声音提醒" : "开启 NW 买卖声音提醒"
              }
              title={
                soundEnabled
                  ? "NW Buy/Sell 新信号时播放提示音"
                  : "点击开启提示音（需用户手势解锁浏览器音频）"
              }
              onClick={() => void toggleSound()}
              className={`${SEGMENT_BASE} shrink-0 ${
                soundEnabled ? SEGMENT_ACTIVE : SEGMENT_INACTIVE
              }`}
            >
              {soundEnabled ? "声音开" : "声音关"}
            </button>
            {lastPrice != null && (
              <span className="font-mono text-base font-semibold tabular-nums">
                {formatPrice(lastPrice)}
              </span>
            )}
            {first && last && (
              <span className="text-xs text-tv-muted">
                {formatTime(first.time)} → {formatTime(last.time)}
              </span>
            )}
          </div>
        </header>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-tv-border px-4 py-1.5 text-xs text-tv-muted">
        <div className="flex items-center gap-1" role="group" aria-label="交易对">
          {SYMBOLS.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={symbol === s}
              onClick={() => setSymbol(s)}
              className={`${SEGMENT_BASE} ${symbol === s ? SEGMENT_ACTIVE : SEGMENT_INACTIVE}`}
            >
              {symbolLabel(s)}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1" role="group" aria-label="K 线周期">
          {INTERVALS.map((iv) => (
            <button
              key={iv}
              type="button"
              aria-pressed={interval === iv}
              onClick={() => setInterval(iv)}
              className={`${SEGMENT_BASE} ${interval === iv ? SEGMENT_ACTIVE : SEGMENT_INACTIVE}`}
            >
              {iv}
            </button>
          ))}
        </div>
        <span className="h-3 w-px bg-tv-border" />
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-0.5 w-4"
            style={{ backgroundColor: EMA20_COLOR }}
          />
          EMA 20
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-0.5 w-4"
            style={{ backgroundColor: EMA50_COLOR }}
          />
          EMA 50
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-0.5 w-4"
            style={{ backgroundColor: NW_CENTER_COLOR }}
          />
          NW 中线
        </span>
        <span className="text-tv-muted">（LuxAlgo Gaussian + MAE 包络）</span>
        <span className="h-3 w-px bg-tv-border" />
        <span style={{ color: "#10b981" }}>▲ EB</span>
        <span style={{ color: "#ef4444" }}>▼ ES</span>
        <span className="text-tv-muted">（EMA 金叉/死叉）</span>
        <span style={{ color: NW_BUY_MARKER_COLOR }}>▲ Buy</span>
        <span style={{ color: NW_SELL_MARKER_COLOR }}>▼ Sell</span>
        <span className="text-tv-muted">（LuxAlgo：下穿下轨买 / 上穿上轨卖）</span>
        <span className="h-3 w-px bg-tv-border" />
        <label className="flex items-center gap-1.5">
          <span>Bandwidth</span>
          <input
            type="range"
            min={2}
            max={50}
            step={1}
            value={bandwidth}
            onChange={(e) => setBandwidth(Number(e.target.value))}
            className="w-20 accent-tv-accent"
          />
          <span className="font-mono tabular-nums text-tv-text">{bandwidth}</span>
        </label>
        <label className="flex items-center gap-1.5">
          <span>Alpha</span>
          <input
            type="range"
            min={0.5}
            max={10}
            step={0.5}
            value={alpha}
            onChange={(e) => setAlpha(Number(e.target.value))}
            className="w-20 accent-tv-accent"
          />
          <span className="font-mono tabular-nums text-tv-text">
            {alpha.toFixed(1)}
          </span>
        </label>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-24 text-sm text-tv-muted">
          正在从 Binance 加载 {interval} K 线…
        </div>
      )}

      {error && (
        <div className="mx-4 my-3 rounded border border-tv-down/40 bg-tv-down/10 px-3 py-2 text-sm text-tv-down">
          {error}
        </div>
      )}

      {!loading && !error && candles.length > 0 && (
        <div className="flex w-full flex-col scroll-mt-28">
          <div className="flex w-full shrink-0 flex-col gap-1 px-2 pb-2 pt-2">
            <div className="shrink-0">
              <div className="px-1 pb-1 text-xs font-medium text-tv-muted">
                主图 · K 线 + EMA + NW
              </div>
              <div ref={mainRef} className="w-full" />
            </div>
            <div className="shrink-0">
              <div className="px-1 pb-1 text-xs font-medium text-tv-muted">
                RSI (14)
              </div>
              <div ref={rsiRef} className="w-full" />
            </div>
            <div className="shrink-0">
              <div className="px-1 pb-1 text-xs font-medium text-tv-muted">
                MACD (12, 26, 9)
              </div>
              <div ref={macdRef} className="w-full" />
            </div>
          </div>
          <LiquidationZonePanel symbol={symbol} marketPrice={lastPrice} />
        </div>
      )}

      <footer className="border-t border-tv-border px-4 py-1.5 text-right text-[10px] text-tv-muted">
        {interval} · Binance REST + WebSocket · EMA/RSI/MACD/NW 浏览器端计算 ·
        Lightweight Charts
      </footer>
    </div>
  );
}
