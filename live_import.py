"""Load OKX position history export (UTF-8, skip metadata row)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_LIVE_CSV = Path(__file__).resolve().parent / "live_okx_20260501.csv"
CUTOFF = pd.Timestamp("2026-05-01 00:00:00")


def load_okx_positions(
    path: Path | str = DEFAULT_LIVE_CSV,
    *,
    since: pd.Timestamp | None = CUTOFF,
    by: str = "close",
) -> pd.DataFrame:
    """Parse OKX 持仓历史 CSV. `by` is ``close`` (仓位更新时间) or ``open``."""
    path = Path(path)
    peek = pd.read_csv(path, encoding="utf-8-sig", nrows=1)
    first_col = str(peek.columns[0]).lstrip("\ufeff")
    skip = 0 if first_col.startswith("仓位创建时间") else 1
    df = pd.read_csv(path, encoding="utf-8-sig", skiprows=skip)
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]

    for col in ("仓位创建时间", "仓位更新时间"):
        df[col] = pd.to_datetime(
            df[col].astype(str).str.replace("\ufeff", "", regex=False),
            errors="coerce",
        )

    numeric = (
        "最大持仓量",
        "开仓均价",
        "平仓均价",
        "收益额",
        "收益率",
        "累计手续费",
        "累计资金费用",
        "合约面值",
        "杠杆倍数",
    )
    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if since is not None:
        time_col = "仓位更新时间" if by == "close" else "仓位创建时间"
        df = df[df[time_col] >= since].copy()

    df["eth_size"] = df["最大持仓量"] * df["合约面值"]
    df["net_pnl"] = df["收益额"] + df["累计手续费"] + df["累计资金费用"]
    return df


def summarize_live(df: pd.DataFrame, account_usdt: float = 3000.0) -> dict:
    net = float(df["net_pnl"].sum())
    return {
        "positions": len(df),
        "gross_pnl": round(float(df["收益额"].sum()), 2),
        "fees": round(float(df["累计手续费"].sum()), 2),
        "funding": round(float(df["累计资金费用"].sum()), 2),
        "net_pnl": round(net, 2),
        "return_pct": round(net / account_usdt * 100, 2),
        "long": int((df["持仓方向"] == "做多").sum()),
        "short": int((df["持仓方向"] == "做空").sum()),
    }
