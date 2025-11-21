from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import base64

app = FastAPI()

@app.get("/quiz-1", response_class=HTMLResponse)
async def quiz_1():
    # The complex sample provided by the user
    # It uses atob to decode a string which contains the task
    # The decoded string is:
    # Q834. Download <a href="http://localhost:8001/data.csv">file</a>.
    # What is the sum of the "value" column?
    # Post your answer to http://localhost:8001/submit with this JSON payload: ...
    
    # Let's construct a similar base64 string but pointing to our local server
    # Task: "Calculate the sum of 100 and 200. Submit to http://localhost:8001/submit"
    # JSON: {"answer": 300}
    
    task_text = """
    Q1. Calculate the sum of 100 and 200.
    Post your answer to http://localhost:8001/submit with this JSON payload:
    {
        "email": "test@example.com",
        "secret": "test",
        "url": "http://localhost:8001/quiz-1",
        "answer": 300
    }
    """
    encoded = base64.b64encode(task_text.encode()).decode()
    
    html_content = f"""
    <html>
    <body>
        <div id="result"></div>
        <script>
          document.querySelector("#result").innerHTML = atob("{encoded}");
        </script>
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
