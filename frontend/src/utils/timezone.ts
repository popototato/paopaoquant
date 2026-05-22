import { TickMarkType, type Time } from "lightweight-charts";

/** Binance K 线时间为 UTC 秒；轴标签按北京时间展示 */
export const BEIJING_TZ = "Asia/Shanghai";

function utcSecondsToDate(ts: number): Date {
  return new Date(ts * 1000);
}

function timeToUtcSeconds(time: Time): number {
  if (typeof time === "number") return time;
  if (typeof time === "string") {
    const d = new Date(time);
    return Math.floor(d.getTime() / 1000);
  }
  const { year, month, day } = time;
  return Math.floor(Date.UTC(year, month - 1, day) / 1000);
}

export function formatBeijingDateTime(
  ts: number,
  options?: Intl.DateTimeFormatOptions
): string {
  return utcSecondsToDate(ts).toLocaleString("zh-CN", {
    timeZone: BEIJING_TZ,
    hour12: false,
    ...options,
  });
}

/** 十字线 / 时间轴悬停标签 */
export function formatChartTime(time: Time): string {
  return formatBeijingDateTime(timeToUtcSeconds(time), {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** 时间轴刻度（≤8 字符，避免重叠） */
export function formatChartTickMark(
  time: Time,
  tickMarkType: TickMarkType,
  _locale: string
): string | null {
  const d = utcSecondsToDate(timeToUtcSeconds(time));
  const fmt = (opts: Intl.DateTimeFormatOptions) =>
    d.toLocaleString("zh-CN", {
      timeZone: BEIJING_TZ,
      hour12: false,
      ...opts,
    });

  switch (tickMarkType) {
    case TickMarkType.Year:
      return fmt({ year: "2-digit" });
    case TickMarkType.Month:
      return fmt({ month: "short" });
    case TickMarkType.DayOfMonth:
      return fmt({ month: "numeric", day: "numeric" });
    case TickMarkType.Time:
      return fmt({ hour: "2-digit", minute: "2-digit" });
    case TickMarkType.TimeWithSeconds:
      return fmt({ hour: "2-digit", minute: "2-digit", second: "2-digit" });
    default:
      return formatChartTime(time);
  }
}
