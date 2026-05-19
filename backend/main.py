from fastapi import FastAPI, UploadFile, File
import pandas as pd
import io

from backend.services.session_service import session_store

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
