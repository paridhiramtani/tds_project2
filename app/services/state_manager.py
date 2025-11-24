from typing import Dict, Any, List
from datetime import datetime
import uuid

class StateManager:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, email: str, initial_url: str) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "id": task_id,
            "email": email,
            "current_url": initial_url,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "logs": [],
            "history": []
        }
        return task_id

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: str, error: str = None):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status
            if error:
                self._tasks[task_id]["error"] = error

    def log(self, task_id: str, message: str):
        if task_id in self._tasks:
            entry = f"[{datetime.utcnow().isoformat()}] {message}"
            self._tasks[task_id]["logs"].append(entry)

    def add_history(self, task_id: str, url: str, action: str, result: str):
        if task_id in self._tasks:
            self._tasks[task_id]["history"].append({
                "url": url,
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })

state_manager = StateManager()

