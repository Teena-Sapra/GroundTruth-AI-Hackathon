from typing import Dict, Any
import re

import pandas as pd

from .utils.logging_utils import get_logger
from .gemini_client import call_gemini_api

logger = get_logger(__name__)


def clean_markdown(text: str) -> str:
    """
    Clean up any markdown-style formatting that the LLM might produce.
    - Remove headings like ##, ###
    - Remove bold/italic markers (**text**, *text*, _text_)
    - Remove stray asterisks
    - Normalize excessive newlines
    """
    if not text:
        return text

    # Remove markdown headers at line starts (##, ###, etc)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Replace bold/italic markdown with plain text
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # **bold**
    text = re.sub(r"\*(.*?)\*", r"\1", text)      # *italic*
    text = re.sub(r"_([^_]*)_", r"\1", text)      # _italic_

    # Remove stray asterisks that might remain
    text = text.replace("*", "")

    # Collapse 3+ newlines into max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _build_prompt(metrics: Dict[str, Any], config) -> str:
    client_name = config["report"]["client_name"]
    week_start = config["report"]["week_start"]
    week_end = config["report"]["week_end"]

    overall = metrics["overall"]
    campaign_summary: pd.DataFrame = metrics["campaign_summary"]

    campaign_lines = []
    for _, row in campaign_summary.iterrows():
        campaign_lines.append(
            f"- {row['campaign_id']}: "
            f"{int(row['impressions'])} impressions, "
            f"{int(row['clicks'])} clicks, "
            f"{int(row['conversions'])} conversions, "
            f"CTR={row['ctr']:.2%}, "
            f"CPC={row['cpc']:.2f}, "
            f"CPA={row['cpa']:.2f}"
        )

    campaign_block = "\n".join(campaign_lines)

    prompt = f"""
You are a senior marketing data analyst. Your job is to explain campaign performance clearly
to a non-technical client.

IMPORTANT FORMAT RULES:
- Do NOT use markdown.
- Do NOT use headings like ##, ###, ####.
- Do NOT use bold, italics, asterisks (*) or underscores (_).
- Write in plain English sentences only.
- Use normal paragraphs separated by blank lines.
- Do not use bullet symbols like "-" or "•" in the final answer.
- Do not include numbered lists like "1., 2., 3.".

Client name: {client_name}
Reporting period: {week_start} to {week_end}

Overall performance:
- Impressions: {int(overall['total_impressions'])}
- Clicks: {int(overall['total_clicks'])}
- Conversions: {int(overall['total_conversions'])}
- Spend: {overall['total_spend']:.2f}
- CTR: {overall['overall_ctr']:.2%}
- CPC: {overall['overall_cpc']:.2f}
- CPA: {overall['overall_cpa']:.2f}
- CVR: {overall['overall_cvr']:.2%}

Campaign details:
{campaign_block}

TASK:
Write a concise, executive-friendly weekly performance summary in 3 short sections:

1. Overall Performance:
   Summarize how the account performed this week in 2–3 sentences.

2. Key Campaign Insights:
   Describe which campaigns did well or poorly, focusing on conversions, CTR and CPA.
   Mention them by name in sentences (for example: "Campaign CAMP01 performed strongly...").

3. Recommendations:
   Suggest 1–3 clear actions the client should take next week to improve performance.

Remember:
- Plain text only.
- No markdown.
- No bullets.
- No headings.
- No emojis.
"""
    return prompt.strip()


def generate_insights(metrics: Dict[str, Any], config) -> Dict[str, str]:
    """
    Generate insights using Gemini via raw HTTP API.
    If anything goes wrong, raise RuntimeError (no fallback).
    """
    llm_cfg = config.get("llm", {})
    if not llm_cfg.get("enabled", True):
        msg = "LLM is disabled in config, but this project requires an active LLM."
        logger.error(msg)
        raise RuntimeError(msg)

    # System prompt defines persona + behavior; user prompt carries full context.
    system_prompt = (
        "You are a senior performance marketing analyst. "
        "You always follow formatting instructions strictly and never return markdown."
    )

    user_prompt = _build_prompt(metrics, config)

    contents = [
        {
            "role": "user",
            "parts": [{"text": user_prompt}],
        }
    ]

    logger.info("Calling Gemini HTTP API for insights...")
    text = call_gemini_api(system_prompt, contents)

    if not text or text.startswith("Error") or text.startswith("FATAL ERROR"):
        msg = f"Gemini call failed: {text}"
        logger.error(msg)
        raise RuntimeError(msg)

    # Clean any accidental markdown / symbols the model might still output
    summary = clean_markdown(text.strip())
    logger.info("Gemini insights generated successfully via HTTP API.")

    return {
        "executive_summary": summary,
    }
