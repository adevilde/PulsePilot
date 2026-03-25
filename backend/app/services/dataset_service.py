from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple


def _slug(value: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in value).strip('_')


COLUMN_SYNONYMS = {
    'user_id': ['user_id', 'userid', 'user', 'participant_id', 'subject_id', 'id'],
    'date': ['date', 'day', 'timestamp', 'datetime', 'recorded_at', 'sleep_date'],
    'resting_hr': ['resting_hr', 'restingheart_rate', 'resting_heart_rate', 'heart_rate', 'hr', 'pulse'],
    'hrv': ['hrv', 'rmssd', 'heart_rate_variability'],
    'sleep_duration': ['sleep_duration', 'sleep_hours', 'total_sleep_hours', 'sleep_time', 'sleep_length', 'duration'],
    'sleep_efficiency': ['sleep_efficiency', 'sleep_score', 'sleep_quality', 'efficiency'],
    'steps': ['steps', 'daily_steps', 'step_count', 'stepcount'],
    'strain_score': ['strain_score', 'strain', 'activity_score', 'stress_level', 'stress_score', 'activity_level'],
}

DISPLAY_META = {
    'labels': {
        'resting_hr': 'Resting HR',
        'hrv': 'HRV',
        'sleep_efficiency': 'Sleep efficiency',
        'sleep_duration': 'Sleep duration',
        'steps': 'Steps',
        'strain_score': 'Strain score',
    },
    'units': {
        'resting_hr': 'bpm',
        'hrv': 'ms',
        'sleep_efficiency': '%',
        'sleep_duration': 'h',
        'steps': 'steps',
        'strain_score': 'pts',
    },
}

REQUIRED_METRICS = ['resting_hr', 'hrv', 'sleep_efficiency', 'sleep_duration', 'steps', 'strain_score']


class DatasetImportService:
    def __init__(self, min_days: int = 14, max_profiles: int = 5) -> None:
        self.min_days = min_days
        self.max_profiles = max_profiles

    def import_csv(self, file_bytes: bytes, filename: str) -> dict:
        text = file_bytes.decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError('CSV file has no header row.')

        headers = [_slug(name) for name in reader.fieldnames]
        mapping = self._detect_mapping(headers)
        rows = [self._normalize_row(raw, mapping, headers) for raw in reader]
        rows = [row for row in rows if row is not None]
        if not rows:
            raise ValueError('No usable rows found in the CSV file.')

        profiles = self._build_profiles(rows, filename)
        if not profiles:
            raise ValueError('No profile with enough daily records was found. Aim for at least 14 days of data with date plus a few wearable metrics.')

        return {
            'datasetName': filename,
            'mapping': mapping,
            'profiles': profiles,
            'rowsProcessed': len(rows),
        }

    def _detect_mapping(self, headers: List[str]) -> Dict[str, Optional[str]]:
        mapping: Dict[str, Optional[str]] = {}
        for target, synonyms in COLUMN_SYNONYMS.items():
            found = None
            for synonym in synonyms:
                if synonym in headers:
                    found = synonym
                    break
            mapping[target] = found
        return mapping

    def _normalize_row(self, raw: dict, mapping: Dict[str, Optional[str]], headers: List[str]) -> Optional[dict]:
        by_slug = {_slug(key): value for key, value in raw.items()}
        date_value = self._parse_date(self._get_value(by_slug, mapping['date']))
        if not date_value:
            return None

        user_id = self._get_value(by_slug, mapping['user_id']) or 'default'
        row = {'user_id': str(user_id), 'date': date_value.isoformat()}
        for metric in REQUIRED_METRICS:
            raw_value = self._get_value(by_slug, mapping[metric])
            value = self._parse_number(raw_value)
            if value is not None:
                row[metric] = value
        return row

    def _build_profiles(self, rows: List[dict], filename: str) -> List[dict]:
        grouped: Dict[str, Dict[str, dict]] = defaultdict(dict)
        for row in rows:
            bucket = grouped[row['user_id']]
            day = bucket.setdefault(row['date'], {'date': row['date']})
            for metric in REQUIRED_METRICS:
                if metric in row and row[metric] is not None:
                    day[metric] = row[metric]

        profiles = []
        for user_id, by_day in list(grouped.items())[: self.max_profiles * 3]:
            timeline = sorted(by_day.values(), key=lambda item: item['date'])
            timeline = self._densify_and_impute(timeline)
            if len(timeline) < self.min_days:
                continue
            key = f"upload_{_slug(filename.rsplit('.', 1)[0])}_{_slug(user_id)}"
            profiles.append({
                'key': key,
                'name': f'Imported profile {user_id}',
                'timeline': timeline,
                'labels': deepcopy(DISPLAY_META['labels']),
                'units': deepcopy(DISPLAY_META['units']),
                'source': 'uploaded_csv',
            })
            if len(profiles) >= self.max_profiles:
                break
        return profiles

    def _densify_and_impute(self, timeline: List[dict]) -> List[dict]:
        if not timeline:
            return []
        parsed = []
        for row in timeline:
            parsed.append({'date': datetime.fromisoformat(row['date']).date(), **{k: row.get(k) for k in REQUIRED_METRICS}})

        start = parsed[0]['date']
        end = parsed[-1]['date']
        by_date = {row['date']: row for row in parsed}
        series = []
        current = start
        while current <= end:
            row = by_date.get(current, {'date': current, **{metric: None for metric in REQUIRED_METRICS}})
            series.append(row)
            current += timedelta(days=1)

        metric_defaults = self._compute_defaults(series)
        for metric in REQUIRED_METRICS:
            last_value = metric_defaults[metric]
            for row in series:
                value = row.get(metric)
                if value is None:
                    row[metric] = last_value
                else:
                    last_value = value
            next_value = metric_defaults[metric]
            for row in reversed(series):
                value = row.get(metric)
                if value is None:
                    row[metric] = next_value
                else:
                    next_value = value
            for row in series:
                if row.get(metric) is None:
                    row[metric] = metric_defaults[metric]

        for row in series:
            row['sleep_efficiency'] = self._normalize_sleep_efficiency(row['sleep_efficiency'])
            row['sleep_duration'] = self._normalize_sleep_duration(row['sleep_duration'])
            row['steps'] = max(0.0, float(row['steps']))
            row['strain_score'] = self._normalize_strain(row['strain_score'], row['steps'])
            row['resting_hr'] = float(row['resting_hr'])
            row['hrv'] = max(1.0, float(row['hrv']))

        return [
            {
                'date': row['date'].isoformat(),
                'resting_hr': round(row['resting_hr'], 2),
                'hrv': round(row['hrv'], 2),
                'sleep_efficiency': round(row['sleep_efficiency'], 2),
                'sleep_duration': round(row['sleep_duration'], 2),
                'steps': round(row['steps'], 2),
                'strain_score': round(row['strain_score'], 2),
            }
            for row in series
        ]

    def _compute_defaults(self, series: List[dict]) -> Dict[str, float]:
        defaults = {}
        for metric in REQUIRED_METRICS:
            values = [float(row[metric]) for row in series if row.get(metric) is not None]
            if values:
                defaults[metric] = sum(values) / len(values)
            else:
                defaults[metric] = {
                    'resting_hr': 58.0,
                    'hrv': 52.0,
                    'sleep_efficiency': 84.0,
                    'sleep_duration': 7.1,
                    'steps': 7500.0,
                    'strain_score': 50.0,
                }[metric]
        return defaults

    def _normalize_sleep_efficiency(self, value: float) -> float:
        value = float(value)
        if value <= 10:
            value *= 10
        return min(100.0, max(50.0, value))

    def _normalize_sleep_duration(self, value: float) -> float:
        value = float(value)
        if value > 24:
            value = value / 60.0
        return min(12.0, max(2.0, value))

    def _normalize_strain(self, value: float, steps: float) -> float:
        value = float(value)
        if value <= 10:
            value *= 10
        if value <= 0:
            value = min(100.0, max(0.0, steps / 150.0))
        return min(100.0, max(0.0, value))

    def _get_value(self, row: dict, key: Optional[str]) -> Optional[str]:
        if not key:
            return None
        return row.get(key)

    def _parse_number(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip().replace(',', '.')
        if not text or text.lower() in {'na', 'nan', 'null', 'none'}:
            return None
        filtered = ''.join(ch for ch in text if ch.isdigit() or ch in '.-')
        if not filtered or filtered in {'-', '.', '-.'}:
            return None
        try:
            return float(filtered)
        except ValueError:
            return None

    def _parse_date(self, value: Optional[str]):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00')).date()
        except ValueError:
            return None
