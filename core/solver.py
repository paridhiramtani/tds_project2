import os
import subprocess
import sys
import json
import logging
from openai import OpenAI
from config import AIPROXY_TOKEN, OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger(__name__)

class TaskSolver:
    def __init__(self):
        api_key = AIPROXY_TOKEN or OPENAI_API_KEY
        if not api_key:
            logger.warning("No API key found. Solver will fail.")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=OPENAI_BASE_URL if AIPROXY_TOKEN else None
        )

    def generate_code(self, user_prompt: str, model: str = "gpt-4o-mini") -> str:
        """
        Uses LLM to generate Python code to solve the task.
        """
        system_prompt = """
You are an expert Python developer and data analyst. 
Your goal is to solve a data processing task described by the user.
You must output ONLY valid Python code. No markdown, no explanations.
The code will be executed directly.

Available libraries: 
- Data: pandas, numpy, sklearn
- Web: requests, beautifulsoup4, httpx
- Documents: pypdf, pdfplumber, tabula (PDF tables), python-docx, openpyxl
- Media: PIL (images), pytesseract (OCR), cv2 (OpenCV), pydub (audio), speech_recognition

The task description contains a question and a submission URL.
Your code MUST:
1. Parse the task to find the specific question and the submission URL.
2. Perform the necessary data analysis/processing to answer the question.
   - If you need to download files, use `requests`.
   - If you need to read a PDF table, use `tabula` or `pdfplumber`.
   - If you need OCR, use `pytesseract`.
3. Print a VALID JSON string to stdout with the following format:
   {"answer": <calculated_answer>, "submit_url": "<extracted_url>"}
   
   - "answer" can be a number, string, or JSON object/list as required.
   - "submit_url" must be the full URL found in the text.
"""
        try:
            logger.info(f"Generating code using model: {model}")
            response = self.client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            code = response.choices[0].message.content
            # Clean up markdown if present
            if code.startswith("```python"):
                code = code.replace("```python", "").replace("```", "")
            elif code.startswith("```"):
                code = code.replace("```", "")
            return code.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def execute_code(self, code: str) -> str:
        """
        Executes the generated code and captures stdout.
        """
        import uuid
        filename = f"temp_solution_{uuid.uuid4().hex}.py"
        try:
            # Write code to a temporary file
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Execute
            result = subprocess.run(
                [sys.executable, filename],
                capture_output=True,
                text=True,
                timeout=60 # 1 minute max execution
            )
            
            if result.returncode != 0:
                logger.error(f"Code execution failed: {result.stderr}")
                raise Exception(f"Execution error: {result.stderr}")
                
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Execution wrapper failed: {e}")
            raise
        finally:
            # Cleanup
            if os.path.exists(filename):
                os.remove(filename)

    def solve(self, task_description: str, feedback: str = None, model: str = "gpt-4o-mini"):
        logger.info("Generating solution code...")
        
        prompt = f"Task: {task_description}\n\nWrite a Python script to solve this."
        if feedback:
            prompt += f"\n\nPrevious attempt failed with feedback: {feedback}\nPlease adjust your code to fix this."
            
        code = self.generate_code(prompt, model=model)
        logger.info("Executing solution code...")
        result = self.execute_code(code)
        
        # Try to parse result as JSON if possible, else return string/number
        try:
            return json.loads(result)
        except:
            # Try to convert to number if possible
            try:
                if "." in result:
                    return float(result)
                return int(result)
            except:
                return result

solver = TaskSolver()
