from fastapi import FastAPI, UploadFile, File
import pandas as pd
import io

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
    
    return {
        "row_count": df.shape[0],
        "column_count": df.shape[1],
        "column_names": df.columns.tolist()
    }

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
