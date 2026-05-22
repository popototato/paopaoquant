import pandas as pd

STEP_COLUMNS = ["第几步", "补仓间距", "每层仓位", "止盈距离"]
HEADER_KEYWORDS = ("步", "间距", "仓位", "止盈", "step", "spacing", "position")


def _detect_separator(line: str) -> str:
    if "\t" in line:
        return "\t"
    if "," in line:
        return ","
    if ";" in line:
        return ";"
    raise ValueError("无法识别分隔符，请使用 Tab、逗号或分号分隔。")


def _is_header(cols: list[str]) -> bool:
    joined = "".join(cols).lower()
    return any(keyword in joined for keyword in HEADER_KEYWORDS)


def _row_to_record(cols: list[str]) -> dict:
    if len(cols) < 4:
        raise ValueError(f"列数不足 4 列：{cols}")
    return {
        "第几步": int(float(cols[0])),
        "补仓间距": float(cols[1]),
        "每层仓位": round(float(cols[2]), 4),
        "止盈距离": float(cols[3]),
    }


def parse_steps_text(text: str) -> pd.DataFrame:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("粘贴内容为空。")

    sep = _detect_separator(lines[0])
    start_idx = 1 if _is_header(lines[0].split(sep)) else 0

    records = []
    for line in lines[start_idx:]:
        cols = [col.strip() for col in line.split(sep) if col.strip() != ""]
        if not cols:
            continue
        records.append(_row_to_record(cols))

    if not records:
        raise ValueError("没有解析到有效数据行，请检查格式。")

    return pd.DataFrame(records, columns=STEP_COLUMNS)


def parse_steps_csv_file(uploaded_file) -> pd.DataFrame:
    content = uploaded_file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("gbk")
    return parse_steps_text(text)


def empty_steps_df() -> pd.DataFrame:
    return pd.DataFrame(columns=STEP_COLUMNS)


def has_valid_steps(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    cleaned = df.dropna(how="all")
    if cleaned.empty:
        return False
    return cleaned[STEP_COLUMNS].notna().all(axis=1).any()


def valid_steps_rows(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.dropna(how="all")
    return cleaned.dropna(subset=STEP_COLUMNS, how="any")


def default_steps_df() -> pd.DataFrame:
    # 每层仓位 ×0.85：与 OKX 实盘一致（0.1 ETH 模型单位 ≈ 0.085 ETH 实盘）
    return pd.DataFrame(
        {
            "第几步": list(range(1, 26)),
            "补仓间距": [
                0, 20, 10, 10, 6, 7, 8, 8, 8, 7, 6, 7, 8, 8, 8, 7, 6, 7, 8, 8, 10, 10, 10, 10, 29
            ],
            "每层仓位": [
                0.085, 0.085, 0.085, 0.085, 0.085, 0.085, 0.085, 0.17, 0.1955, 0.238, 0.2975,
                0.374, 0.4675, 0.6545, 0.8415, 1.0795, 1.377, 1.7595, 2.2525, 2.89, 3.6975,
                4.7345, 6.052, 7.752, 0.085,
            ],
            "止盈距离": [
                25, 15, 15, 10, 8, 7, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5
            ],
        }
    )
