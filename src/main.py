from fastapi import FastAPI, HTTPException
from schemas import ResolveRequest, JobSourceResult
from pipeline import resolve
app = FastAPI(title="AI Job Source Agent", version="0.1.0")
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/resolve", response_model = JobSourceResult)
async def resolve_endpoint(req: ResolveRequest) -> JobSourceResult:
    try:
        return await resolve(req.linkedin_url)
    except Exception as e:
         raise HTTPException(status_code=502, detail=f"Pipeline failed: {e}")

    
    
    