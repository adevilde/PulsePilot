from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .utils import clamp, classify_status


@dataclass(slots=True)
class BucketScore:
    code: str
    label: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "label": self.label, "score": round(self.score, 3)}


class BaselineScoringService:
    def __init__(self) -> None:
        self.metric_directions = {
            "resting_hr": "higher_worse",
            "hrv": "lower_worse",
            "sleep_efficiency": "lower_worse",
            "sleep_duration": "lower_worse",
            "steps": "lower_worse",
            "strain_score": "higher_worse",
        }

    def score(self, feature_output: dict[str, Any], persona_key: str, memory: dict[str, Any]) -> dict[str, Any]:
        adjustments = self.get_feedback_adjustments(persona_key, memory)
        metric_scores = self._build_metric_scores(feature_output)

        recovery_score = self._weighted_bucket(
            metric_scores,
            {"resting_hr": 0.32, "hrv": 0.34, "sleep_efficiency": 0.20, "sleep_duration": 0.14},
        )
        illness_score = self._weighted_bucket(
            metric_scores,
            {"resting_hr": 0.28, "hrv": 0.24, "sleep_efficiency": 0.14, "steps": 0.20, "sleep_duration": 0.14},
        ) + feature_output["composite"]["illness_signature"] * 0.8
        stress_score = self._weighted_bucket(
            metric_scores,
            {"hrv": 0.24, "sleep_duration": 0.18, "sleep_efficiency": 0.16, "steps": 0.12, "strain_score": 0.20, "resting_hr": 0.10},
        ) + feature_output["composite"]["stress_signature"] * 0.8

        recovery_score += adjustments.get("intense_workout", 0) * 4
        recovery_score += adjustments.get("alcohol", 0) * 1.5
        illness_score += adjustments.get("symptoms", 0) * 5
        illness_score -= adjustments.get("alcohol", 0) * 3
        illness_score -= adjustments.get("intense_workout", 0) * 2
        stress_score += adjustments.get("high_workload", 0) * 4
        stress_score += adjustments.get("travel", 0) * 1.5

        buckets = sorted(
            [
                BucketScore("recovery_decline", "Recovery trending down", recovery_score),
                BucketScore("possible_illness", "Possible early illness pattern", illness_score),
                BucketScore("stress_load", "Stress load rising", stress_score),
            ],
            key=lambda item: item.score,
            reverse=True,
        )
        primary = buckets[0]
        average_metric_severity = sum(item["severity"] for item in metric_scores) / len(metric_scores)
        total_score = clamp((primary.score + average_metric_severity) / 1.4, 0, 100)

        return {
            "status": classify_status(total_score),
            "totalScore": round(total_score, 3),
            "primaryInsight": primary.code,
            "primaryLabel": primary.label,
            "buckets": [bucket.to_dict() for bucket in buckets],
            "adjustments": adjustments,
            "topDrivers": sorted(metric_scores, key=lambda item: item["severity"], reverse=True)[:4],
            "metrics": metric_scores,
            "featureOutput": feature_output,
        }

    def _build_metric_scores(self, feature_output: dict[str, Any]) -> List[dict[str, Any]]:
        metric_scores: List[dict[str, Any]] = []
        for feature in feature_output["metrics"].values():
            directional_delta = self._apply_direction(feature["metric"], feature["changePct"])
            baseline_std = feature.get("baselineStd", 0.0)
            z_score = (
                (feature["currentMean"] - feature["baselineMean"]) / baseline_std
                if baseline_std > 0.001
                else directional_delta / 5
            )
            severity = clamp((abs(z_score) / 3) * 100, 0, 100)
            metric_scores.append(
                {
                    **feature,
                    "directionalDelta": round(directional_delta, 3),
                    "zScore": round(z_score, 3),
                    "severity": round(severity, 3),
                }
            )
        return metric_scores

    def _apply_direction(self, metric: str, change_pct: float) -> float:
        return -change_pct if self.metric_directions[metric] == "lower_worse" else change_pct

    def _weighted_bucket(self, metric_scores: List[dict[str, Any]], metric_weights: Dict[str, float]) -> float:
        score_by_metric = {item["metric"]: item for item in metric_scores}
        return sum(score_by_metric.get(metric, {}).get("severity", 0.0) * weight for metric, weight in metric_weights.items())

    def get_feedback_adjustments(self, persona_key: str, memory: dict[str, Any]) -> dict[str, int]:
        result: Dict[str, int] = {}
        for item in memory.get("corrections", []):
            if item.get("persona") != persona_key:
                continue
            tag = item.get("tag")
            if not tag:
                continue
            result[tag] = result.get(tag, 0) + 1
        return result
