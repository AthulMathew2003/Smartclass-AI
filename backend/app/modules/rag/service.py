import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage.s3 import S3StorageService
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException,
)
from app.modules.subjects.models import (
    Subject,
    SubjectStatus,
    SubjectMaterial,
    SubjectMaterialStatus,
    MaterialIndexStatus,
)
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.modules.subjects.material_repository import SubjectMaterialRepository
from app.modules.rag.constants import RAG_SUPPORTED_MIME_TYPES, RAG_UNSUPPORTED_MIME_TYPES
from app.modules.rag.document_processor import DocumentProcessor, compute_content_hash
from app.modules.rag.chunker import DocumentChunker
from app.modules.rag.embeddings import EmbeddingService
from app.modules.rag.vector_store import VectorStoreService
from app.modules.rag.exceptions import RagException
from app.modules.rag.schemas import (
    RagSearchResponse,
    RagSearchResultItem,
    RagIndexStatusResponse,
)

logger = logging.getLogger(__name__)


class RagService:
    def __init__(
        self,
        db: AsyncSession,
        storage: Optional[S3StorageService] = None,
        processor: Optional[DocumentProcessor] = None,
        chunker: Optional[DocumentChunker] = None,
        embeddings: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStoreService] = None,
    ):
        self.db = db
        self.repo = SubjectMaterialRepository(db)
        self.storage = storage or S3StorageService()
        self.processor = processor or DocumentProcessor()
        self.chunker = chunker or DocumentChunker(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP
        )
        self.embeddings = embeddings or EmbeddingService()
        self.vector_store = vector_store or VectorStoreService()

    # ── Hierarchy and Permission Checks ──────────────────────────

    async def _verify_subject_hierarchy(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> tuple[Subject, Workspace]:
        subject = await self.repo.get_subject(subject_id)
        if not subject or subject.subject_status == SubjectStatus.ARCHIVED:
            raise NotFoundException("Subject not found or archived.")

        workspace = await self.repo.get_workspace(subject.subject_workspace_id)
        if not workspace or workspace.workspace_organization_id != org_id or workspace.workspace_status == WorkspaceStatus.ARCHIVED:
            raise NotFoundException("Subject not found in the current organization.")

        return subject, workspace

    async def _verify_material_hierarchy(
        self,
        material_id: uuid.UUID,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> tuple[SubjectMaterial, Subject, Workspace]:
        material = await self.repo.get_material_by_id(material_id)
        if not material or material.material_subject_id != subject_id:
            raise NotFoundException("Material not found in this subject.")

        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        return material, subject, workspace

    async def _verify_teacher_or_admin(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool,
    ) -> None:
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

        is_assigned_teacher = await self.repo.is_user_subject_teacher(subject_id, user_id)
        if not is_assigned_teacher:
            raise ForbiddenException("Access denied. You are not assigned to this subject.")

    async def _verify_workspace_access(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool,
    ) -> None:
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

    # ── Indexing Lifecycle ───────────────────────────────────────

    async def index_material(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        force: bool = False,
    ) -> SubjectMaterial:
        """
        Process a Subject Material for RAG indexing:
        1. Check mime type support.
        2. Fetch file bytes from S3.
        3. Compute SHA-256 hash (skip if unchanged and not force).
        4. Extract text sections.
        5. Chunk text.
        6. Generate embeddings via Gemini.
        7. Upsert vectors to ChromaDB.
        8. Update PostgreSQL metadata.
        """
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_teacher_or_admin(
            user_id=requesting_user_id,
            org_id=org_id,
            subject_id=subject.subject_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin,
        )

        clean_mime = (material.material_content_type or "").strip().lower()

        # Check if type is unsupported for RAG (e.g. video, archive, image)
        if clean_mime in RAG_UNSUPPORTED_MIME_TYPES or clean_mime not in RAG_SUPPORTED_MIME_TYPES:
            material.material_index_status = MaterialIndexStatus.UNSUPPORTED
            material.material_index_error = f"File format ({material.material_content_type}) is not supported for text extraction."
            await self.db.flush()
            return material

        # Mark as processing
        material.material_index_status = MaterialIndexStatus.PROCESSING
        material.material_index_error = None
        await self.db.flush()

        try:
            # 1. Fetch raw bytes from private S3
            file_bytes = self.storage.get_object_bytes(material.material_s3_key)
            content_hash = compute_content_hash(file_bytes)

            # 2. Check if content is identical and already indexed
            if (
                not force
                and material.material_content_hash == content_hash
                and material.material_index_status == MaterialIndexStatus.INDEXED
            ):
                logger.info(f"Material {material_id} content hash unchanged. Skipping re-embedding.")
                return material

            # 3. Extract text sections
            sections = self.processor.extract_sections(
                file_bytes=file_bytes,
                mime_type=clean_mime,
                filename=material.material_original_filename,
            )

            # 4. Chunk sections
            chunks = self.chunker.chunk_sections(sections)
            if not chunks:
                raise RagException("No text chunks could be generated from document.")

            # 5. Generate embeddings via Gemini
            chunk_texts = [c.text for c in chunks]
            embeddings = self.embeddings.embed_documents(chunk_texts)

            # 6. Store vectors in ChromaDB with tenant metadata
            stored_count = self.vector_store.upsert_chunks(
                organization_id=org_id,
                workspace_id=workspace.workspace_id,
                subject_id=subject.subject_id,
                material_id=material.material_id,
                material_title=material.material_title,
                filename=material.material_original_filename,
                content_hash=content_hash,
                chunks=chunks,
                embeddings=embeddings,
            )

            # 7. Update PostgreSQL metadata
            material.material_index_status = MaterialIndexStatus.INDEXED
            material.material_indexed_at = datetime.now(timezone.utc)
            material.material_content_hash = content_hash
            material.material_chunk_count = stored_count
            material.material_index_error = None
            await self.db.flush()

            logger.info(f"Successfully indexed material {material_id} with {stored_count} chunks.")
            return material

        except Exception as e:
            logger.error(f"Failed to index material {material_id}: {str(e)}")
            # Safe user-facing error message
            safe_error = str(e)
            if "API key" in safe_error or "Key" in safe_error:
                safe_error = "AI embedding service configuration error."
            
            material.material_index_status = MaterialIndexStatus.FAILED
            material.material_index_error = safe_error[:1000]
            await self.db.flush()
            return material

    async def get_index_status(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
    ) -> RagIndexStatusResponse:
        """Get indexing status for a subject material."""
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_workspace_access(
            user_id=requesting_user_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin,
        )

        return RagIndexStatusResponse(
            material_id=material.material_id,
            status=material.material_index_status.value if hasattr(material.material_index_status, "value") else str(material.material_index_status),
            indexed_at=material.material_indexed_at,
            chunk_count=material.material_chunk_count or 0,
            content_hash=material.material_content_hash,
            error=material.material_index_error,
        )

    async def delete_material_vectors(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> None:
        """Delete all vectors for a material idempotently."""
        self.vector_store.delete_material_vectors(material_id)

    # ── Semantic Search ──────────────────────────────────────────

    async def search(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        query: str,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        top_k: int = 5,
    ) -> RagSearchResponse:
        """
        Execute authorization-enforced semantic retrieval:
        1. Validate workspace and subject access for user.
        2. Generate query embedding.
        3. Search ChromaDB with organization, workspace, and subject filter.
        4. Return top-k chunk results with source citations.
        """
        if not query or not query.strip():
            raise ValidationException("Search query cannot be empty.")

        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_workspace_access(
            user_id=requesting_user_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin,
        )

        # Generate query vector
        query_embedding = self.embeddings.embed_query(query.strip())

        # Query vector store with strict tenant filter
        raw_results = self.vector_store.search(
            query_embedding=query_embedding,
            organization_id=org_id,
            workspace_id=workspace.workspace_id,
            subject_id=subject.subject_id,
            top_k=min(top_k, settings.RAG_MAX_SEARCH_TOP_K),
        )

        items: List[RagSearchResultItem] = [
            RagSearchResultItem(
                material_id=r["material_id"],
                material_title=r["material_title"],
                filename=r["filename"],
                chunk_index=r["chunk_index"],
                page_number=r["page_number"],
                slide_number=r["slide_number"],
                content=r["content"],
                score=r["score"],
            )
            for r in raw_results
        ]

        return RagSearchResponse(
            query=query.strip(),
            subject_id=subject.subject_id,
            results_count=len(items),
            results=items,
        )
