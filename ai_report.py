from __future__ import annotations

import json
from typing import Any


DISCLAIMER = "本工具只做家庭投资风险体检和学习参考，不构成任何投资建议，也不提供买卖推荐。"


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _fmt_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "暂无"


def _sanitize_report_text(text: str) -> str:
    replacements = {
        "买入": "继续观察",
        "卖出": "重点复盘",
        "加仓": "增加投入前先讨论",
        "减仓": "控制集中度",
        "强烈": "明显",
        "抄底": "低位判断",
        "必涨": "确定上涨",
        "一定赚钱": "确定有收益",
        "马上操作": "立刻处理",
        "预测涨跌": "判断短期方向",
        "我们可能需要慢慢调整": "后续讨论时可以重点关注这一点",
    }
    safe = text
    for old, new in replacements.items():
        safe = safe.replace(old, new)
    return safe


def _flatten_missing_data(missing_data: dict[str, Any]) -> str:
    if not missing_data:
        return "这次体检没有发现明显的数据缺口。"
    parts = []
    valuation_missing = False
    for title, items in missing_data.items():
        if not items:
            continue
        if "估值" in title:
            valuation_missing = True
            continue
        parts.append(f"{title}涉及 {len(items)} 只标的")
    if valuation_missing:
        parts.insert(0, "估值数据暂缺，本次不评价估值高低。")
    return "；".join(parts) if parts else "这次体检没有发现明显的数据缺口。"


def generate_agent_report(agent_context: dict[str, Any]) -> str:
    """Generate a family-facing report strictly from the agent_context fields."""
    holdings = agent_context.get("holdings", []) or []
    main_risks = agent_context.get("main_risks", []) or []
    missing_data = agent_context.get("missing_data", {}) or {}
    risk_score = agent_context.get("risk_score", 0)
    risk_level = agent_context.get("risk_level", "暂无")
    cash_ratio = agent_context.get("cash_ratio", 0)
    stock_ratio = agent_context.get("stock_ratio", 0)
    max_position_ratio = agent_context.get("max_position_ratio", 0)
    risk_preference = agent_context.get("risk_preference", "稳健")
    data_status = agent_context.get("data_status", "本地缓存")
    history_summary = agent_context.get("history_summary", "")

    if max_position_ratio >= 0.40:
        overall = "这个组合需要多留心，主要是单只标的占比偏高，家庭资金集中度不低。"
    elif stock_ratio >= 0.75:
        overall = "这个组合的股票/基金占比较高，遇到市场波动时，家里感受到的压力可能会更明显。"
    elif cash_ratio >= 0.30:
        overall = "这个组合整体现金垫比较厚，短期用钱压力相对小一些。"
    else:
        overall = "这个组合整体风险不算极端，但仍要重点看现金垫、单只占比和数据是否完整。"

    primary_risk = main_risks[0] if main_risks else "目前没有特别刺眼的风险点，但仍建议定期复盘。"
    holding_names = "、".join(
        f"{item.get('code', '')} {item.get('name', '')}".strip()
        for item in holdings[:5]
    ) or "当前持仓"

    missing_text = _flatten_missing_data(missing_data)
    history_text = f"最近历史记录提示：{history_summary}" if history_summary else "目前没有可参考的历史体检摘要。"

    report = f"""【整体判断】
爸妈看这个结果时，先记住一句话：这次体检只是在看家庭持仓风险，不是在判断明天涨跌。当前组合涉及 {holding_names}，综合评分为 {risk_score}/100，风险等级是{risk_level}。按“{risk_preference}”的风险承受能力看，现金比例约为 {_fmt_percent(cash_ratio)}，股票/基金持仓比例约为 {_fmt_percent(stock_ratio)}，最大单只持仓占比约为 {_fmt_percent(max_position_ratio)}。{overall}

【主要风险】
这次最需要关注的是：{primary_risk} 如果钱集中在少数标的或同一类行业上，家里对单一变化会更敏感。后续讨论时可以重点关注这一点，同时把家庭备用金放在前面考虑。

【数据缺失说明】
当前数据状态：{data_status}。{missing_text} 如果某些数据暂时没有，本次就只做保守体检，不把缺失部分当成好消息，也不编造没有的数据。

【给爸妈重点看的地方】
爸妈看这个结果时，不用盯着复杂指标，先看三件事：第一，现金够不够应付家里临时用钱；第二，单只标的占比会不会太高；第三，公司的经营和财务数据是否够完整。{history_text} 这个结果适合拿来做家庭讨论和复盘，不适合当成操作指令。

【免责声明】
{DISCLAIMER}"""
    return _sanitize_report_text(report)


def _build_ai_context(analysis: dict[str, Any]) -> dict[str, Any]:
    stock_items = []
    for item in analysis.get("stock_results", []):
        stock_items.append(
            {
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "amount": item.get("amount", 0),
                "single_ratio": item.get("single_ratio", 0),
                "level": item.get("level", ""),
                "industry": item.get("industry", ""),
                "financial_text": item.get("financial_text", ""),
                "heat_text": item.get("heat_text", ""),
                "position_notes": item.get("position_notes", []),
                "price": item.get("price"),
                "pct_change": item.get("pct_change"),
                "turnover": item.get("turnover"),
                "pe": item.get("pe"),
                "pb": item.get("pb"),
                "turnover_rate": item.get("turnover_rate"),
                "market_cap": item.get("market_cap"),
                "float_market_cap": item.get("float_market_cap"),
                "volume_ratio": item.get("volume_ratio"),
                "amplitude": item.get("amplitude"),
                "in_out_ratio": item.get("in_out_ratio"),
                "roe": item.get("roe"),
                "net_margin": item.get("net_margin"),
                "gross_margin": item.get("gross_margin"),
                "revenue_growth": item.get("revenue_growth"),
                "profit_growth": item.get("profit_growth"),
                "debt_ratio": item.get("debt_ratio"),
                "cashflow_profit_ratio": item.get("cashflow_profit_ratio"),
                "updated_at": item.get("updated_at"),
                "data_source": item.get("data_source", ""),
                "market_source": item.get("market_source", ""),
                "finance_source": item.get("finance_source", ""),
            }
        )

    return {
        "score": analysis.get("score", 0),
        "level": analysis.get("level", ""),
        "level_text": analysis.get("level_text", ""),
        "data_status": analysis.get("data_status", ""),
        "analysis_time": analysis.get("analysis_time", ""),
        "cash": analysis.get("cash", 0),
        "total_assets": analysis.get("total_assets", 0),
        "cash_ratio": analysis.get("cash_ratio", 0),
        "stock_ratio": analysis.get("stock_ratio", 0),
        "max_single_ratio": analysis.get("max_single_ratio", 0),
        "top_industry": analysis.get("top_industry", ""),
        "industry_concentration": analysis.get("industry_concentration", 0),
        "module_scores": analysis.get("module_scores", {}),
        "risk_notes": analysis.get("risk_notes", []),
        "advice": analysis.get("advice", []),
        "stocks": stock_items,
    }


def generate_parent_friendly_report(analysis: dict[str, Any], api_key: str) -> str:
    """Call DeepSeek to write a plain-language risk explanation for family users."""
    if not api_key:
        raise ValueError("missing api key")

    from openai import OpenAI

    context = _build_ai_context(analysis)
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    rules = [
        "1. 语气像在家庭微信群里回消息：用'我们''爸''妈'，偶尔用'其实''不过''另外'等口语连接词，"
        "读起来像真人在说话，不像在朗读报告。不用'您家''贵家庭''阁下'等疏远表达。",
        "2. 不推荐任何股票，不预测涨跌，不说'必涨''抄底''一定赚''马上卖'，"
        "不给买入/卖出/加仓/减仓的具体指令。",
        "3. 每次出现财务或交易指标，先写专业术语，括号里跟一句通俗说明，两者缺一不可。"
        "标准写法示例（格式不变）：\n"
        "   ROE（公司用自己的钱赚钱的能力）\n"
        "   净利率（每卖出100元最终留下多少利润）\n"
        "   毛利率（产品本身的赚钱空间）\n"
        "   营收增长率（公司收入有没有在增加）\n"
        "   净利润增长率（公司最终到手的钱有没有在增加）\n"
        "   资产负债率（公司借了多少钱相对自己的家底）\n"
        "   经营现金流（公司账面利润有多少真正变成了现金）\n"
        "   换手率（今天有多少人在买卖这只股票）\n"
        "   量比（今天成交量比平时多多少）\n"
        "   振幅（今天股价最高最低相差多少）\n"
        "   市盈率（按现在股价买，需要多少年回本）\n"
        "   市净率（股价相对公司账面资产贵不贵）",
        "4. 总字数控制在 600～700 字，内容要扎实，但不要凑字数，爸妈一口气能看完最好。",
        "5. 按下面五段结构输出，每段加标题，顺序不变，不增减段落：\n"
        "   【整体感觉】\n   【主要风险】\n   【数据缺失说明】\n   【爸妈重点看什么】\n   【免责声明】",
        "6. 【免责声明】那段原文照抄，一字不改：" + DISCLAIMER,
    ]

    system_prompt = (
        "你是家里懂一点投资的亲戚，正在用微信跟家人解释这次持仓风险体检的结果。\n"
        "你说话直接、温和，会把枯燥的数据翻译成家人听得懂的话，"
        "但绝不给任何买卖建议，因为你知道预测市场是不靠谱的。\n\n"
        "写作要求：\n"
        + "\n".join(rules)
    )

    data_note = (
        "数据缺失处理：\n"
        "- 某只持仓的 finance_source 是「数据缺失」→ 【数据缺失说明】里提一句：行情找到了，但财务数据暂时缺，"
        "对这只股票的公司质量判断不完整，要多留心。\n"
        "- 所有数据都完整 → 写：这次体检数据都找到了，没有明显缺失。"
    )

    user_prompt = (
        "下面是家庭投资风险体检的 JSON 结果，请按你的写作要求输出给爸妈看的说明。\n\n"
        + data_note
        + "\n\n体检数据：\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

    # deepseek-reasoner (R1) 推理模型：分析更深入，响应约慢 3-5 倍，费用约贵 15 倍。
    # 如需切回快速版，把 model 改为 "deepseek-chat"，temperature 改回 0.35。
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,   # R1 官方推荐区间 0.5-0.7
        max_tokens=2048,
    )

    content = _safe_text(response.choices[0].message.content).strip()
    if DISCLAIMER not in content:
        content = f"{content}\n\n{DISCLAIMER}"
    return content
