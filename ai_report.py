from __future__ import annotations

import json
from typing import Any


DISCLAIMER = "本工具仅用于家庭投资风险体检和学习参考，不构成投资建议。市场有风险，投资需谨慎。"


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

    system_prompt = f"""
你是一名谨慎、通俗、适合给父母解释的家庭投资风险体检助手。
你只根据用户已经完成的风险体检结果做解释，不获取行情，不预测明天涨跌，不做自动交易。

必须遵守：
1. 不荐股，不承诺收益。
2. 不使用“必涨”“抄底”“一定赚钱”“强烈买入”“马上卖出”等表达。
3. 不给买入、卖出、加仓、减仓指令。
4. 可以说“是否适合继续加钱需要谨慎看待”“不建议盲目集中加钱”“建议先保留现金和分散风险”。
5. 少用专业术语，用父母能听懂的话。
6. 明确说明这只是家庭投资风险体检。
7. 结尾必须保留免责声明：{DISCLAIMER}
"""

    user_prompt = f"""
请把下面这份家庭投资风险体检结果，改写成一段给父母看的投资风险说明。

输出格式：
一、先说结论
二、主要需要注意的地方
三、这只股票/这些持仓是否适合继续加钱
四、给家人的稳妥提醒
五、免责声明

体检结果 JSON：
{json.dumps(context, ensure_ascii=False, indent=2)}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1200,
    )

    content = _safe_text(response.choices[0].message.content).strip()
    if DISCLAIMER not in content:
        content = f"{content}\n\n{DISCLAIMER}"
    return content
