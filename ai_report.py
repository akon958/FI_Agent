from __future__ import annotations

import json
from typing import Any


DISCLAIMER = "本工具只做家庭投资风险体检和学习参考，不构成任何投资建议，也不提供买卖推荐。"


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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
        "1. 口吻像子女跟爸妈聊天，自然、亲切，不用您家、贵家庭等疏远的表达。",
        "2. 不荐股，不承诺收益，不用必涨、抄底、一定赚钱、强烈买入、马上卖出。",
        "3. 不给具体买入、卖出、加仓、减仓指令。",
        "4. 专业词汇用生活化语言替换，例如：换手率高→今天这只股票买卖的人特别多、ROE→公司用自己的錢赚錢的能力。",
        "5. 字数控制在 500～800 字，不要太长，爸妈看完不累。",
        "6. 严格按照以下五段结构输出，每段用标题标注，不要增减段落：\n   【整体感觉】\n   【主要风险】\n   【数据缺失说明】\n   【爸妈重点看什么】\n   【免责声明】",
        "7. 【免责声明】段落内容必须原文照抄，一字不差：" + DISCLAIMER,
    ]

    system_prompt = (
        "你是一个帮子女跟父母解释家庭投资风险的助手。\n"
        "你的任务是把体检工具跑出来的数据结果，"
        "用子女和爸妈聊天的口吻写成一段话，"
        "让爸妈听得懂、不焦虑、也不盲目乐观。\n\n"
        "写作规则：\n"
        + "\n".join(rules)
    )

    data_note = (
        "- 如果某只持仓的财务数据来源是「数据缺失」，"
        "在【数据缺失说明】里说清楚："
        "行情数据已匹配，但财务数据暂时没找到，"
        "所以对这只股票的公司质量判断不完整，要多留心。\n"
        "- 如果所有持仓数据都完整，【数据缺失说明】"
        "写：这次体检的数据都找到了，没有明显缺失。"
    )

    user_prompt = (
        "请根据下面这份家庭投资风险体检结果，"
        "按照你的写作规则输出给爸妈看的说明。\n\n"
        "注意：\n"
        + data_note
        + "\n\n体检结果 JSON：\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    content = _safe_text(response.choices[0].message.content).strip()
    if DISCLAIMER not in content:
        content = f"{content}\n\n{DISCLAIMER}"
    return content
