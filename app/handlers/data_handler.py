# app/handlers/data_handler.py
from typing import Dict, Any
from app.handlers.base_handler import BaseHandler
# Import the robust solver from core
from core.solver import solver 

class DataHandler(BaseHandler):
    async def handle(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        question = task_data.get("question")
        context = task_data.get("context", "")
        
        # Combine context and question for the solver
        # We might need to mock the structure expected by core.solver
        input_data = {
            "text": f"{question}\n\nContext:\n{context}",
            "screenshot": None # You might want to pass screenshot if available
        }
        
        # Use the robust solver logic you wrote in core/
        return solver.solve(input_data)
