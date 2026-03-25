from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    persona: str
    feedbackType: str = Field(pattern="^(accurate|not_accurate|context)$")
    tag: str
    note: Optional[str] = None


class InsightRequest(BaseModel):
    contextTags: List[str] = []


class FeedbackEntry(BaseModel):
    persona: str
    feedbackType: str
    tag: str
    note: Optional[str] = None
    createdAt: str


class InsightResponse(BaseModel):
    persona: Dict[str, Any]
    scoredInsight: Dict[str, Any]
    explanation: Dict[str, Any]
    memory: Dict[str, Any]


class DatasetImportResponse(BaseModel):
    datasetName: str
    mapping: Dict[str, Any]
    profiles: List[Dict[str, Any]]
    rowsProcessed: int
