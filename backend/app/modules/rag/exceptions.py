class RagException(Exception):
    """Base exception for RAG operations."""
    def __init__(self, message: str = "A RAG processing error occurred."):
        self.message = message
        super().__init__(self.message)


class DocumentExtractionException(RagException):
    """Exception raised when document text extraction fails."""
    pass


class EmbeddingException(RagException):
    """Exception raised when vector embedding generation fails."""
    pass


class VectorStoreException(RagException):
    """Exception raised when vector database operations fail."""
    pass
