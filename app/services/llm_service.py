import logging
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import AIPROXY_TOKEN, OPENAI_API_KEY, OPENAI_BASE_URL, TOKEN_BUDGET_LIMIT
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = AIPROXY_TOKEN or OPENAI_API_KEY
        if not self.api_key:
            logger.warning("No API key found. LLM calls will fail.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=OPENAI_BASE_URL if AIPROXY_TOKEN else None
        )
        
        self.total_cost = 0.0
        self._cache = {} # Simple in-memory cache
        
        # Approximate costs per 1k tokens (Input, Output)
        self.PRICING = {
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4o": (0.0025, 0.0100)
        }

    def _track_cost(self, model: str, usage):
        if not usage:
            return
            
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        rates = self.PRICING.get(model, (0.0, 0.0))
        cost = (input_tokens / 1000 * rates[0]) + (output_tokens / 1000 * rates[1])
        
        self.total_cost += cost
        logger.info(f"Cost: ${cost:.5f} | Total: ${self.total_cost:.4f}")
        
        if self.total_cost > TOKEN_BUDGET_LIMIT:
            logger.warning(f"BUDGET EXCEEDED: ${self.total_cost:.4f} > ${TOKEN_BUDGET_LIMIT}")

    def call(self, messages: List[Dict[str, Any]], model: str = "gpt-4o-mini", response_format=None, use_cache: bool = True) -> str:
        # Cache Key Generation
        if use_cache:
            cache_key = f"{model}:{json.dumps(messages, sort_keys=True)}"
            if cache_key in self._cache:
                logger.info("LLM Cache Hit")
                return self._cache[cache_key]

        try:
            logger.info(f"Calling LLM: {model}")
            
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0
            }
            if response_format:
                kwargs["response_format"] = response_format
                
            response = self.client.chat.completions.create(**kwargs)
            
            self._track_cost(model, response.usage)
            content = response.choices[0].message.content
            
            if use_cache:
                self._cache[cache_key] = content
                
            return content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Fallback Strategy
            if model == "gpt-4o":
                logger.warning("Falling back to gpt-4o-mini")
                return self.call(messages, model="gpt-4o-mini", response_format=response_format, use_cache=use_cache)
            raise

    def parse_json(self, response: str) -> Dict[str, Any]:
        try:
            # Clean markdown
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "")
            elif response.startswith("```"):
                response = response.replace("```", "")
            return json.loads(response.strip())
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {response}")
            raise

llm_client = LLMService()
