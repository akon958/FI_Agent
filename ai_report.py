"""ai_report.py

负责调用 DeepSeek API，生成给父母看的家庭投资风险说明。

设计原则：
- 不荐股、不预测涨跌、不给买卖指令
- 只做家庭投资风险体检说明
- 语言适合父母阅读（口语化、不用专业术语）
- API Key 从 Streamlit Secrets 读取，绝不写进代码
- API 失败时静默降级，不让页面崩溃
"""
from __future__ import annotations

from typing import Any


# ── Key 检查 ────────────────────────────────────────────────────────────────

def get_api_key() -> str | None:
    """从 Streamlit Secrets 读取 DEEPSEEK_API_KEY。
    未配置时返回 None，不抛异常。
    """
    try:
        import streamlit as st
        key = st.secrets.get("DEEPSEEK_API_KEY", "")
        return key if key else None
    except Exception:  # noqa: BLE001
        return None


def is_ai_available() -> bool:
    """判断 AI 功能是否可用（Key 存在即可，不发请求）。"""
    return get_api_key() is not None


# ── Prompt 构建 ──────────────────────────────────────────────────────────────

def _build_prompt(analysis: dict[str, Any]) -> str:
    """把体检结果转成给 DeepSeek 的中文 prompt。"""

    level = analysis.get("level", "未知")
    score = analysis.get("score", 0)
    total_assets = analysis.get("total_assets", 0)
    cash_ratio = analysis.get("cash_ratio", 0)
    stock_ratio = analysis.get("stock_ratio", 0)
    max_single_ratio = analysis.get("max_single_ratio", 0)
    top_industry = analysis.get("top_industry", "未知")
    industry_concentration = analysis.get("industry_concentration", 0)
    data_status = analysis.get("data_status", "未知")
    risk_notes = analysis.get("risk_notes", [])
    module_scores = analysis.get("module_scores", {})
    stock_results = analysis.get("stock_results", [])

    # 持仓摘要
    holdings_lines = []
    for item in stock_results:
        holdings_lines.append(
            f"- {item.get('name', item.get('code', '未知'))}（{item.get('code', '')}）："
            f"占家庭总资金 {item.get('single_ratio', 0) * 100:.1f}%，"
            f"风险等级 {item.get('level', '未知')}，"
            f"行业 {item.get('industry', '未知')}"
        )
    holdings_text = "\n".join(holdings_lines) if holdings_lines else "无持仓数据"

    # 四项得分
    score_lines = [f"- {k}：{v}/100" for k, v in module_scores.items()]
    score_text = "\n".join(score_lines) if score_lines else "无评分数据"

    # 主要风险提示
    risk_text = "\n".join(f"- {n}" for n in risk_notes[:8]) if risk_notes else "无特别风险提示"

    prompt = f"""你是一个帮助普通家庭做投资风险体检的助手。
请根据下面的体检数据，用适合父母阅读的口语化中文，写一段家庭投资风险说明。

【重要限制，必须严格遵守】
1. 不荐股，不提任何具体股票的投资价值
2. 不预测明天或未来的涨跌
3. 不给出买入、卖出、加仓、减仓、持有等任何操作指令
4. 只做风险体检说明，帮家人理解当前的风险状况
5. 语言要像家人聊天一样，避免专业术语，数字要用生活化方式解释
6. 结尾必须写上：本说明仅供家庭风险体检参考，不构成投资建议，市场有风险，投资需谨慎。

【体检数据】
综合风险等级：{level}
综合评分：{score}/100
数据状态：{data_status}

家庭资产概况：
- 家庭可投资总资产：{total_assets:,.0f} 元
- 现金比例：{cash_ratio * 100:.1f}%
- 股票/基金仓位：{stock_ratio * 100:.1f}%
- 单只最大占比：{max_single_ratio * 100:.1f}%
- 持仓最集中的行业：{top_industry}（占股票总仓位 {industry_concentration * 100:.1f}%）

四项评分：
{score_text}

持仓明细：
{holdings_text}

主要风险提示：
{risk_text}

【输出要求】
- 用3到5段话，每段聚焦一个话题（比如：整体情况怎么样、现金够不够用、某只持仓要注意什么、下一步家庭可以关注什么方向）
- 不要用表格、不要用Markdown标题、不要分条列举，用自然段落
- 语气温和、关心家人，像儿女跟父母解释一样
- 字数控制在400字以内
"""
    return prompt


# ── API 调用 ─────────────────────────────────────────────────────────────────

def generate_ai_report(analysis: dict[str, Any]) -> tuple[str | None, str | None]:
    """调用 DeepSeek API 生成 AI 风险说明。

    Returns:
        (report_text, error_message)
        成功时 report_text 有内容，error_message 为 None。
        失败时 report_text 为 None，error_message 说明原因。
    """
    api_key = get_api_key()
    if not api_key:
        return None, "未配置 AI 分析功能"

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        prompt = _build_prompt(analysis)

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个帮助普通家庭做投资风险体检的助手。"
                        "你只做风险体检说明，绝不荐股，绝不预测涨跌，绝不给出任何操作指令。"
                        "语言要口语化，适合没有金融背景的父母阅读。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.5,
            stream=False,
        )

        text = response.choices[0].message.content or ""
        text = text.strip()

        if not text:
            return None, "AI 返回内容为空，请稍后重试。"

        return text, None

    except ImportError:
        return None, "openai 库未安装，请检查 requirements.txt。"
    except Exception as e:  # noqa: BLE001
        # 不暴露具体错误细节给用户，只记录日志
        error_hint = str(e)[:80] if str(e) else "未知错误"
        # 对常见错误给出友好提示
        if "401" in error_hint or "Authentication" in error_hint:
            return None, "AI 分析暂时不可用（API Key 验证失败），基础风险体检结果不受影响。"
        if "429" in error_hint or "rate" in error_hint.lower():
            return None, "AI 分析暂时不可用（请求过于频繁），稍后再试，基础风险体检结果不受影响。"
        if "timeout" in error_hint.lower() or "connect" in error_hint.lower():
            return None, "AI 分析暂时不可用（网络连接超时），基础风险体检结果不受影响。"
        return None, "AI 分析暂时不可用，基础风险体检结果不受影响。"
