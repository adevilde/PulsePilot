from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .data.personas import CONTEXT_OPTIONS, get_persona, list_personas
from .schemas import DatasetImportResponse, FeedbackCreate, InsightRequest, InsightResponse
from .services.baseline_service import BaselineScoringService
from .services.dataset_service import DatasetImportService
from .services.feature_pipeline import FeatureEngineeringPipeline
from .services.llm_service import LLMExplanationService

app = FastAPI(title="PulsePilot API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = FeatureEngineeringPipeline()
scoring_service = BaselineScoringService()
dataset_service = DatasetImportService()
explanation_service = LLMExplanationService()
MEMORY = {"corrections": []}
IMPORTED_PERSONAS: dict[str, dict] = {}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/personas")
def personas() -> dict:
    uploaded = [
        {"key": persona["key"], "name": persona["name"], "source": persona.get("source", "demo")}
        for persona in IMPORTED_PERSONAS.values()
    ]
    return {"personas": list_personas() + uploaded, "contextOptions": CONTEXT_OPTIONS}


@app.get("/api/memory")
def memory() -> dict:
    return MEMORY


@app.post("/api/datasets/upload", response_model=DatasetImportResponse)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetImportResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    content = await file.read()
    try:
        imported = dataset_service.import_csv(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for profile in imported["profiles"]:
        IMPORTED_PERSONAS[profile["key"]] = profile
    return DatasetImportResponse(**imported)


@app.post("/api/feedback")
def add_feedback(payload: FeedbackCreate) -> dict:
    entry = payload.model_dump()
    entry["createdAt"] = datetime.now(timezone.utc).isoformat()
    MEMORY["corrections"].append(entry)
    return {"ok": True, "entry": entry, "memory": MEMORY}


@app.post("/api/insight/{persona_key}", response_model=InsightResponse)
async def insight(persona_key: str, payload: InsightRequest) -> InsightResponse:
    try:
        persona = IMPORTED_PERSONAS.get(persona_key) or get_persona(persona_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Persona not found") from exc

    feature_output = pipeline.run(persona["timeline"])
    scored_insight = scoring_service.score(feature_output, persona_key, MEMORY)
    explanation = await explanation_service.explain(persona, scored_insight, payload.contextTags)
    return InsightResponse(
        persona=persona,
        scoredInsight=scored_insight,
        explanation=explanation,
        memory=MEMORY,
    )
