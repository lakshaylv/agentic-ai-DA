from fastapi import FastAPI, UploadFile, File
import pandas as pd
import io

from backend.models.schemas import AnalyzeRequest
from backend.services.session_service import session_store
from backend.services.llm_service import LLMConfig
from backend.tools.registry import ToolRegistry
from backend.tools.inspection import SchemaInspector, MissingValueAnalyzer
from backend.tools.operations import GroupBy, FilterTool
from backend.agent.orchestrator import run_analysis

registry = ToolRegistry()
registry.register(SchemaInspector())
registry.register(MissingValueAnalyzer())
registry.register(GroupBy())
registry.register(FilterTool())

llm_config = LLMConfig()

app = FastAPI(
    title="AI Data Analyst Agent Backend",
    description="Backend for AI-powered data analysis and visualization.",
    version="0.1.0",
)

@app.get("/health", response_model=dict)
async def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    session_id = session_store.create(df, filename=file.filename or "")
    return {
        "session_id": session_id,
        "row_count": df.shape[0],
        "column_count": df.shape[1],
        "column_names": df.columns.tolist(),
    }

@app.get("/sessions")
async def list_sessions():
    return {"sessions": session_store.list_sessions()}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_store.delete(session_id)
    return {"deleted": deleted}

@app.post("/analyze")
async def analyze_session(req: AnalyzeRequest):
    df = session_store.get(req.session_id)
    if df is None:
        return {"error": f"Session '{req.session_id}' not found"}

    result = run_analysis(
        df=df,
        query=req.query,
        session_id=req.session_id,
        registry=registry,
        llm_config=llm_config,
    )
    return result.model_dump()

# Future backend expansion points:
# @app.include_router(api_router, prefix="/api/v1")
# @app.on_event("startup")
# async def startup_event():
#     # Initialize resources here
#     pass

# @app.on_event("shutdown")
# async def shutdown_event():
#     # Clean up resources here
#     pass
