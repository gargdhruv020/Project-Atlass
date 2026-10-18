"""
Chat Application Service
Delegates market research copilot queries to the compiled LangGraph agent workflow,
integrating router classification, relational MySQL entitlements, ChromaDB vector retrieval,
read-only SQL aggregations, deterministic calculations, critique, escalation routing,
and transactional conversation & message persistence in MySQL.
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
        - Resolves or creates conversation session associated with client_id
        - Persists user query to chat_messages
        - Router: Intent classification (factual, comparison, calculation, sql, out-of-scope, unsafe)
        - Entitlement Checker: Client permission validation against relational MySQL data
        - Retriever: Scoped retrieval from MySQL and ChromaDB with independent verification
        - Read-Only SQL Tool: Safe aggregate calculations over permitted reports
        - Calculator: Deterministic CAGR projections and regional share derivations
        - Critic: Grounding audit, citation verification, and methodological conflict detection
        - Escalation: MySQL analyst ticket logging without protected text disclosure
        - Writer: Grounded synthesis with calibrated confidence and structured response
        - Persists assistant response to chat_messages with metadata and returns message_id
        """
        from app.agents.workflow import run_copilot_workflow
        from app.services.conversation_service import ConversationService

        logger.info(f"ChatService.process_chat executing LangGraph agent for client='{client_id}'")

        # 1. Resolve or create active conversation session
        conv = ConversationService.get_or_create_conversation(
            db=db,
            client_id=client_id,
            conversation_id=conversation_id,
            title=query.strip()[:42] + ("..." if len(query.strip()) > 42 else "")
        )
        active_conversation_id = conv.id

        # 2. Persist user query to history
        ConversationService.save_message(
            db=db,
            conversation_id=active_conversation_id,
            client_id=client_id,
            sender="user",
            content=query
        )

        # 3. Execute LangGraph Copilot agent workflow
        resp = run_copilot_workflow(
            db=db,
            query=query,
            client_id=client_id,
            conversation_id=active_conversation_id,
            report_id=report_id
        )

        # 4. Persist assistant response to history
        citations_dump = [c.model_dump() for c in resp.citations] if resp.citations else []
        conflicts_dump = [cf.model_dump() for cf in resp.conflicts] if resp.conflicts else []

        asst_msg = ConversationService.save_message(
            db=db,
            conversation_id=active_conversation_id,
            client_id=client_id,
            sender="assistant",
            content=resp.answer,
            citations=citations_dump,
            conflicts=conflicts_dump,
            derived_values=resp.derived_values,
            confidence=resp.confidence,
            escalated=resp.escalated,
            escalation_ticket=resp.escalation_ticket
        )

        resp.conversation_id = active_conversation_id
        resp.message_id = asst_msg.id
        return resp
