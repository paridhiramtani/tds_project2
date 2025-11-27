import subprocess
import sys
import os
import uuid
import json
import re
from typing import Dict, Any, Optional
from app.handlers.base_handler import BaseHandler
from app.services.llm_service import llm_client
from app.utils.logger import setup_logger
from app.config import TEMP_DIR

logger = setup_logger(__name__)

class DataHandler(BaseHandler):
    async def handle(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Analyzes the task (Reasoning).
        2. Generates Python code to solve it (Coding).
        3. Executes code and parses the messy output (Robust Parsing).
        """
        context = task_data.get("context", "")
        # If we have a screenshot, we would pass it here, but let's focus on the text/code flow first.
        
        # --- Step 1: Reasoning & Code Generation ---
        code = self._generate_robust_code(context)
        
        # --- Step 2: Execution ---
        execution_output = self._execute_code(code)
        
        # --- Step 3: Robust Parsing (The Fix for Point 3) ---
        result_json = self._extract_json_from_output(execution_output)
        
        if not result_json:
            logger.error(f"Failed to extract JSON from output: {execution_output}")
            return {"answer": None, "error": "Could not parse solver output"}

        return result_json

    def _generate_robust_code(self, context: str) -> str:
        """
        Generates a script that includes the context variable directly.
        """
        # We escape the context to prevent syntax errors in the generated Python file
        safe_context = context.replace('"""', "'''")
        
        system_prompt = """
You are an expert Python Data Analyst.
Goal: Write a Python script to solve the user's question found in the 'context'.
Output: Return ONLY valid Python code. No markdown.

Requirements:
1. You must parse the 'context' text provided in the variable.
2. If the context contains a URL to a CSV/Excel/PDF, use `requests` to download it.
3. Use pandas, numpy, or beautifulsoup4 as needed.
4. FINAL OUTPUT: Print a valid JSON string to stdout. 
   Format: {"answer": <the_result>, "submit_url": "<url_to_submit_to>"}
5. Do not print debug info to stdout (use stderr if needed), but if you do, the JSON must be the last thing printed.
"""
        user_prompt = f"""
Here is the task context text:
\"\"\"
{safe_context}
\"\"\"

Write the solution script.
"""
        response = llm_client.call(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            model="gpt-4o"
        )
        
        # Clean Markdown
        code = response
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.replace("```", "")
            
        return code.strip()

    def _execute_code(self, code: str) -> str:
        filename = os.path.join(TEMP_DIR, f"solve_{uuid.uuid4().hex}.py")
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            
            logger.info(f"Executing logic...")
            # Run with a timeout to prevent hanging
            result = subprocess.run(
                [sys.executable, filename],
                capture_output=True,
                text=True,
                timeout=45
            )
            
            # Combine stdout and stderr for debugging, but we mostly care about stdout for the answer
            full_output = result.stdout
            if result.stderr:
                logger.warning(f"Script Stderr: {result.stderr}")
                
            if result.returncode != 0:
                logger.error(f"Script execution failed. Stderr: {result.stderr}")
                raise Exception(f"Code execution error: {result.stderr}")
                
            return full_output
            
        except Exception as e:
            logger.error(f"Execution wrapper failed: {e}")
            return ""
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def _extract_json_from_output(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Scans string for a JSON object. Handles messy stdout.
        """
        try:
            # 1. Try pure parse (rarely works with raw scripts)
            return json.loads(output.strip())
        except json.JSONDecodeError:
            pass

        # 2. Regex Search: Find the LAST occurrence of a pattern looking like {"...": ...}
        # We look for the largest valid JSON block.
        try:
            # This regex finds a string starting with { and ending with } 
            # DOTALL allows it to match across multiple lines
            matches = re.findall(r'\{.*\}', output, re.DOTALL)
            
            if matches:
                # Try the last match first (as the answer is usually printed last)
                last_match = matches[-1]
                try:
                    return json.loads(last_match)
                except:
                    # If that fails, try to repair common issues or try earlier matches
                    pass
                    
            # 3. Fallback: Sometimes LLMs output: Answer: {"key": "value"}
            # Let's try to find the specific "answer" key
            if '"answer":' in output:
                 # Clean up the string to find the start and end of the JSON structure
                 start = output.find('{')
                 end = output.rfind('}') + 1
                 if start != -1 and end != -1:
                     json_str = output[start:end]
                     return json.loads(json_str)

        except Exception as e:
            logger.error(f"JSON extraction failed: {e}")
            
        return None
