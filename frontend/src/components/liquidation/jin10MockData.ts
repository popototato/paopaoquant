import { createRngForSeedKey, stableSeedKey } from "./mockData";
import type { Jin10NewsItem } from "./types";

const FLASH_TEMPLATES: Array<{
  category: Jin10NewsItem["category"];
  importance: Jin10NewsItem["importance"];
  titles: string[];
  symbolTag?: "BTC" | "ETH";
}> = [
  {
    category: "币圈",
    importance: "important",
    symbolTag: "BTC",
    titles: [
      "比特币短线拉升逾1.2%，现货 ETF 单日净流入创近两周新高",
      "某大型交易所 BTC 永续资金费率转负，多头去杠杆迹象明显",
      "链上数据显示巨鲸地址近 6 小时向交易所转入约 2800 枚 BTC",
    ],
  },
  {
    category: "币圈",
    importance: "normal",
    symbolTag: "ETH",
    titles: [
      "以太坊 L2 总锁仓量突破前高，Gas 费维持低位",
      "ETH 质押队列退出等待时间缩短至约 4 天",
    ],
  },
  {
    category: "特朗普",
    importance: "important",
    titles: [
      "特朗普：将对部分进口商品加征关税，市场避险情绪升温",
      "特朗普在竞选集会上重申将推动美国能源独立政策",
      "白宫官员：特朗普团队正评估新一轮对华贸易条款",
    ],
  },
  {
    category: "宏观",
    importance: "important",
    titles: [
      "美国 4 月核心 PCE 同比 2.8%，略高于市场预期",
      "美联储官员：仍需更多数据才能确认通胀回落趋势",
      "欧元区 5 月制造业 PMI 初值 47.2，连续第三个月萎缩",
    ],
  },
  {
    category: "外汇",
    importance: "normal",
    titles: [
      "美元指数 DXY 短线拉升 0.35%，非美货币普遍承压",
      "日本央行官员：将继续密切关注日元过度波动风险",
    ],
  },
  {
    category: "原油",
    importance: "normal",
    titles: [
      "WTI 原油日内涨逾 1.5%，中东地缘紧张推升风险溢价",
      "EIA 周报：美国商业原油库存降幅超预期",
    ],
  },
  {
    category: "股市",
    importance: "normal",
    titles: [
      "纳指期货盘前涨 0.4%，科技股财报季情绪偏暖",
      "A50 期指夜盘小幅走高，亚太风险偏好回升",
    ],
  },
];

function formatFlashTime(offsetMinutes: number): string {
  const d = new Date(Date.now() - offsetMinutes * 60_000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

function pick<T>(rng: () => number, arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)]!;
}

export function createMockJin10News(
  symbol: string,
  marketPrice: number,
  count = 14
): Jin10NewsItem[] {
  const seedKey = `jin10:${stableSeedKey(symbol, marketPrice)}`;
  const rng = createRngForSeedKey(seedKey);
  const sym = symbol.includes("ETH") ? "ETH" : "BTC";
  const items: Jin10NewsItem[] = [];
  const itemCount = Math.max(8, Math.min(count, 20));

  for (let i = 0; i < itemCount; i++) {
    const tpl = pick(rng, FLASH_TEMPLATES);
    const title = pick(rng, tpl.titles);
    const tag =
      tpl.symbolTag ??
      (tpl.category === "币圈" && rng() > 0.45 ? sym : undefined);

    items.push({
      id: `${seedKey}:${i}`,
      time: formatFlashTime(3 + Math.floor(rng() * 180)),
      title,
      category: tpl.category,
      importance: tpl.importance,
      symbolTag: tag,
    });
  }

  const sorted = items.sort((a, b) => a.time.localeCompare(b.time)).reverse();
  return sorted.length > 0 ? sorted : buildFallbackMockNews(sym, seedKey);
}

function buildFallbackMockNews(
  sym: "BTC" | "ETH",
  seedKey: string
): Jin10NewsItem[] {
  return [
    {
      id: `${seedKey}:fallback-0`,
      time: formatFlashTime(2),
      title: "Mock 示例：数据加载失败时的占位条目，便于预览列表布局",
      category: "宏观",
      importance: "normal",
    },
    {
      id: `${seedKey}:fallback-1`,
      time: formatFlashTime(6),
      title: `Mock 示例：${sym} 相关示例快讯，刷新后将更新时间戳`,
      category: "币圈",
      importance: "important",
      symbolTag: sym,
    },
  ];
}

/** Re-stamp times relative to now (manual refresh). */
export function refreshJin10Timestamps(items: Jin10NewsItem[]): Jin10NewsItem[] {
  return items.map((item, i) => ({
    ...item,
    time: formatFlashTime(2 + i * 4 + Math.floor((i * 7) % 11)),
  }));
}
