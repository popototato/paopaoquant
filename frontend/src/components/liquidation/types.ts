export type LiquidationSide = "LONG" | "SHORT";

export type PressureState =
  | "neutral"
  | "high_long_risk"
  | "high_short_risk";

export interface HeatmapLevel {
  price: number;
  longIntensity: number;
  shortIntensity: number;
}

export interface MajorLevel {
  id: string;
  side: LiquidationSide;
  label: string;
  price: number;
  sizeUsd: number;
  distancePct: number;
}

export interface LiquidationFeedItem {
  id: string;
  time: string;
  side: LiquidationSide;
  amountUsd: number;
  price: number;
}

export interface AiInsight {
  id: string;
  text: string;
  severity: "info" | "warn" | "critical";
}

export interface LiquidationData {
  symbol: string;
  /** Aggregation window in hours (fixed 12h snapshot) */
  windowHours: number;
  marketPrice: number;
  updatedAt: number;
  heatmap: HeatmapLevel[];
  majorLevels: MajorLevel[];
  pressure: {
    state: PressureState;
    score: number;
    longBias: number;
    shortBias: number;
  };
}

export type LiquidationDataSource = {
  subscribe: (
    symbol: string,
    onData: (data: LiquidationData) => void
  ) => () => void;
};

export type Jin10NewsCategory =
  | "币圈"
  | "特朗普"
  | "宏观"
  | "外汇"
  | "原油"
  | "股市";

export type Jin10Importance = "normal" | "important";

export interface Jin10NewsItem {
  id: string;
  time: string;
  title: string;
  category: Jin10NewsCategory;
  importance: Jin10Importance;
  /** Optional BTC/ETH tag for crypto-related flashes */
  symbolTag?: "BTC" | "ETH";
}

export type Jin10DataSource = "live" | "mock";
