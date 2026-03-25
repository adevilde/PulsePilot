from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .utils import linear_slope, mean, pct_change, stddev


@dataclass(slots=True)
class MetricFeature:
    metric: str
    baseline_mean: float
    current_mean: float
    baseline_std: float
    change_pct: float
    slope: float
    latest: float
    recent_min: float
    recent_max: float

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "metric": self.metric,
            "baselineMean": round(self.baseline_mean, 3),
            "currentMean": round(self.current_mean, 3),
            "baselineStd": round(self.baseline_std, 3),
            "changePct": round(self.change_pct, 3),
            "slope": round(self.slope, 6),
            "latest": round(self.latest, 3),
            "recentMin": round(self.recent_min, 3),
            "recentMax": round(self.recent_max, 3),
        }


class FeatureEngineeringPipeline:
    def __init__(self, baseline_days: int = 21, current_days: int = 7) -> None:
        self.baseline_days = baseline_days
        self.current_days = current_days

    def run(self, timeline: List[dict[str, Any]]) -> dict[str, Any]:
        prepared_timeline = self._prepare_timeline(timeline)
        if len(prepared_timeline) < max(self.baseline_days, self.current_days):
            raise ValueError(
                f"Need at least {max(self.baseline_days, self.current_days)} daily records."
            )

        baseline = prepared_timeline[: self.baseline_days]
        current = prepared_timeline[-self.current_days :]
        metric_names = [key for key in baseline[0].keys() if key != "date"]

        metrics = {
            metric: self._build_metric_feature(metric, baseline, current).to_dict()
            for metric in metric_names
        }

        composite = self._build_composite_signals(metrics)

        return {
            "baselineWindow": [day["date"] for day in baseline],
            "currentWindow": [day["date"] for day in current],
            "metrics": metrics,
            "composite": composite,
        }

    def _prepare_timeline(self, timeline: List[dict[str, Any]]) -> List[dict[str, Any]]:
        prepared = []
        for day in timeline:
            row = {"date": str(day["date"])}
            for key, value in day.items():
                if key == "date":
                    continue
                row[key] = float(value)
            prepared.append(row)
        return sorted(prepared, key=lambda item: item["date"])

    def _build_metric_feature(
        self,
        metric: str,
        baseline: List[dict[str, Any]],
        current: List[dict[str, Any]],
    ) -> MetricFeature:
        baseline_values = [float(day[metric]) for day in baseline]
        current_values = [float(day[metric]) for day in current]

        return MetricFeature(
            metric=metric,
            baseline_mean=mean(baseline_values),
            current_mean=mean(current_values),
            baseline_std=stddev(baseline_values),
            change_pct=pct_change(mean(current_values), mean(baseline_values)),
            slope=linear_slope(current_values),
            latest=current_values[-1],
            recent_min=min(current_values),
            recent_max=max(current_values),
        )

    def _build_composite_signals(self, metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        return {
            "recovery_balance": (
                -metrics["hrv"]["changePct"] * 0.45
                + metrics["resting_hr"]["changePct"] * 0.35
                - metrics["sleep_efficiency"]["changePct"] * 0.20
            ),
            "illness_signature": (
                metrics["resting_hr"]["changePct"] * 0.35
                - metrics["hrv"]["changePct"] * 0.30
                - metrics["steps"]["changePct"] * 0.20
                - metrics["sleep_efficiency"]["changePct"] * 0.15
            ),
            "stress_signature": (
                metrics["resting_hr"]["changePct"] * 0.20
                - metrics["hrv"]["changePct"] * 0.25
                - metrics["sleep_duration"]["changePct"] * 0.20
                - metrics["steps"]["changePct"] * 0.15
                + metrics["strain_score"]["changePct"] * 0.20
            ),
        }
