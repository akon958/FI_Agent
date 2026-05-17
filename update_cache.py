from __future__ import annotations

import argparse
import concurrent.futures
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


CACHE_FILE = Path(__file__).with_name("stock_metrics.csv")
CHECKPOINT_FILE = CACHE_FILE.with_suffix(".csv.ckpt")

pd: Any = None

# 单只股票财务请求的最长等待秒数
FINANCE_TIMEOUT = 12

CACHE_COLUMNS = [
    "代码", "名称", "最新价", "涨跌幅", "成交额",
    "市盈率-动态", "市净率", "换手率", "总市值", "流通市值",
    "所属行业", "量比", "振幅", "内外盘比例",
    "ROE", "净利率", "毛利率", "营收增长率", "净利润增长率",
    "资产负债率", "经营现金流/净利润",
    "数据来源", "更新时间",
]

FINANCIAL_COLUMNS = [
    "ROE", "净利率", "毛利率", "营收增长率", "净利润增长率",
    "资产负债率", "经营现金流/净利润",
]

COLUMN_ALIASES = {
    "代码":     ["代码", "股票代码", "证券代码", "symbol"],
    "名称":     ["名称", "股票名称", "证券简称", "简称", "name"],
    "最新价":   ["最新价", "最新价格", "最新收盘价", "收盘", "现价", "trade", "price"],
    "涨跌幅":   ["涨跌幅", "涨跌幅%", "涨幅", "changepercent", "pct_chg"],
    "成交额":   ["成交额", "成交金额", "amount"],
    "市盈率-动态": ["市盈率-动态", "市盈率动态", "动态市盈率", "市盈率", "pe", "pe_ttm"],
    "市净率":   ["市净率", "pb"],
    "换手率":   ["换手率", "换手率%", "turnover", "turnoverrate"],
    "总市值":   ["总市值", "market_cap", "总市值(元)"],
    "流通市值": ["流通市值", "circulating_market_cap", "流通市值(元)"],
    "量比":     ["量比"],
    "振幅":     ["振幅", "振幅%", "amplitude"],
}

# 财务字段在 AkShare 接口中的列名别名
FINANCIAL_ALIASES: dict[str, list[str]] = {
    "ROE": [
        "净资产收益率", "加权净资产收益率", "摊薄净资产收益率", "roe", "ROE",
    ],
    "净利率": [
        "销售净利率", "净利润率", "净利率", "net_profit_margin",
    ],
    "毛利率": [
        "销售毛利率", "毛利率", "gross_profit_margin", "gross_margin",
    ],
    "营收增长率": [
        "营业总收入同比增长率", "营业收入增长率", "营收增长率",
        "revenue_growth_yoy", "revenue_yoy", "营收同比增长率",
    ],
    "净利润增长率": [
        "净利润同比增长率", "归母净利润增长率", "净利润增长率",
        "net_profit_growth_yoy", "profit_yoy",
    ],
    "资产负债率": [
        "资产负债率", "debt_to_assets", "负债率",
    ],
    "经营现金流/净利润": [
        "经营活动产生的现金流量净额/净利润",
        "经营现金流/净利润", "经营性现金流/净利润", "cash_profit_ratio",
        "经营活动现金流量/净利润",
    ],
}

# 这些字段 AkShare 通常以百分比形式返回（15.23 = 15.23%），需 /100 转为小数
# analyzer.py 期望小数形式（0.1523）
PCT_FIELDS    = {"ROE", "净利率", "毛利率", "资产负债率"}
GROWTH_FIELDS = {"营收增长率", "净利润增长率"}
# 经营现金流/净利润 是比率，无需转换


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def normalize_code(code: Any) -> str:
    text = str(code or "").strip().upper()
    if text.startswith(("SH", "SZ", "BJ")):
        text = text[2:]
    return text.zfill(6) if text else ""


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
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
        try:
            val = row[name]
            if val is not None and not pd.isna(val):
                return val
        except (KeyError, TypeError):
            pass
    return None


def is_valid_frame(df: Any) -> bool:
    return df is not None and hasattr(df, "empty") and not df.empty


# ── 缓存读写 ──────────────────────────────────────────────────────────────────

def read_existing_cache() -> Any:
    if not CACHE_FILE.exists():
        return pd.DataFrame(columns=CACHE_COLUMNS)
    try:
        df = pd.read_csv(CACHE_FILE, dtype={"代码": str, "股票代码": str})
    except Exception as exc:  # noqa: BLE001
        print(f"读取旧缓存失败，将重新生成。原因：{exc}", flush=True)
        return pd.DataFrame(columns=CACHE_COLUMNS)
    if "代码" not in df.columns and "股票代码" in df.columns:
        df["代码"] = df["股票代码"]
    for col in CACHE_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df["代码"] = df["代码"].map(normalize_code)
    return df[df["代码"] != ""].drop_duplicates(subset=["代码"], keep="last")


def save_cache(df: Any, path: Path | None = None) -> None:
    target = path or CACHE_FILE
    tmp = target.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(target)


# ── 行情抓取 ──────────────────────────────────────────────────────────────────

def fetch_market(
    label: str,
    fetcher: Callable[[], Any],
) -> Any | None:
    try:
        df = fetcher()
    except Exception as exc:  # noqa: BLE001
        print(f"{label} 获取失败：{exc}", flush=True)
        return None
    if not is_valid_frame(df):
        print(f"{label} 返回空数据。", flush=True)
        return None
    print(f"{label} 获取成功，共 {len(df)} 条", flush=True)
    return df


def fetch_spot_data(ak: Any) -> Any | None:
    print("正在尝试获取沪深京 A 股全市场数据...", flush=True)
    df = fetch_market("全市场接口 stock_zh_a_spot_em", ak.stock_zh_a_spot_em)
    if is_valid_frame(df):
        return df

    print("全市场接口失败，分市场获取...", flush=True)
    frames = []
    for name, fn in [("沪A", ak.stock_sh_a_spot_em),
                     ("深A", ak.stock_sz_a_spot_em),
                     ("京A", ak.stock_bj_a_spot_em)]:
        sub = fetch_market(name, fn)
        if is_valid_frame(sub):
            frames.append(sub)
    if frames:
        combined = pd.concat(frames, ignore_index=True, sort=False)
        print(f"分市场合并完成，共 {len(combined)} 条。", flush=True)
        return combined

    print("东财接口全部失败，尝试备用接口 stock_zh_a_spot ...", flush=True)
    df = fetch_market("备用接口 stock_zh_a_spot", ak.stock_zh_a_spot)
    if is_valid_frame(df):
        return df

    print("更新失败：所有行情接口均无有效数据。", flush=True)
    return None


def normalize_spot_frame(spot_df: Any) -> Any:
    df = spot_df.copy()
    code_col = next(
        (c for c in COLUMN_ALIASES["代码"] if c in df.columns), None
    )
    if code_col is None:
        print(f"找不到代码字段，实际列：{list(df.columns)}", flush=True)
        return pd.DataFrame(columns=CACHE_COLUMNS)
    df["代码"] = df[code_col].map(normalize_code)
    return df[df["代码"] != ""].drop_duplicates(subset=["代码"], keep="last")


def build_cache_rows(spot_df: Any, old_cache: Any) -> Any:
    old_idx = (
        old_cache.set_index("代码", drop=False).to_dict("index")
        if not old_cache.empty else {}
    )
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows: list[dict[str, Any]] = []

    for _, spot_row in spot_df.iterrows():
        code = normalize_code(first_present(spot_row, COLUMN_ALIASES["代码"]))
        if not code:
            continue
        old = old_idx.get(code, {})
        row: dict[str, Any] = {col: old.get(col) for col in CACHE_COLUMNS}
        row["代码"]       = code
        row["名称"]       = first_present(spot_row, COLUMN_ALIASES["名称"]) or old.get("名称") or code
        row["最新价"]     = to_float(first_present(spot_row, COLUMN_ALIASES["最新价"]))
        row["涨跌幅"]     = to_float(first_present(spot_row, COLUMN_ALIASES["涨跌幅"]))
        row["成交额"]     = to_float(first_present(spot_row, COLUMN_ALIASES["成交额"]))
        row["市盈率-动态"] = to_float(first_present(spot_row, COLUMN_ALIASES["市盈率-动态"]))
        row["市净率"]     = to_float(first_present(spot_row, COLUMN_ALIASES["市净率"]))
        row["换手率"]     = to_float(first_present(spot_row, COLUMN_ALIASES["换手率"]))
        row["总市值"]     = to_float(first_present(spot_row, COLUMN_ALIASES["总市值"]))
        row["流通市值"]   = to_float(first_present(spot_row, COLUMN_ALIASES["流通市值"]))
        row["量比"]       = to_float(first_present(spot_row, COLUMN_ALIASES["量比"]))
        row["振幅"]       = to_float(first_present(spot_row, COLUMN_ALIASES["振幅"]))
        row["所属行业"]   = old.get("所属行业") or "未知"
        row["内外盘比例"] = old.get("内外盘比例")
        for col in FINANCIAL_COLUMNS:         # 保留旧财务数据
            row[col] = old.get(col)
        row["数据来源"]   = "真实数据"
        row["更新时间"]   = now_text
        rows.append(row)

    return pd.DataFrame(rows, columns=CACHE_COLUMNS)


# ── 财务数据抓取 ──────────────────────────────────────────────────────────────

def _normalize_pct(field: str, value: float) -> float:
    """AkShare 多数接口以百分比形式返回（15.23 = 15.23%），
    analyzer.py 期望小数（0.1523）。按字段和数值大小判断是否 /100。"""
    if field in PCT_FIELDS and abs(value) > 1:
        return value / 100.0
    if field in GROWTH_FIELDS and abs(value) > 10:
        return value / 100.0
    return value


def _extract_financial(df: Any) -> dict[str, float]:
    """从财务 DataFrame 取最新行，映射到 FINANCIAL_COLUMNS。"""
    result: dict[str, float] = {}
    if not is_valid_frame(df):
        return result
    for _, row in df.iterrows():
        for target, aliases in FINANCIAL_ALIASES.items():
            if target in result:
                continue
            raw = first_present(row, aliases)
            if raw is None:
                continue
            val = to_float(raw)
            if val is not None:
                result[target] = _normalize_pct(target, val)
        if len(result) == len(FINANCIAL_COLUMNS):
            break
    return result


def _fetch_one_financial(ak: Any, code: str) -> dict[str, float]:
    """尝试两个接口，合并结果。此函数在子线程中运行，受外部 timeout 控制。"""
    result: dict[str, float] = {}

    # 接口 1：财务摘要
    try:
        df = ak.stock_financial_abstract(symbol=code)
        result.update(_extract_financial(df))
    except Exception:  # noqa: BLE001
        pass

    # 接口 2：乐咕指标，补全缺失字段
    if len(result) < len(FINANCIAL_COLUMNS):
        try:
            df = ak.stock_a_lg_indicator(symbol=code)
            for field, val in _extract_financial(df).items():
                if field not in result:
                    result[field] = val
        except Exception:  # noqa: BLE001
            pass

    return result


def fetch_financial_with_timeout(ak: Any, code: str) -> dict[str, float]:
    """在独立线程中执行财务抓取，超过 FINANCE_TIMEOUT 秒强制返回空字典。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exe:
        future = exe.submit(_fetch_one_financial, ak, code)
        try:
            return future.result(timeout=FINANCE_TIMEOUT)
        except concurrent.futures.TimeoutError:
            return {}
        except Exception:  # noqa: BLE001
            return {}


# ── 财务数据批量回填 ──────────────────────────────────────────────────────────

def enrich_with_financial(ak: Any, df: Any, limit: int = 0) -> Any:
    """逐只抓财务数据，回填 FINANCIAL_COLUMNS，每 10 只打印进度，每 100 只存档。"""
    codes: list[str] = df["代码"].tolist()
    if limit > 0:
        codes = codes[:limit]
        print(f"  --limit {limit}：仅对前 {limit} 只股票抓取财务数据。", flush=True)

    total   = len(codes)
    success = 0
    timeout_count = 0
    fail    = 0

    # 以列表形式缓存新财务值，最后批量写回（避免逐行 loc 操作拖慢速度）
    new_fin: dict[str, list[Any]] = {col: [None] * len(df) for col in FINANCIAL_COLUMNS}
    code_to_idx = {c: i for i, c in enumerate(df["代码"].tolist())}

    print(f"开始抓取财务数据，共 {total} 只（超时阈值 {FINANCE_TIMEOUT}s/只）...", flush=True)
    t_start = time.time()

    for seq, code in enumerate(codes, 1):
        t0 = time.time()
        try:
            fin = fetch_financial_with_timeout(ak, code)
        except Exception:  # noqa: BLE001
            fin = {}

        elapsed = time.time() - t0
        idx = code_to_idx.get(code)

        if fin and idx is not None:
            for col in FINANCIAL_COLUMNS:
                if col in fin:
                    new_fin[col][idx] = fin[col]
            success += 1
        else:
            if elapsed >= FINANCE_TIMEOUT - 0.5:
                timeout_count += 1
            else:
                fail += 1

        # 每 10 只打印一次进度
        if seq % 10 == 0 or seq == total:
            elapsed_total = time.time() - t_start
            rate = seq / elapsed_total if elapsed_total > 0 else 0
            eta  = (total - seq) / rate if rate > 0 else 0
            print(
                f"  [{seq:5d}/{total}] 成功 {success}  超时 {timeout_count}  失败 {fail}"
                f"  速度 {rate:.1f}只/s  预计剩余 {eta/60:.1f}min",
                flush=True,
            )

        # 每 100 只存一次检查点（只写财务字段，行情字段已在 df 里）
        if seq % 100 == 0:
            _apply_fin_to_df(df, new_fin)
            save_cache(df, CHECKPOINT_FILE)
            print(f"  ✓ 检查点已保存 → {CHECKPOINT_FILE.name}", flush=True)

    # 最终写回
    _apply_fin_to_df(df, new_fin)
    # 清理检查点文件
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    print(
        f"财务数据完成：成功 {success} 只 / 超时 {timeout_count} 只 / 失败 {fail} 只。",
        flush=True,
    )
    return df


def _apply_fin_to_df(df: Any, new_fin: dict[str, list[Any]]) -> None:
    """将 new_fin 里非 None 的值合并回 df（已有旧值的字段不覆盖为 None）。"""
    for col in FINANCIAL_COLUMNS:
        existing = df[col].tolist()
        merged = [
            nv if nv is not None else ev
            for nv, ev in zip(new_fin[col], existing)
        ]
        df[col] = merged


# ── 主流程 ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="更新 stock_metrics.csv：先抓行情，再抓财务数据。"
    )
    parser.add_argument(
        "--skip-finance",
        action="store_true",
        help="跳过财务数据抓取，只更新行情数据（速度快，适合日常刷新）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="只处理前 N 只股票（财务数据部分），0 表示不限制（默认）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("正在启动 update_cache.py...", flush=True)
    if args.skip_finance:
        print("  模式：--skip-finance，只更新行情数据。", flush=True)
    if args.limit > 0:
        print(f"  模式：--limit {args.limit}，财务数据只处理前 {args.limit} 只。", flush=True)

    global pd
    try:
        import pandas as _pd  # type: ignore
        pd = _pd
    except Exception as exc:  # noqa: BLE001
        print(f"无法导入 pandas：{exc}", flush=True)
        return

    try:
        import akshare as ak  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"无法导入 akshare：{exc}", flush=True)
        return

    # ── 第一步：行情 ──────────────────────────────────────────────────────────
    spot_df = fetch_spot_data(ak)
    if not is_valid_frame(spot_df):
        return

    try:
        spot_df = normalize_spot_frame(spot_df)
        if spot_df.empty:
            print("行情数据没有有效股票代码，中止。", flush=True)
            return
        old_cache = read_existing_cache()
        output = build_cache_rows(spot_df, old_cache)
        if output.empty:
            print("生成的缓存数据为空，中止。", flush=True)
            return
    except Exception as exc:  # noqa: BLE001
        print(f"处理行情数据出错：{exc}", flush=True)
        return

    print(f"行情数据处理完成，共 {len(output)} 只股票。", flush=True)

    # ── 第二步：财务数据 ──────────────────────────────────────────────────────
    if args.skip_finance:
        print("已跳过财务数据抓取（--skip-finance）。", flush=True)
    else:
        output = enrich_with_financial(ak, output, limit=args.limit)

    # ── 第三步：保存 ──────────────────────────────────────────────────────────
    try:
        save_cache(output)
    except Exception as exc:  # noqa: BLE001
        print(f"保存 stock_metrics.csv 失败：{exc}", flush=True)
        return

    fin_count = int(output[FINANCIAL_COLUMNS].notna().any(axis=1).sum())
    print(
        f"\n完成！stock_metrics.csv 已更新：{len(output)} 只 A 股，"
        f"其中 {fin_count} 只含财务数据。",
        flush=True,
    )


if __name__ == "__main__":
    main()
