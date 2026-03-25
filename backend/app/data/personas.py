from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Dict, List

Timeline = List[dict]


def _build_timeline(start: date, daily_rows: List[dict]) -> Timeline:
    timeline = []
    for idx, row in enumerate(daily_rows):
        entry = {"date": (start + timedelta(days=idx)).isoformat()}
        entry.update(row)
        timeline.append(entry)
    return timeline


BASELINE_START = date(2026, 2, 1)


def _series(base: List[dict], tail: List[dict]) -> Timeline:
    return _build_timeline(BASELINE_START, base + tail)


RUNNER_BASE = [
    {"resting_hr": 54 + (i % 3), "hrv": 62 - (i % 4), "sleep_efficiency": 89 - (i % 2), "sleep_duration": 7.8 - ((i + 1) % 2) * 0.2, "steps": 11200 + (i % 5) * 320, "strain_score": 55 + (i % 4) * 3}
    for i in range(21)
]
RUNNER_TAIL = [
    {"resting_hr": 58, "hrv": 56, "sleep_efficiency": 86, "sleep_duration": 7.2, "steps": 10800, "strain_score": 68},
    {"resting_hr": 59, "hrv": 53, "sleep_efficiency": 84, "sleep_duration": 7.0, "steps": 10400, "strain_score": 72},
    {"resting_hr": 60, "hrv": 50, "sleep_efficiency": 83, "sleep_duration": 6.8, "steps": 9800, "strain_score": 76},
    {"resting_hr": 61, "hrv": 48, "sleep_efficiency": 82, "sleep_duration": 6.7, "steps": 9200, "strain_score": 81},
    {"resting_hr": 62, "hrv": 46, "sleep_efficiency": 81, "sleep_duration": 6.5, "steps": 8900, "strain_score": 84},
    {"resting_hr": 62, "hrv": 45, "sleep_efficiency": 80, "sleep_duration": 6.4, "steps": 8600, "strain_score": 86},
    {"resting_hr": 63, "hrv": 44, "sleep_efficiency": 79, "sleep_duration": 6.3, "steps": 8400, "strain_score": 87},
]

CONSULTANT_BASE = [
    {"resting_hr": 58 + (i % 2), "hrv": 55 - (i % 3), "sleep_efficiency": 88 - (i % 2), "sleep_duration": 7.4 - (i % 2) * 0.1, "steps": 8400 + (i % 4) * 260, "strain_score": 44 + (i % 3) * 2}
    for i in range(21)
]
CONSULTANT_TAIL = [
    {"resting_hr": 60, "hrv": 52, "sleep_efficiency": 86, "sleep_duration": 7.0, "steps": 7800, "strain_score": 49},
    {"resting_hr": 61, "hrv": 50, "sleep_efficiency": 84, "sleep_duration": 6.8, "steps": 7600, "strain_score": 54},
    {"resting_hr": 62, "hrv": 47, "sleep_efficiency": 82, "sleep_duration": 6.5, "steps": 7100, "strain_score": 58},
    {"resting_hr": 63, "hrv": 45, "sleep_efficiency": 80, "sleep_duration": 6.3, "steps": 6700, "strain_score": 63},
    {"resting_hr": 63, "hrv": 44, "sleep_efficiency": 79, "sleep_duration": 6.2, "steps": 6400, "strain_score": 66},
    {"resting_hr": 64, "hrv": 42, "sleep_efficiency": 78, "sleep_duration": 6.0, "steps": 6200, "strain_score": 69},
    {"resting_hr": 64, "hrv": 41, "sleep_efficiency": 77, "sleep_duration": 5.9, "steps": 5900, "strain_score": 72},
]

ILLNESS_BASE = [
    {"resting_hr": 56 + (i % 2), "hrv": 59 - (i % 3), "sleep_efficiency": 88 - (i % 2), "sleep_duration": 7.6 - (i % 2) * 0.1, "steps": 9800 + (i % 5) * 250, "strain_score": 48 + (i % 2) * 2}
    for i in range(21)
]
ILLNESS_TAIL = [
    {"resting_hr": 58, "hrv": 54, "sleep_efficiency": 85, "sleep_duration": 7.2, "steps": 8700, "strain_score": 50},
    {"resting_hr": 60, "hrv": 51, "sleep_efficiency": 83, "sleep_duration": 7.0, "steps": 7600, "strain_score": 49},
    {"resting_hr": 62, "hrv": 47, "sleep_efficiency": 81, "sleep_duration": 6.8, "steps": 6500, "strain_score": 46},
    {"resting_hr": 64, "hrv": 43, "sleep_efficiency": 79, "sleep_duration": 6.7, "steps": 5200, "strain_score": 42},
    {"resting_hr": 65, "hrv": 40, "sleep_efficiency": 77, "sleep_duration": 6.5, "steps": 4300, "strain_score": 38},
    {"resting_hr": 66, "hrv": 38, "sleep_efficiency": 76, "sleep_duration": 6.2, "steps": 3600, "strain_score": 35},
    {"resting_hr": 67, "hrv": 36, "sleep_efficiency": 75, "sleep_duration": 6.0, "steps": 3000, "strain_score": 31},
]

PERSONAS: Dict[str, dict] = {
    "runner": {
        "key": "runner",
        "name": "Overtrained runner",
        "timeline": _series(RUNNER_BASE, RUNNER_TAIL),
        "labels": {
            "resting_hr": "Resting HR",
            "hrv": "HRV",
            "sleep_efficiency": "Sleep efficiency",
            "sleep_duration": "Sleep duration",
            "steps": "Steps",
            "strain_score": "Strain score",
        },
        "units": {
            "resting_hr": "bpm",
            "hrv": "ms",
            "sleep_efficiency": "%",
            "sleep_duration": "h",
            "steps": "steps",
            "strain_score": "pts",
        },
    },
    "consultant": {
        "key": "consultant",
        "name": "High-stress consultant",
        "timeline": _series(CONSULTANT_BASE, CONSULTANT_TAIL),
        "labels": {
            "resting_hr": "Resting HR",
            "hrv": "HRV",
            "sleep_efficiency": "Sleep efficiency",
            "sleep_duration": "Sleep duration",
            "steps": "Steps",
            "strain_score": "Strain score",
        },
        "units": {
            "resting_hr": "bpm",
            "hrv": "ms",
            "sleep_efficiency": "%",
            "sleep_duration": "h",
            "steps": "steps",
            "strain_score": "pts",
        },
    },
    "illness": {
        "key": "illness",
        "name": "Possible illness onset",
        "timeline": _series(ILLNESS_BASE, ILLNESS_TAIL),
        "labels": {
            "resting_hr": "Resting HR",
            "hrv": "HRV",
            "sleep_efficiency": "Sleep efficiency",
            "sleep_duration": "Sleep duration",
            "steps": "Steps",
            "strain_score": "Strain score",
        },
        "units": {
            "resting_hr": "bpm",
            "hrv": "ms",
            "sleep_efficiency": "%",
            "sleep_duration": "h",
            "steps": "steps",
            "strain_score": "pts",
        },
    },
}

CONTEXT_OPTIONS = [
    {"value": "intense_workout", "label": "Intense workout"},
    {"value": "alcohol", "label": "Alcohol"},
    {"value": "travel", "label": "Travel"},
    {"value": "high_workload", "label": "High workload"},
    {"value": "symptoms", "label": "Symptoms"},
    {"value": "poor_sleep", "label": "Poor sleep"},
    {"value": "nothing_unusual", "label": "Nothing unusual"},
]


def get_persona(key: str) -> dict:
    if key not in PERSONAS:
        raise KeyError(key)
    return deepcopy(PERSONAS[key])


def list_personas() -> List[dict]:
    return [
        {"key": persona["key"], "name": persona["name"]}
        for persona in PERSONAS.values()
    ]
