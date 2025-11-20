# LLM Analysis Quiz Solver

A high-performance, automated agent to solve data analysis quizzes using FastAPI, Playwright, and LLM-based code execution.

## Features
- **Automated Browser Navigation**: Uses Playwright to navigate and scrape quiz tasks.
- **Intelligent Solver**: Uses GPT-4o-mini (via AIProxy) to generate and execute Python code for any data task.
- **Robust Execution**: Handles concurrent requests, retries, and recursive task chains.
- **Dockerized**: Ready for deployment.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

2.  **Environment Variables**:
    Set your API token in a `.env` file or export it:
    ```bash
    export AIPROXY_TOKEN=your_token_here
    # OR
    export OPENAI_API_KEY=your_key_here
    ```

3.  **Run the Application**:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

## Docker Usage

```bash
docker build -t quiz-solver .
docker run -p 8000:8000 -e AIPROXY_TOKEN=your_token quiz-solver
```

## API Endpoint

**POST /run**
```json
{
  "email": "student@example.com",
  "secret": "your_secret",
  "url": "https://example.com/quiz-start"
}
```

## Project Structure
- `main.py`: Entry point and orchestration loop.
- `core/browser.py`: Playwright scraper.
- `core/solver.py`: LLM agent and code executor.
- `core/submitter.py`: API submission handler.
- `prompts/`: System and User prompts for the contest.
