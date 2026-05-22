import csv
import time
from datetime import date, datetime, time as dt_time, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import requests

BINANCE_KLINES_URLS = (
    "https://api.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
)
_BINANCE_GEO_BLOCK_CODES = frozenset({403, 451})
KLINE_INTERVAL = "1m"
ETH_CSV_PATH = Path(__file__).parent / "eth.csv"
_csv_info_cache: dict | None = None
_csv_info_cache_key: tuple[int, int] | None = None
MAX_LIMIT = 1000
ONE_MIN_MS = 60 * 1000
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
TIMEZONE_LABEL = "北京时间 (UTC+8)"
ETH_LISTING_MS = int(datetime(2017, 8, 17, 4, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
# 近 5 年 1 分钟线
FIVE_YEARS_MS = 5 * 365 * 24 * 60 * 60 * 1000

ProgressCallback = Callable[[int, int], None]


def format_ms_beijing(ms: int) -> str:
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(BEIJING_TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def beijing_str_to_ms(dt_str: str) -> int:
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BEIJING_TZ)
    return int(dt.timestamp() * 1000)


def five_years_start_ms(now_ms: int | None = None) -> int:
    now_ms = now_ms or int(datetime.now(timezone.utc).timestamp() * 1000)
    return max(ETH_LISTING_MS, now_ms - FIVE_YEARS_MS)


def _ms_to_row(open_ms: int, item: list) -> list:
    return [
        format_ms_beijing(open_ms),
        float(item[1]),
        float(item[2]),
        float(item[3]),
        float(item[4]),
        float(item[5]),
    ]


def _detect_interval_label(csv_path: Path) -> str:
    """根据相邻两根 K 线时间差判断周期。"""
    with csv_path.open(encoding="utf-8") as file:
        file.readline()
        first = file.readline()
        second = file.readline()
    if not first or not second:
        return KLINE_INTERVAL
    t0 = beijing_str_to_ms(first.split(",")[0])
    t1 = beijing_str_to_ms(second.split(",")[0])
    delta = (t1 - t0) // 1000
    if delta <= 60:
        return "1m"
    if delta <= 300:
        return "5m"
    return f"{delta}s"


def _get_last_datetime(csv_path: Path) -> str | None:
    """只读最后一行时间，避免加载整个大文件。"""
    if not csv_path.exists() or csv_path.stat().st_size < 20:
        return None
    with csv_path.open("rb") as file:
        file.seek(0, 2)
        pos = file.tell() - 1
        buf = b""
        while pos >= 0:
            file.seek(pos)
            ch = file.read(1)
            if ch == b"\n":
                if buf:
                    line = buf[::-1].decode("utf-8", errors="ignore").strip()
                    if line and not line.startswith("datetime"):
                        return line.split(",")[0]
                    buf = b""
            else:
                buf += ch
            pos -= 1
    return None


def _read_existing_rows(csv_path: Path) -> dict[str, list]:
    if not csv_path.exists():
        return {}
    rows: dict[str, list] = {}
    with csv_path.open(encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows[row["datetime"]] = [
                row["datetime"],
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            ]
    return rows


def _write_rows(rows: dict[str, list], csv_path: Path) -> None:
    sorted_rows = [rows[key] for key in sorted(rows.keys())]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["datetime", "open", "high", "low", "close", "volume"])
        writer.writerows(sorted_rows)


def _remove_legacy_files() -> None:
    legacy = Path(__file__).parent / "eth_1m.csv"
    if legacy.exists():
        legacy.unlink()


class BinanceKlinesError(Exception):
    """Binance K 线接口全部不可用。"""


def _request_klines(
    session: requests.Session,
    params: dict,
    url_index: int = 0,
) -> tuple[requests.Response, int]:
    """依次尝试主站与 data-api；451/403 时切换备用端点。"""
    last_status: int | None = None
    for idx in range(url_index, len(BINANCE_KLINES_URLS)):
        response = session.get(BINANCE_KLINES_URLS[idx], params=params, timeout=30)
        if response.status_code == 429:
            return response, idx
        if response.status_code in _BINANCE_GEO_BLOCK_CODES:
            last_status = response.status_code
            continue
        if response.ok:
            return response, idx
        response.raise_for_status()
    raise BinanceKlinesError(
        "无法从 Binance 拉取 K 线数据：主站与 data-api.binance.vision 均不可用"
        + (f"（最近 HTTP {last_status}，常见于 Streamlit Cloud 等地区限制）" if last_status else "")
        + "。请稍后重试，或在本地网络下载 eth.csv 后上传。"
    )


def _fetch_klines_since(
    start_ms: int,
    progress_callback: ProgressCallback | None = None,
    base_count: int = 0,
) -> dict[str, list]:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    current = start_ms
    fetched: dict[str, list] = {}
    session = requests.Session()
    url_index = 0
    params_base = {
        "symbol": "ETHUSDT",
        "interval": KLINE_INTERVAL,
        "limit": MAX_LIMIT,
    }

    while current < now_ms:
        params = {**params_base, "startTime": current}
        try:
            response, url_index = _request_klines(session, params, url_index)
        except BinanceKlinesError:
            raise
        if response.status_code == 429:
            time.sleep(1.5)
            continue
        batch = response.json()
        if not batch:
            break

        for item in batch:
            row = _ms_to_row(item[0], item)
            fetched[row[0]] = row

        current = batch[-1][0] + ONE_MIN_MS
        if progress_callback:
            progress_callback(base_count + len(fetched), current)
        if len(batch) < MAX_LIMIT:
            break
        time.sleep(0.05)

    return fetched


def update_eth_data(
    progress_callback: ProgressCallback | None = None,
    force_full: bool = False,
) -> dict:
    """
    更新 eth.csv（Binance ETH/USDT 1 分钟线，北京时间）。
    force_full=True：删除旧数据，从近 5 年起全量重下并覆盖。
    """
    _remove_legacy_files()
    csv_path = ETH_CSV_PATH
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    default_start = five_years_start_ms(now_ms)

    if force_full:
        if csv_path.exists():
            csv_path.unlink()
        existing: dict[str, list] = {}
        start_ms = default_start
    else:
        last_dt = _get_last_datetime(csv_path)
        if last_dt:
            start_ms = beijing_str_to_ms(last_dt) + ONE_MIN_MS
            existing = {}  # 增量只追加，不重读全文件
        else:
            existing = {}
            start_ms = default_start

    if not force_full and start_ms >= now_ms:
        rows = _read_existing_rows(csv_path)
        return _build_meta(rows if rows else existing)

    base_count = 0
    if not force_full and csv_path.exists():
        with csv_path.open(encoding="utf-8") as file:
            base_count = sum(1 for _ in file) - 1

    new_rows = _fetch_klines_since(start_ms, progress_callback=progress_callback, base_count=base_count)

    if force_full:
        _write_rows(new_rows, csv_path)
    else:
        write_header = not csv_path.exists() or csv_path.stat().st_size == 0
        with csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["datetime", "open", "high", "low", "close", "volume"])
            for key in sorted(new_rows.keys()):
                writer.writerow(new_rows[key])
        return get_csv_info() or _build_meta(new_rows)

    return _build_meta(new_rows)


def _count_csv_rows(csv_path: Path) -> int:
    with csv_path.open("rb") as file:
        return max(0, sum(1 for _ in file) - 1)


def get_csv_info() -> dict | None:
    global _csv_info_cache, _csv_info_cache_key
    if not ETH_CSV_PATH.exists():
        _csv_info_cache = None
        _csv_info_cache_key = None
        return None

    stat = ETH_CSV_PATH.stat()
    cache_key = (stat.st_mtime_ns, stat.st_size)
    if _csv_info_cache_key == cache_key and _csv_info_cache is not None:
        return _csv_info_cache

    last_dt = _get_last_datetime(ETH_CSV_PATH)
    if not last_dt:
        return None

    first_dt = None
    with ETH_CSV_PATH.open(encoding="utf-8") as file:
        file.readline()
        first_line = file.readline().strip()
        if first_line:
            first_dt = first_line.split(",")[0]

    if not first_dt:
        return None

    interval = _detect_interval_label(ETH_CSV_PATH)
    count = _count_csv_rows(ETH_CSV_PATH)
    updated_at = datetime.fromtimestamp(stat.st_mtime, tz=BEIJING_TZ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    start_date = datetime.strptime(first_dt, "%Y-%m-%d %H:%M:%S").date()
    end_date = datetime.strptime(last_dt, "%Y-%m-%d %H:%M:%S").date()
    _csv_info_cache = {
        "path": str(ETH_CSV_PATH.resolve()),
        "interval": interval,
        "count": count,
        "start": first_dt,
        "end": last_dt,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": TIMEZONE_LABEL,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 1),
        "updated_at": updated_at,
    }
    _csv_info_cache_key = cache_key
    return _csv_info_cache


def _build_meta(rows: dict[str, list]) -> dict:
    if not rows:
        return {
            "path": str(ETH_CSV_PATH),
            "interval": "1m",
            "count": 0,
            "start": None,
            "end": None,
            "start_date": None,
            "end_date": None,
        }
    keys = sorted(rows.keys())
    start = keys[0]
    end = keys[-1]
    return {
        "path": str(ETH_CSV_PATH),
        "interval": "1m",
        "count": len(rows),
        "start": start,
        "end": end,
        "start_date": datetime.strptime(start, "%Y-%m-%d %H:%M:%S").date(),
        "end_date": datetime.strptime(end, "%Y-%m-%d %H:%M:%S").date(),
        "timezone": TIMEZONE_LABEL,
    }


def parse_date(value: date | datetime | str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def to_backtrader_datetime(value: date, end_of_day: bool = False) -> datetime:
    if end_of_day:
        return datetime.combine(value, dt_time(23, 59, 59))
    return datetime.combine(value, dt_time.min)
