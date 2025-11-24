import subprocess
import sys
import os
import uuid
import json
from typing import Dict, Any
from app.handlers.base_handler import BaseHandler
from app.services.llm_service import llm_client
from app.utils.logger import setup_logger
from app.config import TEMP_DIR

logger = setup_logger(__name__)

class DataHandler(BaseHandler):
    async def handle(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates Python code to solve the task.
        """
        question = task_data.get("question")
        context = task_data.get("context", "")
        
        # 1. Generate Plan & Code
        code = self._generate_code(question, context)
        
        # 2. Execute Code
        result = self._execute_code(code)
        
        # 3. Parse Result
        try:
            return json.loads(result)
        except:
            return {"answer": result, "submit_url": None}

    def _generate_code(self, question: str, context: str) -> str:
        system_prompt = """
        You are a Python expert. Write a script to solve the user's data problem.
        The script MUST print a valid JSON string to stdout: {"answer": <result>, "submit_url": <url>}
        
        Available Helper:
        - The variable 'context' contains the text content.
        - If you need to download a file, use standard libraries (requests/httpx).
        
        Do not use markdown blocks. Just the code.
        """
        user_prompt = f"Question: {question}\nContext: {context}"
        
        code = llm_client.call(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            model="gpt-4o"
        )
        
        # Cleanup
        if code.startswith("```python"):
            code = code.replace("```python", "").replace("```", "")
        elif code.startswith("```"):
            code = code.replace("```", "")
        return code.strip()

    def _execute_code(self, code: str) -> str:
        filename = os.path.join(TEMP_DIR, f"solve_{uuid.uuid4().hex}.py")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            
            logger.info(f"Executing code: {filename}")
            result = subprocess.run(
                [sys.executable, filename],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Execution failed: {result.stderr}")
                raise Exception(f"Code execution failed: {result.stderr}")
                
            return result.stdout.strip()
        finally:
            if os.path.exists(filename):
                os.remove(filename)
