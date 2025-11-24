import os
import httpx
import uuid
from typing import Dict, Any
from app.handlers.base_handler import BaseHandler
from app.services.llm_service import llm_client
from app.utils.logger import setup_logger
from app.config import TEMP_DIR

logger = setup_logger(__name__)

class AudioHandler(BaseHandler):
    async def handle(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Downloads audio, transcribes it, and answers the question.
        """
        audio_url = task_data.get("audio_url")
        question = task_data.get("question")
        
        if not audio_url:
            raise ValueError("AudioHandler requires 'audio_url'")

        # 1. Download Audio
        audio_path = await self._download_audio(audio_url)
        
        try:
            # 2. Transcribe
            transcript = await self._transcribe(audio_path)
            logger.info(f"Transcript: {transcript[:100]}...")
            
            # 3. Answer Question
            return self._solve_with_transcript(transcript, question)
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    async def _download_audio(self, url: str) -> str:
        filename = os.path.join(TEMP_DIR, f"audio_{uuid.uuid4().hex}.mp3")
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(filename, "wb") as f:
                f.write(resp.content)
        return filename

    async def _transcribe(self, file_path: str) -> str:
        # Use OpenAI Whisper API
        try:
            with open(file_path, "rb") as audio_file:
                transcript = llm_client.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            return transcript.text
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def _solve_with_transcript(self, transcript: str, question: str) -> Dict[str, Any]:
        prompt = f"Transcript: {transcript}\n\nQuestion: {question}\n\nExtract the answer as JSON: {{'answer': ...}}"
        response = llm_client.call([{"role": "user", "content": prompt}], model="gpt-4o-mini")
        return llm_client.parse_json(response)
