from __future__ import annotations

import json
from typing import Optional

import httpx


class MistralExplanationService:
    def __init__(self, endpoint: Optional[str] = None, model: str = "mistral") -> None:
        self.endpoint = endpoint
        self.model = model

    async def explain(self, persona: dict, scored_insight: dict, context_tags: list[str]) -> dict:
        if self.endpoint:
            try:
                return await self._fetch_local_mistral(persona, scored_insight, context_tags)
            except Exception:
                pass
        return self._local_explanation(persona, scored_insight, context_tags)

    async def _fetch_local_mistral(self, persona: dict, scored_insight: dict, context_tags: list[str]) -> dict:
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["monitor", "caution", "high_attention"]},
                "primary_insight": {"type": "string", "enum": ["recovery_decline", "possible_illness", "stress_load"]},
                "summary": {"type": "string"},
                "confidence": {"type": "number"},
                "actions_today": {"type": "array", "items": {"type": "string"}},
                "seek_care_if": {"type": "array", "items": {"type": "string"}},
                "explanation_notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["status", "primary_insight", "summary", "confidence", "actions_today", "seek_care_if", "explanation_notes"],
        }
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
            "bucketScores": [{"code": bucket["code"], "score": round(bucket["score"], 1)} for bucket in scored_insight["buckets"]],
            "feedbackPatterns": scored_insight["adjustments"],
        }
        request_body = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a preventative-health explanation layer. Never diagnose. Return only JSON matching the schema.",
                },
                {"role": "user", "content": json.dumps(payload)},
            ],
            "options": {"temperature": 0.2, "num_predict": 280},
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.endpoint, json=request_body)
            response.raise_for_status()
            data = response.json()
        content = data.get("message", {}).get("content") or data.get("response")
        parsed = json.loads(content or "{}")
        return {
            "status": parsed.get("status", scored_insight["status"]),
            "primaryInsight": parsed.get("primary_insight", scored_insight["primaryInsight"]),
            "summary": parsed.get("summary", ""),
            "confidence": parsed.get("confidence", round(scored_insight["totalScore"] / 100, 2)),
            "actions": parsed.get("actions_today", []),
            "seekCare": parsed.get("seek_care_if", []),
            "notes": parsed.get("explanation_notes", []),
            "source": "mistral",
        }

    def _local_explanation(self, persona: dict, scored_insight: dict, context_tags: list[str]) -> dict:
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
            "Combines deterministic scoring with a local explanation layer.",
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
