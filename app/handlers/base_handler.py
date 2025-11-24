from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseHandler(ABC):
    @abstractmethod
    async def handle(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the task and return the answer.
        Returns: {"answer": ..., "submit_url": ...}
        """
        pass
