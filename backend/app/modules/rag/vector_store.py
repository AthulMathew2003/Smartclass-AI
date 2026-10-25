import uuid
import logging
from typing import List, Dict, Any, Optional
import chromadb

from app.core.config import settings
from app.modules.rag.chunker import DocumentChunk
from app.modules.rag.exceptions import VectorStoreException

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    ChromaDB Vector Store wrapper with strict multi-tenant metadata filtering and deterministic vector IDs.
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        client: Optional[Any] = None
    ):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        
        if client is not None:
            self._client = client
        else:
            self._client = chromadb.PersistentClient(path=self.persist_directory)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(
        self,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        material_title: str,
        filename: str,
        content_hash: str,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ) -> int:
        """
        Idempotently insert/replace all vectors for a material.
        First deletes any previous chunks for the material, then inserts the new ones.
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreException(
                f"Mismatch between number of chunks ({len(chunks)}) and embeddings ({len(embeddings)})."
            )

        # 1. Clean previous vectors for this material
        self.delete_material_vectors(material_id)

        if not chunks:
            return 0

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk, emb in zip(chunks, embeddings):
            vector_id = f"{material_id}:{chunk.chunk_index}"
            ids.append(vector_id)
            documents.append(chunk.text)
            
            meta: Dict[str, Any] = {
                "organization_id": str(organization_id),
                "workspace_id": str(workspace_id),
                "subject_id": str(subject_id),
                "material_id": str(material_id),
                "material_title": str(material_title)[:255],
                "filename": str(filename)[:255],
                "chunk_index": int(chunk.chunk_index),
                "content_hash": str(content_hash),
                "page_number": int(chunk.page_number) if chunk.page_number is not None else -1,
                "slide_number": int(chunk.slide_number) if chunk.slide_number is not None else -1,
            }
            metadatas.append(meta)

        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            return len(ids)
        except Exception as e:
            logger.error(f"ChromaDB insert failed for material {material_id}: {str(e)}")
            raise VectorStoreException(f"Failed to store vectors in vector database: {str(e)}")

    def delete_material_vectors(self, material_id: uuid.UUID) -> None:
        """
        Idempotently delete all chunks associated with a specific material.
        """
        try:
            self._collection.delete(
                where={"material_id": str(material_id)}
            )
        except Exception as e:
            # ChromaDB raises if items don't exist in some versions; log safely without crashing
            logger.info(f"Vector deletion notice for material {material_id}: {str(e)}")

    def search(
        self,
        query_embedding: List[float],
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        subject_id: uuid.UUID,
        top_k: int = 5,
        material_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search with strict tenant isolation metadata filtering.

        Args:
            material_ids: When provided, restricts results to only these specific
                          materials (must belong to the specified subject). Used by
                          the question paper generator to enforce selected-material-only
                          retrieval. Each ID is validated server-side before this call.
        """
        # Strict tenant boundary filter — always applied
        tenant_conditions: List[Dict[str, Any]] = [
            {"organization_id": str(organization_id)},
            {"workspace_id": str(workspace_id)},
            {"subject_id": str(subject_id)},
        ]

        # Optional material-scoped filter for question paper generation
        if material_ids:
            # ChromaDB $in operator: match any of the listed material IDs
            material_id_strs = [str(mid) for mid in material_ids]
            tenant_conditions.append({"material_id": {"$in": material_id_strs}})

        where_filter = {"$and": tenant_conditions}

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"ChromaDB query error: {str(e)}")
            raise VectorStoreException(f"Vector search failed: {str(e)}")

        formatted_results: List[Dict[str, Any]] = []

        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            return []

        doc_list = results["documents"][0]
        meta_list = results["metadatas"][0]
        dist_list = results["distances"][0] if results.get("distances") else [0.0] * len(doc_list)

        for doc, meta, dist in zip(doc_list, meta_list, dist_list):
            # Cosine distance to similarity conversion: similarity = 1 - distance
            # Chroma returns cosine distance in [0, 2]
            score = max(0.0, 1.0 - float(dist)) if dist is not None else 1.0

            page_num = meta.get("page_number")
            slide_num = meta.get("slide_number")

            formatted_results.append({
                "material_id": uuid.UUID(meta["material_id"]),
                "material_title": meta.get("material_title", ""),
                "filename": meta.get("filename", ""),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "page_number": int(page_num) if page_num is not None and page_num != -1 else None,
                "slide_number": int(slide_num) if slide_num is not None and slide_num != -1 else None,
                "content": doc,
                "score": round(score, 4)
            })

        return formatted_results
