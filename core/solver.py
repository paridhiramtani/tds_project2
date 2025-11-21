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

    def _call_llm(self, messages: list, model: str = "gpt-4o-mini", response_format=None) -> str:
        try:
            logger.info(f"Calling LLM {model}")
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0
            }
            if response_format:
                kwargs["response_format"] = response_format
                
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def analyze_task(self, task_data: dict) -> dict:
        """
        Reasoning Agent: Analyzes text and screenshot to understand the task.
        """
        text_content = task_data.get("text", "")
        screenshot_b64 = task_data.get("screenshot", "")
        
        system_prompt = """
You are an expert Data Analyst and Logic Reasoner.
Your goal is to deconstruct a data processing task.
You will be given the text content of a webpage and a screenshot.

Output a JSON object with the following structure:
{
  "question": "The exact question to be answered",
  "submit_url": "The URL to submit the answer to",
  "task_type": "visual | data | hybrid",
  "plan": "Step-by-step plan to solve the task using Python",
  "visual_extraction_needed": boolean // true if we need to extract data from the screenshot (e.g. charts, unselectable text)
}
"""
        user_content = [
            {"type": "text", "text": f"Webpage Text Content:\n{text_content}"}
        ]
        
        if screenshot_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
            })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self._call_llm(messages, model="gpt-4o", response_format={"type": "json_object"})
        return json.loads(response)

    def extract_visual_data(self, task_data: dict, question: str) -> str:
        """
        Vision Agent: Extracts specific data from the screenshot.
        """
        screenshot_b64 = task_data.get("screenshot", "")
        if not screenshot_b64:
            return "No screenshot available."
            
        system_prompt = """
You are an expert in Optical Character Recognition (OCR) and Visual Data Extraction.
Extract the specific data requested by the user from the provided screenshot.
Return ONLY the extracted data in a structured format (CSV, JSON, or plain text) that is easy to parse programmatically.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": f"Extract data relevant to this question: {question}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ]}
        ]
        
        return self._call_llm(messages, model="gpt-4o")

    def generate_code(self, plan: dict, visual_data: str = None, feedback: str = None) -> str:
        """
        Coding Agent: Generates Python code based on the plan.
        """
        system_prompt = """
You are an expert Python developer.
Your goal is to write a Python script to solve a data task based on a provided plan.
You must output ONLY valid Python code. No markdown.

Available libraries: 
- Data: pandas, numpy, sklearn
- Web: requests, beautifulsoup4, httpx
- Documents: pypdf, pdfplumber, tabula (PDF tables), python-docx, openpyxl
- Media: PIL (images), pytesseract (OCR), cv2 (OpenCV), pydub (audio), speech_recognition

Your code MUST:
1. Solve the problem described in the plan.
2. If 'visual_data' is provided, use it directly (it's pre-extracted from the screen).
3. Print a VALID JSON string to stdout with the format:
   {"answer": <calculated_answer>, "submit_url": "<submit_url_from_plan>"}
"""
        user_prompt = f"Plan: {json.dumps(plan, indent=2)}\n"
        if visual_data:
            user_prompt += f"\nVisual Data Extracted: {visual_data}\n"
        if feedback:
            user_prompt += f"\nPrevious Attempt Feedback: {feedback}\n"
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        code = self._call_llm(messages, model="gpt-4o")
        
        # Clean up markdown
        if code.startswith("```python"):
            code = code.replace("```python", "").replace("```", "")
        elif code.startswith("```"):
            code = code.replace("```", "")
        return code.strip()

    def execute_code(self, code: str) -> str:
        """
        Executes the generated code and captures stdout.
        """
        import uuid
        filename = f"temp_solution_{uuid.uuid4().hex}.py"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            
            result = subprocess.run(
                [sys.executable, filename],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise Exception(f"Execution error: {result.stderr}")
                
            return result.stdout.strip()
        except Exception as e:
            raise
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def solve(self, task_data: dict, feedback: str = None, model: str = "gpt-4o"):
        """
        Orchestrates the multi-agent flow.
        """
        try:
            # 1. Analyze Task (Reasoning)
            # Only re-analyze if it's the first attempt (no feedback)
            if not feedback:
                logger.info("Analyzing task...")
                self.analysis = self.analyze_task(task_data)
                logger.info(f"Analysis: {self.analysis}")
            
            # 2. Vision Extraction (if needed)
            visual_data = None
            if self.analysis.get("visual_extraction_needed"):
                logger.info("Extracting visual data...")
                visual_data = self.extract_visual_data(task_data, self.analysis["question"])
            
            # 3. Generate Code (Coding)
            logger.info("Generating code...")
            code = self.generate_code(self.analysis, visual_data, feedback)
            
            # 4. Execute
            logger.info("Executing code...")
            result = self.execute_code(code)
            
            # Parse result
            try:
                return json.loads(result)
            except:
                # Try to salvage if it's just the answer
                return {"answer": result, "submit_url": self.analysis.get("submit_url")}
                
        except Exception as e:
            logger.error(f"Solver failed: {e}")
            return {"error": str(e)}

solver = TaskSolver()
