import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from app.core.config import settings
from app.modules.ai_tutor.exceptions import AiTutorGenerationException

logger = logging.getLogger(__name__)


class AiTutorLlmClient:
    """
    Client responsible for interfacing with Google Gemini LLM API for AI Tutor response generation.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_GENERATION_MODEL or "gemini-3.6-flash"
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise AiTutorGenerationException("Google Gemini API key is not configured.")
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_tutor_response(
        self,
        system_instruction: str,
        conversation_history: List[Dict[str, str]],
        current_query_with_context: str,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate grounded tutor response using Google Gemini models API.
        
        :param system_instruction: Strict grounding, role, and anti-injection instructions.
        :param conversation_history: List of past messages formatted as [{'role': 'user'|'assistant', 'content': '...'}]
        :param current_query_with_context: The prompt containing reference course material context + user question.
        :return: Generated text response.
        """
        client = self._get_client()

        # Build multi-turn content objects
        contents: List[types.Content] = []

        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            text_content = msg.get("content", "").strip()
            if text_content:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text_content)]
                    )
                )

        # Append current turn
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=current_query_with_context)]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature if temperature is not None else settings.AI_TUTOR_TEMPERATURE,
            max_output_tokens=max_output_tokens or settings.AI_TUTOR_MAX_OUTPUT_TOKENS,
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            if not response or not response.text:
                raise AiTutorGenerationException("Gemini returned an empty response.")

            return response.text.strip()

        except Exception as e:
            if isinstance(e, AiTutorGenerationException):
                raise
            logger.error(f"Gemini LLM generation error: {str(e)}")
            safe_msg = str(e)
            if "API key" in safe_msg or "Key" in safe_msg:
                safe_msg = "AI generation service configuration error."
            raise AiTutorGenerationException(f"Failed to generate tutor response: {safe_msg}")
