from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.models import GroqTextResponse, ImportRisk
from app.services.explanations import fallback_ask, fallback_explain, fallback_summary


async def explain_risk(settings: Settings, risk: ImportRisk, column_role: str = "") -> GroqTextResponse:
    fallback = fallback_explain(risk, column_role)
    if not settings.ai_explanations_enabled or not settings.groq_configured:
        return GroqTextResponse(text=fallback, source="fallback", ai_available=False)

    payload = {
        "category": risk.category.value,
        "column": risk.column,
        "columnRole": column_role or risk.column,
        "affectedRows": risk.affected_rows,
        "originalExample": risk.examples[0].original if risk.examples else "",
        "convertedExample": risk.examples[0].converted if risk.examples else "",
        "recommendedType": risk.recommended_type.value,
        "outsidePreview": risk.outside_preview_count > 0,
    }
    prompt = (
        "Rewrite this structured Databricks import risk as 2 short sentences for a PM. "
        "Do not invent new risks or change counts. Mention what changed, why it matters, and the fix.\n"
        f"DATA: {json.dumps(payload)}"
    )
    text = await _chat(settings, prompt)
    if not text:
        return GroqTextResponse(text=fallback, source="fallback", ai_available=False)
    return GroqTextResponse(text=text.strip(), source="groq", ai_available=True)


async def import_summary(
    settings: Settings,
    unresolved: list[ImportRisk],
    resolved: list[ImportRisk],
    total_rows: int,
    preview_limit: int,
) -> GroqTextResponse:
    fallback = fallback_summary(unresolved, resolved, total_rows, preview_limit)
    if not settings.ai_explanations_enabled or not settings.groq_configured:
        return GroqTextResponse(text=fallback, source="fallback", ai_available=False)

    payload = {
        "totalRows": total_rows,
        "previewLimit": preview_limit,
        "unresolved": [
            {
                "category": r.category.value,
                "column": r.column,
                "affectedRows": r.affected_rows,
                "severity": r.severity.value,
                "outsidePreview": r.outside_preview_count > 0,
            }
            for r in unresolved
        ],
        "resolvedCount": len(resolved),
    }
    prompt = (
        "Summarize this import confidence scan in at most 3 sentences. "
        "Do not invent risks. Prefer business impact language.\n"
        f"DATA: {json.dumps(payload)}"
    )
    text = await _chat(settings, prompt)
    if not text:
        return GroqTextResponse(text=fallback, source="fallback", ai_available=False)
    return GroqTextResponse(text=text.strip(), source="groq", ai_available=True)


async def ask(settings: Settings, question: str, context: dict[str, Any]) -> GroqTextResponse:
    unresolved = context.get("unresolved_risks") or []
    resolved = context.get("resolved_risks") or []
    fallback = fallback_ask(question, unresolved, resolved)
    if not settings.ai_explanations_enabled or not settings.groq_configured:
        return GroqTextResponse(text=fallback, source="fallback", ai_available=False)

    prompt = (
        "Answer the user's question using ONLY the provided import scan context. "
        "If unknown, say you only know what the scanner found. Keep answer under 120 words.\n"
        f"CONTEXT: {json.dumps(context)}\nQUESTION: {question}"
    )
    text = await _chat(settings, prompt)
    if not text:
        return GroqTextResponse(text=fallback, source="fallback", ai_available=False)
    return GroqTextResponse(text=text.strip(), source="groq", ai_available=True)


async def _chat(settings: Settings, prompt: str) -> str | None:
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.groq_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You explain Databricks file-import conversion risks. "
                    "Never change counts, types, or invent findings."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{settings.groq_base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            if resp.status_code >= 400:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None
