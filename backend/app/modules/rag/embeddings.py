import time
import logging
from typing import List, Optional
from google import genai

from app.core.config import settings
from app.modules.rag.exceptions import EmbeddingException

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service responsible for generating vector embeddings via Google Gemini Embeddings API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_EMBEDDING_MODEL or "gemini-embedding-001"
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise EmbeddingException("Google Gemini API key is not configured.")
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for a single search query string."""
        if not text or not text.strip():
            raise EmbeddingException("Search query text cannot be empty.")

        client = self._get_client()
        try:
            response = client.models.embed_content(
                model=self.model,
                contents=text.strip(),
            )
            if hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
            elif hasattr(response, "embedding") and response.embedding:
                return response.embedding.values
            else:
                raise EmbeddingException("Unexpected empty embedding response from Gemini API.")
        except Exception as e:
            if isinstance(e, EmbeddingException):
                raise
            logger.error(f"Gemini embedding error for query: {str(e)}")
            raise EmbeddingException(f"Failed to generate query embedding: {str(e)}")

    def embed_documents(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """
        Generate embedding vectors for a list of document chunk texts in batches with retries.
        """
        if not texts:
            return []

        client = self._get_client()
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self._embed_batch_with_retry(client, batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _embed_batch_with_retry(self, client: genai.Client, batch: List[str], max_retries: int = 3) -> List[List[float]]:
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.embed_content(
                    model=self.model,
                    contents=batch,
                )
                if hasattr(response, "embeddings") and response.embeddings:
                    return [emb.values for emb in response.embeddings]
                raise EmbeddingException("Invalid embedding response structure from Gemini API.")
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini embed_content attempt {attempt}/{max_retries} failed: {str(e)}")
                if attempt < max_retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))

        raise EmbeddingException(f"Failed to generate embeddings after {max_retries} attempts: {str(last_error)}")
