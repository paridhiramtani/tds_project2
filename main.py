from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
import uvicorn
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.browser import scraper
from core.solver import solver
from core.submitter import submit_result
from config import HOST, PORT

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ... (imports remain same)

app = FastAPI(
    title="LLM Quiz Solver API",
    description="Professional Agentic API for solving data quizzes.",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory storage for task status (Use Redis/DB in production)
TASKS: Dict[str, Dict[str, Any]] = {}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/tasks")
async def list_tasks():
    return TASKS

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return JSONResponse(status_code=204)

# --- Models ---

class RunRequest(BaseModel):
    email: str = Field(..., description="Student email ID")
    secret: str = Field(..., description="Student-provided secret")
    url: str = Field(..., description="A unique task URL")

class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Text content of the task")
    screenshot: Optional[str] = Field(None, description="Base64 encoded screenshot")
    model: str = "gpt-4o"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str

# --- Core Logic ---

async def process_task(task_id: str, email: str, secret: str, initial_url: str):
    """
    Main loop: Scrape -> Solve -> Submit -> Repeat if needed.
    Updates global TASKS state.
    """
    TASKS[task_id]["status"] = "processing"
    TASKS[task_id]["logs"].append(f"Started processing {initial_url}")
    
    # Global timeout enforcement
    start_time = datetime.utcnow()
    
    # Safety break to prevent infinite loops
    current_url = initial_url
    for step_idx in range(10): 
        # Check global timeout
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed > 160: # Leave 20s buffer
            msg = f"Global timeout approaching ({elapsed}s). Stopping."
            logger.warning(msg)
            TASKS[task_id]["logs"].append(msg)
            TASKS[task_id]["status"] = "timeout"
            break

        try:
            logger.info(f"[{task_id}] Processing URL: {current_url}")
            TASKS[task_id]["logs"].append(f"Step {step_idx+1}: Navigating to {current_url}")
            
            # 1. Scrape the task
            try:
                task_data = await scraper.get_task_from_url(current_url)
                TASKS[task_id]["logs"].append(f"Scraped content (text_len={len(task_data.get('text', ''))})")
            except Exception as e:
                msg = f"Scraping failed: {e}"
                logger.error(msg)
                TASKS[task_id]["logs"].append(msg)
                TASKS[task_id]["status"] = "failed"
                TASKS[task_id]["error"] = msg
                return

            # 2. Solve the task (with retries and model escalation)
            max_retries = 3
            feedback = None
            
            for attempt in range(max_retries):
                model = "gpt-4o" # Always use best model
                
                logger.info(f"[{task_id}] Solving (attempt {attempt+1}/{max_retries})")
                TASKS[task_id]["logs"].append(f"Solving attempt {attempt+1} with {model}")
                
                result = solver.solve(task_data, feedback, model=model)
                
                if not isinstance(result, dict) or "answer" not in result or "submit_url" not in result:
                    msg = f"Invalid solver result: {result}"
                    logger.error(msg)
                    TASKS[task_id]["logs"].append(msg)
                    feedback = f"Invalid JSON format. Output: {result}. Fix format."
                    continue
                    
                answer = result["answer"]
                submit_url = result["submit_url"]
                TASKS[task_id]["logs"].append(f"Generated answer: {answer}")
                
                # 3. Submit
                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer
                }
                
                try:
                    submission_response = await submit_result(submit_url, payload)
                    logger.info(f"[{task_id}] Submission response: {submission_response}")
                    TASKS[task_id]["logs"].append(f"Submission result: {submission_response}")
                except Exception as e:
                    msg = f"Submission failed: {e}"
                    logger.error(msg)
                    TASKS[task_id]["logs"].append(msg)
                    # If submission fails (network), maybe retry? For now, treat as error in logic
                    feedback = f"Submission failed: {e}"
                    continue

                # 4. Handle Response
                if submission_response.get("correct", False):
                    TASKS[task_id]["logs"].append("Answer Correct!")
                    next_url = submission_response.get("url")
                    if next_url:
                        current_url = next_url
                        TASKS[task_id]["logs"].append(f"Next URL found: {next_url}")
                        break # Break retry loop, continue outer loop
                    else:
                        TASKS[task_id]["status"] = "completed"
                        TASKS[task_id]["logs"].append("Quiz Completed Successfully.")
                        TASKS[task_id]["result"] = "Success"
                        return # Exit function
                else:
                    reason = submission_response.get("reason", "Unknown error")
                    TASKS[task_id]["logs"].append(f"Answer Incorrect: {reason}")
                    feedback = f"Incorrect. Server said: {reason}"
                    # Continue retry loop
            
            else:
                # Exhausted retries
                msg = f"Failed to solve task at {current_url} after {max_retries} attempts."
                logger.error(msg)
                TASKS[task_id]["status"] = "failed"
                TASKS[task_id]["error"] = msg
                TASKS[task_id]["logs"].append(msg)
                break

        except Exception as e:
            logger.error(f"[{task_id}] Error in process loop: {e}")
            TASKS[task_id]["status"] = "error"
            TASKS[task_id]["error"] = str(e)
            break

# --- Endpoints ---

@app.post("/run", response_model=TaskResponse)
async def run_quiz(request: RunRequest, background_tasks: BackgroundTasks):
    # Verify secret
    user_secret = os.getenv("USER_SECRET", "default_secret")
    if request.secret != user_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret")
    
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "logs": [],
        "result": None,
        "error": None
    }
    
    # Start processing in background
    background_tasks.add_task(process_task, task_id, request.email, request.secret, request.url)
    
    return {
        "task_id": task_id,
        "status": "queued",
        "created_at": TASKS[task_id]["created_at"]
    }

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id]

@app.post("/analyze")
async def analyze_task_direct(request: AnalyzeRequest):
    """
    Directly access the solver agent. Useful for debugging or standalone usage.
    """
    try:
        task_data = {"text": request.text, "screenshot": request.screenshot}
        result = solver.solve(task_data, model=request.model)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    await scraper.start()

@app.on_event("shutdown")
async def shutdown():
    await scraper.stop()

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
