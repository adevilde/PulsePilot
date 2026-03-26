# PulsePilot

PulsePilot is a preventive health application that turns wearable data into actionable insights.

It analyzes signals such as heart rate, heart rate variability (HRV), sleep, activity, and strain, compares them to a personal baseline, and highlights meaningful changes with clear explanations and recommended actions.

![PulsePilot Demo](./assets/demo.gif)

## Features

- Upload wearable data as CSV
- Automatic data normalization
- Personal baseline computation with rolling windows
- Detection of deviations and trend changes
- Insight generation for recovery, stress, and possible illness patterns
- Actionable daily recommendations
- Local AI explanations with llama.cpp
- User feedback loop to refine future interpretations

## Project structure

```text
PulsePilot/
├── backend/
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── data/
│       ├── schemas.py
│       └── services/
│           ├── baseline_service.py
│           ├── dataset_service.py
│           ├── feature_pipeline.py
│           ├── llm_service.py
│           └── utils.py
└── frontend/
    ├── package.json
    └── src/
```

## Setup

### Backend with uv

Install `uv`:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

Install backend dependencies:

```bash
cd backend
uv sync
```

Run the API:

```bash
uv run uvicorn app.main:app --reload --reload-dir app
```

The backend will be available at `http://localhost:8000`.

### Frontend with React

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Local AI with llama.cpp

PulsePilot can generate explanation text with a local model served by `llama.cpp`.

### 1. Install llama.cpp

Clone and build with CMake:

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build
cmake --build build --config Release -j 8
```

If CMake is not installed:

```bash
brew install cmake
```


### 2. Download a GGUF model

A good default is Mistral 7B Instruct in GGUF format:

- `https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF`

Download one `.gguf` file such as `Q4_K_M.gguf`.

### 3. Start the local server

```bash
./build/bin/llama-server -m /absolute/path/to/your-model.gguf --host 127.0.0.1 --port 8080
```

### 4. Backend connection

The backend connects by default to:

```text
http://127.0.0.1:8080/v1/chat/completions
```

Optional environment variables:

```bash
export LLM_BASE_URL=http://127.0.0.1:8080
export LLM_CHAT_PATH=/v1/chat/completions
export LLM_MODEL=local-mistral-7b
```

If the local model is unavailable, PulsePilot falls back to deterministic explanations.

## Dataset

Recommended dataset:

- `https://www.kaggle.com/datasets/mftnakrsu/health-wearables-stresssleep-tracking-syntc`

This dataset contains daily health tracking data such as:

- heart rate
- heart rate variability (HRV)
- sleep metrics
- stress-related indicators

### How to use the dataset

1. Download the dataset as CSV from Kaggle
2. Start the backend and frontend
3. Upload the CSV through the app interface
4. Select an imported profile and generate insights

## Supported data fields

The upload pipeline automatically maps common column names such as:

- `date`, `timestamp`
- `hr`, `heart_rate`, `resting_hr`
- `hrv`, `rmssd`
- `sleep_duration`, `sleep_score`, `sleep_quality`
- `steps`, `activity`
- `stress`, `strain`, `strain_score`

If some fields are missing, defaults and imputations are applied so the analysis pipeline can still run.

## API routes

- `GET /api/health`
- `GET /api/personas`
- `GET /api/memory`
- `POST /api/datasets/upload`
- `POST /api/insight/{persona_key}`
- `POST /api/feedback`

## Notes

- The application runs locally
- No external API key is required
- Health data does not need to leave your machine
- PulsePilot does not provide medical diagnosis
