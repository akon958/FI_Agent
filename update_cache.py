from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable


CACHE_FILE = Path(__file__).with_name("stock_metrics.csv")
pd: Any = None

CACHE_COLUMNS = [
    "代码",
    "名称",
    "最新价",
    "涨跌幅",
    "成交额",
    "市盈率-动态",
    "市净率",
    "换手率",
    "总市值",
    "流通市值",
    "所属行业",
    "量比",
    "振幅",
    "内外盘比例",
    "ROE",
    "净利率",
    "毛利率",
    "营收增长率",
    "净利润增长率",
    "资产负债率",
    "经营现金流/净利润",
    "数据来源",
    "更新时间",
]

FINANCIAL_COLUMNS = [
    "ROE",
    "净利率",
    "毛利率",
    "营收增长率",
    "净利润增长率",
    "资产负债率",
    "经营现金流/净利润",
]

COLUMN_ALIASES = {
    "代码": ["代码", "股票代码", "证券代码", "symbol", "代码代码"],
    "名称": ["名称", "股票名称", "证券简称", "简称", "name"],
    "最新价": ["最新价", "最新价格", "最新收盘价", "收盘", "现价", "trade", "price"],
    "涨跌幅": ["涨跌幅", "涨跌幅%", "涨幅", "changepercent", "pct_chg"],
    "成交额": ["成交额", "成交金额", "amount"],
    "市盈率-动态": ["市盈率-动态", "市盈率动态", "动态市盈率", "市盈率", "pe", "pe_ttm"],
    "市净率": ["市净率", "pb"],
    "换手率": ["换手率", "换手率%", "turnover", "turnoverrate"],
    "总市值": ["总市值", "market_cap", "总市值(元)"],
    "流通市值": ["流通市值", "circulating_market_cap", "流通市值(元)"],
    "量比": ["量比"],
    "振幅": ["振幅", "振幅%", "amplitude"],
}


def normalize_code(code: Any) -> str:
    text = str(code or "").strip().upper()
    if text.startswith(("SH", "SZ", "BJ")):
        text = text[2:]
    return text.zfill(6) if text else ""


def to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "--", "None", "nan"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def first_present(row: Any, names: list[str]) -> Any:
    for name in names:
        if name in row and row[name] is not None and not pd.isna(row[name]):
            return row[name]
    return None


def is_valid_frame(df: Any) -> bool:
    return df is not None and hasattr(df, "empty") and not df.empty


def read_existing_cache() -> Any:
    if not CACHE_FILE.exists():
        return pd.DataFrame(columns=CACHE_COLUMNS)

    try:
        df = pd.read_csv(CACHE_FILE, dtype={"代码": str, "股票代码": str})
    except Exception as exc:  # noqa: BLE001
        print(f"读取旧缓存失败，将重新生成缓存。原因：{exc}", flush=True)
        return pd.DataFrame(columns=CACHE_COLUMNS)

    if "代码" not in df.columns and "股票代码" in df.columns:
        df["代码"] = df["股票代码"]

    for column in CACHE_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df["代码"] = df["代码"].map(normalize_code)
    return df[df["代码"] != ""].drop_duplicates(subset=["代码"], keep="last")


def fetch_market(
    market_name: str,
    fetcher: Callable[[], Any],
    success_label: str | None = None,
) -> Any | None:
    try:
        df = fetcher()
    except Exception as exc:  # noqa: BLE001
        print(f"{market_name} 获取失败，原因：{exc}", flush=True)
        return None

    if not is_valid_frame(df):
        print(f"{market_name} 获取失败：返回数据为空。", flush=True)
        return None

    label = success_label or market_name
    print(f"{label} 获取成功，共 {len(df)} 条", flush=True)
    return df


def fetch_spot_data(ak: Any) -> Any | None:
    print("正在尝试获取沪深京 A 股全市场数据...", flush=True)
    spot_df = fetch_market("全市场接口", ak.stock_zh_a_spot_em, "全市场接口")
    if is_valid_frame(spot_df):
        return spot_df

    print("全市场接口失败，开始分市场获取...", flush=True)
    market_frames = []
    market_fetchers = [
        ("沪 A", ak.stock_sh_a_spot_em),
        ("深 A", ak.stock_sz_a_spot_em),
        ("京 A", ak.stock_bj_a_spot_em),
    ]
    for market_name, fetcher in market_fetchers:
        print(f"正在获取{market_name}数据...", flush=True)
        market_df = fetch_market(market_name, fetcher)
        if is_valid_frame(market_df):
            market_frames.append(market_df)

    if market_frames:
        combined = pd.concat(market_frames, ignore_index=True, sort=False)
        print(f"分市场数据合并完成，共 {len(combined)} 条原始数据。", flush=True)
        return combined

    print("东财接口全部失败，开始尝试备用接口 ak.stock_zh_a_spot()...", flush=True)
    backup_df = fetch_market("备用接口 ak.stock_zh_a_spot()", ak.stock_zh_a_spot, "备用接口")
    if is_valid_frame(backup_df):
        return backup_df

    print("更新失败：所有行情接口都未获取到有效数据，没有覆盖 stock_metrics.csv。", flush=True)
    return None


def normalize_spot_frame(spot_df: Any) -> Any:
    df = spot_df.copy()
    code_source = None
    for column in COLUMN_ALIASES["代码"]:
        if column in df.columns:
            code_source = column
            break

    if code_source is None:
        print(f"更新失败：行情结果中没有可识别的代码字段。实际字段：{list(df.columns)}", flush=True)
        return pd.DataFrame(columns=list(df.columns) + ["代码"])

    df["代码"] = df[code_source].map(normalize_code)
    df = df[df["代码"] != ""].drop_duplicates(subset=["代码"], keep="last")
    return df


def build_cache_rows(spot_df: Any, old_cache: Any) -> Any:
    old_by_code = old_cache.set_index("代码", drop=False).to_dict("index") if not old_cache.empty else {}
    rows: list[dict[str, Any]] = []
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, spot_row in spot_df.iterrows():
        code = normalize_code(first_present(spot_row, COLUMN_ALIASES["代码"]))
        if not code:
            continue

        old_row = old_by_code.get(code, {})
        row = {column: old_row.get(column) for column in CACHE_COLUMNS}
        row["代码"] = code
        row["名称"] = first_present(spot_row, COLUMN_ALIASES["名称"]) or old_row.get("名称") or code
        row["最新价"] = to_float(first_present(spot_row, COLUMN_ALIASES["最新价"]))
        row["涨跌幅"] = to_float(first_present(spot_row, COLUMN_ALIASES["涨跌幅"]))
        row["成交额"] = to_float(first_present(spot_row, COLUMN_ALIASES["成交额"]))
        row["市盈率-动态"] = to_float(first_present(spot_row, COLUMN_ALIASES["市盈率-动态"]))
        row["市净率"] = to_float(first_present(spot_row, COLUMN_ALIASES["市净率"]))
        row["换手率"] = to_float(first_present(spot_row, COLUMN_ALIASES["换手率"]))
        row["总市值"] = to_float(first_present(spot_row, COLUMN_ALIASES["总市值"]))
        row["流通市值"] = to_float(first_present(spot_row, COLUMN_ALIASES["流通市值"]))
        row["量比"] = to_float(first_present(spot_row, COLUMN_ALIASES["量比"]))
        row["振幅"] = to_float(first_present(spot_row, COLUMN_ALIASES["振幅"]))
        row["所属行业"] = old_row.get("所属行业") or "未知"
        row["内外盘比例"] = old_row.get("内外盘比例")
        for column in FINANCIAL_COLUMNS:
            row[column] = old_row.get(column)
        row["数据来源"] = "真实数据"
        row["更新时间"] = now_text
        rows.append(row)

    return pd.DataFrame(rows, columns=CACHE_COLUMNS)


def save_cache(output: Any) -> None:
    temp_file = CACHE_FILE.with_suffix(".csv.tmp")
    output.to_csv(temp_file, index=False, encoding="utf-8-sig")
    temp_file.replace(CACHE_FILE)


def main() -> None:
    print("正在启动 update_cache.py...", flush=True)

    global pd
    try:
        import pandas as pandas  # type: ignore

        pd = pandas
    except Exception as exc:  # noqa: BLE001
        print(f"更新失败：无法导入 pandas。请先运行 pip install -r requirements.txt。原因：{exc}", flush=True)
        return

    try:
        import akshare as ak  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"更新失败：无法导入 akshare。请先运行 pip install -r requirements.txt。原因：{exc}", flush=True)
        return

    spot_df = fetch_spot_data(ak)
    if not is_valid_frame(spot_df):
        return

    try:
        spot_df = normalize_spot_frame(spot_df)
        if spot_df.empty:
            print("更新失败：行情数据没有有效股票代码，没有覆盖 stock_metrics.csv。", flush=True)
            return

        old_cache = read_existing_cache()
        output = build_cache_rows(spot_df, old_cache)
        if output.empty:
            print("更新失败：生成的缓存数据为空，没有覆盖 stock_metrics.csv。", flush=True)
            return

        save_cache(output)
    except Exception as exc:  # noqa: BLE001
        print(f"更新失败：保存 stock_metrics.csv 时出错，没有覆盖原文件。原因：{exc}", flush=True)
        return

    print(f"已更新 stock_metrics.csv，共 {len(output)} 条 A 股数据。", flush=True)


if __name__ == "__main__":
    main()
