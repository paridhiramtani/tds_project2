from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.orchestrator import orchestrator
from app.config import HOST, PORT
import uvicorn
import os

app = FastAPI(title="TDS Project 2 - Advanced Solver")

class RunRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/run")
async def run_task(request: RunRequest, background_tasks: BackgroundTasks):
    # Validate secret
    if request.secret != os.getenv("USER_SECRET", "default_secret"):
        raise HTTPException(status_code=403, detail="Invalid secret")
        
    background_tasks.add_task(orchestrator.run, request.url, request.email, request.secret)
    return {"status": "started", "message": "Task processing started in background"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
