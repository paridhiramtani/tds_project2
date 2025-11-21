# LLM Quiz Solver Agent

A high-performance, automated agent to solve data analysis quizzes using FastAPI, Playwright, and a Multi-Model Agentic Strategy (Reasoning, Vision, Coding).

## Features
-   **Multi-Model Agents**: Uses specialized agents for Reasoning, Vision (OCR/Charts), and Coding.
-   **Frontend Dashboard**: Professional web UI to run tasks and monitor logs in real-time.
-   **Robust Scraper**: Captures full-page screenshots and handles complex DOMs.
-   **Secure API**: Strict secret verification and input validation.
-   **Task Tracking**: Async background processing with status polling.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

2.  **Environment Variables**:
    Create a `.env` file or export:
    ```bash
    export AIPROXY_TOKEN=your_token
    export USER_SECRET=your_secret_code
    ```

3.  **Run the Application**:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

4.  **Access Dashboard**:
    Open `http://localhost:8000` in your browser.

## Docker Usage

```bash
docker build -t quiz-solver .
docker run -p 8000:8000 -e AIPROXY_TOKEN=your_token -e USER_SECRET=your_secret quiz-solver
```

## API Endpoints

-   `GET /`: Frontend Dashboard
-   `POST /run`: Start a new task (returns `task_id`)
-   `GET /tasks/{task_id}`: Get task status and logs
-   `POST /analyze`: Direct access to the solver agent
-   `GET /health`: Health check

## Project Structure
-   `main.py`: API server and task orchestration.
-   `static/`: Frontend assets.
-   `core/`:
    -   `solver.py`: Multi-agent logic (Reasoning, Vision, Coding).
    -   `browser.py`: Playwright scraper with screenshot support.
    -   `submitter.py`: Submission handler.
-   `prompts/`: Security contest prompts.
