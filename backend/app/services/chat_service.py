"""
Chat Application Service
Delegates market research copilot queries to the compiled LangGraph agent workflow,
integrating router classification, relational MySQL entitlements, ChromaDB vector retrieval,
read-only SQL aggregations, deterministic calculations, critique, and escalation routing.
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
        Executes end-to-end Copilot workflow via the LangGraph agent:
        - Router: Intent classification (factual, comparison, calculation, sql, out-of-scope, unsafe)
        - Entitlement Checker: Client permission validation against relational MySQL data
        - Retriever: Scoped retrieval from MySQL and ChromaDB with independent verification
        - Read-Only SQL Tool: Safe aggregate calculations over permitted reports
        - Calculator: Deterministic CAGR projections and regional share derivations
        - Critic: Grounding audit, citation verification, and methodological conflict detection
        - Escalation: MySQL analyst ticket logging without protected text disclosure
        - Writer: Grounded synthesis with calibrated confidence and structured response
        """
        from app.agents.workflow import run_copilot_workflow

        logger.info(f"ChatService.process_chat executing LangGraph agent for client='{client_id}'")
        return run_copilot_workflow(
            db=db,
            query=query,
            client_id=client_id,
            conversation_id=conversation_id,
            report_id=report_id
        )
