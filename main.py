from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging
import uvicorn
from core.browser import scraper
from core.solver import solver
from core.submitter import submit_result
from config import HOST, PORT

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

class RunRequest(BaseModel):
    email: str
    secret: str
    url: str

async def process_task(email: str, secret: str, initial_url: str):
    """
    Main loop: Scrape -> Solve -> Submit -> Repeat if needed.
    """
    current_url = initial_url
    
    # Safety break to prevent infinite loops
    for _ in range(10): 
        try:
            logger.info(f"Processing URL: {current_url}")
            
            # 1. Scrape the task
            task_content = await scraper.get_task_from_url(current_url)
            logger.info(f"Task content extracted (len={len(task_content)})")
            
            # 2. Solve the task (with retries and model escalation)
            max_retries = 3
            feedback = None
            
            for attempt in range(max_retries):
                # Escalation strategy: Use gpt-4o-mini for first attempt, then gpt-4o for retries
                model = "gpt-4o-mini" if attempt == 0 else "gpt-4o"
                
                logger.info(f"Solving task (attempt {attempt+1}/{max_retries}) using {model}...")
                result = solver.solve(task_content, feedback, model=model)
                logger.info(f"Solver result: {result}")
                
                if not isinstance(result, dict) or "answer" not in result or "submit_url" not in result:
                    logger.error(f"Invalid solver result format: {result}")
                    feedback = "Your previous output was not valid JSON with 'answer' and 'submit_url'. Please fix the format."
                    continue
                    
                answer = result["answer"]
                submit_url = result["submit_url"]
                
                # 3. Submit
                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer
                }
                
                submission_response = await submit_result(submit_url, payload)
                logger.info(f"Submission response: {submission_response}")
                
                # 4. Handle Response
                if submission_response.get("correct", False):
                    logger.info("Answer correct!")
                    next_url = submission_response.get("url")
                    if next_url:
                        current_url = next_url
                        logger.info(f"Moving to next task: {next_url}")
                        # Break the retry loop to go to the outer loop for the next URL
                        break 
                    else:
                        logger.info("Quiz completed successfully.")
                        return # Exit the entire process_task
                else:
                    reason = submission_response.get("reason", "Unknown error")
                    logger.warning(f"Answer incorrect: {reason}")
                    feedback = f"The answer was incorrect. Server response: {reason}. Please try a different approach."
                    # Continue to next retry attempt
            
            else:
                # If we exhausted retries without success
                logger.error(f"Failed to solve task at {current_url} after {max_retries} attempts.")
                break
            
            # If we broke out of the retry loop because of success (and there is a next_url), 
            # the outer loop will continue to the next URL.
            pass

        except Exception as e:
            logger.error(f"Error in process loop: {e}")
            break
        except Exception as e:
            logger.error(f"Error in process loop: {e}")
            break

@app.post("/run")
async def run_quiz(request: RunRequest, background_tasks: BackgroundTasks):
    # Verify secret (simple check, real verification might need DB or env)
    # For this project, we just accept and use it.
    
    # Start processing in background
    background_tasks.add_task(process_task, request.email, request.secret, request.url)
    
    return {"message": "Task started", "status": "processing"}

@app.on_event("startup")
async def startup():
    await scraper.start()

@app.on_event("shutdown")
async def shutdown():
    await scraper.stop()

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
