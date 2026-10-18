"""
Chat Application Service
Delegates market research copilot queries to the unified RAGPipeline,
integrating relational MySQL entitlements, ChromaDB vector retrieval,
conflict detection, derived calculations, and prompt-injected security defense.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.schemas.chat import ChatResponse
from app.observability.logger import logger


class ChatService:
    @staticmethod
    def process_chat(
        db: Session,
        client_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Executes end-to-end RAG copilot workflow via the RAGPipeline:
        - Permission verification against relational MySQL data
        - Dual retrieval from MySQL (structured metrics) and ChromaDB (unstructured narrative)
        - Conflict detection between disparate report methodologies
        - Derived value calculations
        - Defense-in-depth isolation against adversarial document instructions
        - Grounded synthesis with LLM API and calibrated confidence scoring
        """
        from app.retrieval.rag_pipeline import rag_pipeline

        logger.info(f"ChatService.process_chat received query for client='{client_id}'")
        return rag_pipeline.execute(
            db=db,
            client_id=client_id,
            query=query,
            conversation_id=conversation_id,
            report_id=report_id
        )
