# AI Data Analyst Agent

A bounded autonomous data analysis agent with a FastAPI backend, tool-calling architecture, and LLM-driven iterative analysis loop. The LLM decides which tools to call — it never directly manipulates data.

## Setup

```bash
python -m venv ai_analyst_env
source ai_analyst_env/bin/activate
pip install -r requirements.txt
```

Create `.env` with your LLM API key:

```
GEMINI_API_KEY=your_key_here
```

## Run

**Backend (FastAPI):**

```bash
uvicorn backend.main:app --reload
```

**Frontend (Streamlit):**

```bash
streamlit run frontend/app.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/upload` | Upload CSV, returns session_id |
| GET | `/sessions` | List active sessions |
| DELETE | `/sessions/{id}` | Delete a session |
| POST | `/analyze` | Run analysis query on a session |

## Architecture

```
User query → Orchestrator (bounded loop, max 10 iters)
                ↓
           LLM decides next tool ←→ ToolRegistry
                ↓
           Tool executes on DataFrame → returns structured response
                ↓
           Orchestrator appends result to conversation history
                ↓
           Repeat until LLM marks complete or max iters reached
```

## Tools

| Tool | Description |
|------|-------------|
| `schema_inspector` | Column names, dtypes, shape |
| `missing_value_analyzer` | Missing value counts and percentages |
| `groupby` | Group + aggregate (sum, mean, count, etc.) |
| `filter` | Filter rows (eq, ne, gt, gte, lt, lte, contains) |

## Tests

```bash
pytest tests/ -v
```
