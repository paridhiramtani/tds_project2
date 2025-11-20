from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import base64

app = FastAPI()

@app.get("/quiz-1", response_class=HTMLResponse)
async def quiz_1():
    # A simple task: Sum of two numbers
    html_content = """
    <html>
    <body>
        <div id="task">
            Calculate the sum of 50 and 75.
            Submit your answer to http://localhost:8001/submit
        </div>
    </body>
    </html>
    """
    return html_content

@app.post("/submit")
async def submit(request: Request):
    data = await request.json()
    print(f"Received submission: {data}")
    
    answer = data.get("answer")
    if answer == 125:
        return JSONResponse({
            "correct": True,
            "url": "http://localhost:8001/quiz-2"
        })
    else:
        return JSONResponse({
            "correct": False,
            "reason": "Incorrect sum"
        })

@app.get("/quiz-2", response_class=HTMLResponse)
async def quiz_2():
    # A slightly harder task: Decode base64
    secret = "Success"
    encoded = base64.b64encode(secret.encode()).decode()
    html_content = f"""
    <html>
    <body>
        <div id="task">
            Decode this string: {encoded}
            Submit your answer to http://localhost:8001/submit
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
