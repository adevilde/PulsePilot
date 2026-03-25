from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx


class LLMExplanationService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        chat_path: str = "/v1/chat/completions",
        model: str = "local-mistral-7b",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or "http://127.0.0.1:8080").rstrip("/")
        self.chat_path = os.getenv("LLM_CHAT_PATH", chat_path)
        self.model = os.getenv("LLM_MODEL", model)
        self.timeout = timeout

    async def explain(self, persona: dict[str, Any], scored_insight: dict[str, Any], context_tags: list[str]) -> dict[str, Any]:
        try:
            return await self._fetch_llama_cpp_explanation(persona, scored_insight, context_tags)
        except Exception:
            return self._fallback_explanation(persona, scored_insight, context_tags)

    async def _fetch_llama_cpp_explanation(
        self,
        persona: dict[str, Any],
        scored_insight: dict[str, Any],
        context_tags: list[str],
    ) -> dict[str, Any]:
        prompt = self._build_prompt(persona, scored_insight, context_tags)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a preventative-health explanation layer. "
                        "Never diagnose. Return only valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}{self.chat_path}", json=payload)
            response.raise_for_status()
            body = response.json()

        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return self._normalize_response(parsed, scored_insight)

    def _build_prompt(self, persona: dict[str, Any], scored_insight: dict[str, Any], context_tags: list[str]) -> str:
        payload = {
            "persona": persona["name"],
            "status": scored_insight["status"],
            "primaryInsight": scored_insight["primaryInsight"],
            "score": round(scored_insight["totalScore"], 1),
            "contextTags": context_tags,
            "topDrivers": [
                {
                    "metric": driver["metric"],
                    "baselineMean": round(driver["baselineMean"], 2),
                    "currentMean": round(driver["currentMean"], 2),
                    "changePct": round(driver["changePct"], 1),
                    "zScore": round(driver["zScore"], 2),
                }
                for driver in scored_insight["topDrivers"]
            ],
            "bucketScores": [
                {"code": bucket["code"], "score": round(bucket["score"], 1)}
                for bucket in scored_insight["buckets"]
            ],
            "feedbackPatterns": scored_insight["adjustments"],
        }
        schema = {
            "status": "monitor|caution|high_attention",
            "primaryInsight": "recovery_decline|possible_illness|stress_load",
            "summary": "short explanation",
            "confidence": 0.0,
            "actions": ["action 1", "action 2"],
            "seekCare": ["condition 1", "condition 2"],
            "notes": ["reasoning note 1", "reasoning note 2"],
        }
        return (
            "Analyze wearable-health features and return JSON only.\n"
            f"Required shape: {json.dumps(schema)}\n"
            "Rules: concise, no diagnosis, focus on actionable advice, only use supplied data.\n"
            f"Input: {json.dumps(payload)}"
        )

    def _normalize_response(self, parsed: Dict[str, Any], scored_insight: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": parsed.get("status", scored_insight["status"]),
            "primaryInsight": parsed.get("primaryInsight", scored_insight["primaryInsight"]),
            "summary": parsed.get("summary", ""),
            "confidence": float(parsed.get("confidence", round(scored_insight["totalScore"] / 100, 2))),
            "actions": parsed.get("actions", []),
            "seekCare": parsed.get("seekCare", []),
            "notes": parsed.get("notes", []),
            "source": "llama.cpp",
        }

    def _fallback_explanation(
        self,
        persona: dict[str, Any],
        scored_insight: dict[str, Any],
        context_tags: list[str],
    ) -> dict[str, Any]:
        top = scored_insight["topDrivers"][:3]
        lines = []
        for driver in top:
            label = persona["labels"][driver["metric"]]
            direction = "up" if driver["changePct"] > 0 else "down"
            lines.append(f"{label} is {direction} {abs(round(driver['changePct'], 1))}% versus baseline")

        summary = f"{scored_insight['primaryLabel']}. " + "; ".join(lines) + "."
        if "alcohol" in context_tags:
            summary += " Recent alcohol intake may partly explain the recovery pattern."
        if "intense_workout" in context_tags:
            summary += " Recent hard training can also contribute to this signal."
        if "symptoms" in context_tags:
            summary += " Because symptoms were reported, illness-related interpretation deserves more attention."

        action_map = {
            "recovery_decline": ["Reduce workout intensity today", "Hydrate well", "Aim for earlier sleep"],
            "possible_illness": ["Prioritize rest", "Hydrate and monitor symptoms", "Avoid intense exercise"],
            "stress_load": ["Reduce cognitive load where possible", "Protect tonight's sleep window", "Take a low-intensity walk break"],
        }
        notes = [
            "Built from a 21-day baseline and 7-day scoring window.",
            "Uses deterministic scoring with a local fallback explanation layer.",
        ]
        if scored_insight["adjustments"]:
            notes.append("Past user feedback adjusted the interpretation weights.")
        return {
            "status": scored_insight["status"],
            "primaryInsight": scored_insight["primaryInsight"],
            "summary": summary,
            "confidence": round(scored_insight["totalScore"] / 100, 2),
            "actions": action_map[scored_insight["primaryInsight"]],
            "seekCare": ["Chest pain, fainting, or shortness of breath", "Symptoms worsening or persisting beyond 48 hours"],
            "notes": notes,
            "source": "fallback",
        }
