"""
Escalation Service
Manages analyst escalation tickets using the existing MySQL database (escalation_tickets table)
with duplicate suppression, graceful failure handling, and non-sensitive metadata tracking.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.escalation import EscalationTicket
from app.observability.logger import logger


class EscalationService:
    @staticmethod
    def _sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Strip sensitive fields (auth tokens, passwords, full text chunks) from metadata."""
        if not metadata:
            return {}
        safe_meta = {}
        disallowed_keys = {"api_key", "password", "token", "secret", "raw_content", "chunk_text", "unauthorized_content"}
        for k, v in metadata.items():
            if any(bad in k.lower() for bad in disallowed_keys):
                continue
            # Keep serializable primitives or small dicts/lists
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                safe_meta[k] = v
        return safe_meta

    @classmethod
    def create_escalation(
        cls,
        client_id: str,
        query_text: str,
        reason: str = "Low retrieval confidence or client entitlement restriction",
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Create and persist a new analyst escalation ticket in MySQL.
        Handles duplicate submissions and database failures gracefully.
        Never fabricates a ticket identifier if the database operation fails.
        """
        clean_query = query_text.strip() if query_text else ""
        safe_meta = cls._sanitize_metadata(metadata)
        
        should_close = False
        session = db
        if session is None:
            try:
                session = SessionLocal()
                should_close = True
            except Exception as e:
                logger.error(f"EscalationService: Database connection error initializing session: {e}")
                return {"ticket_id": None, "error": str(e), "status": "failed"}

        try:
            # Refresh session to prevent stale MVCC snapshot in long-lived sessions
            try:
                session.commit()
            except Exception:
                session.rollback()

            # 1. Duplicate check: find open ticket for identical client and query
            existing = session.query(EscalationTicket).filter(
                EscalationTicket.client_id == client_id,
                EscalationTicket.query_text == clean_query,
                EscalationTicket.status == "open"
            ).order_by(desc(EscalationTicket.id)).first()

            if existing:
                logger.info(
                    f"Duplicate escalation detected: reusing open ticket '{existing.ticket_id}' "
                    f"for client '{client_id}'."
                )
                res = existing.to_dict()
                res["is_duplicate"] = True
                return res

            # 2. Concurrency-safe ticket generation with retry
            max_id = session.query(func.max(EscalationTicket.id)).scalar() or 0
            candidate_num = max_id + 1

            for _ in range(15):
                ticket_number = f"ESC-{candidate_num:04d}"
                # Check if this ticket_number already exists in database
                exists = session.query(EscalationTicket.id).filter(
                    EscalationTicket.ticket_id == ticket_number
                ).first()
                if exists:
                    candidate_num += 1
                    continue

                ticket = EscalationTicket(
                    ticket_id=ticket_number,
                    client_id=client_id,
                    query_text=clean_query,
                    reason=reason,
                    status="open",
                    priority=priority,
                    metadata_json=safe_meta,
                    created_at=datetime.now(timezone.utc)
                )

                try:
                    session.add(ticket)
                    session.commit()
                    session.refresh(ticket)

                    logger.info(
                        f"Successfully created MySQL escalation ticket '{ticket_number}' "
                        f"for client '{client_id}' | Reason: {reason}"
                    )
                    return ticket.to_dict()
                except IntegrityError:
                    session.rollback()
                    # Check if another process inserted this query concurrently
                    concur_existing = session.query(EscalationTicket).filter(
                        EscalationTicket.client_id == client_id,
                        EscalationTicket.query_text == clean_query,
                        EscalationTicket.status == "open"
                    ).first()
                    if concur_existing:
                        res = concur_existing.to_dict()
                        res["is_duplicate"] = True
                        return res
                    candidate_num += 1
                    continue

            return {"ticket_id": None, "error": "Unable to allocate unique ticket_id", "status": "failed"}

        except Exception as e:
            logger.error(f"Failed to persist escalation ticket in MySQL: {e}", exc_info=True)
            try:
                session.rollback()
            except Exception:
                pass
            # Return failure without fabricating a ticket ID
            return {"ticket_id": None, "error": str(e), "status": "failed"}

        finally:
            if should_close and session is not None:
                session.close()

    @classmethod
    def list_escalations(
        cls,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve escalation tickets from MySQL filtered by client and status.
        """
        should_close = False
        session = db
        if session is None:
            try:
                session = SessionLocal()
                should_close = True
            except Exception as e:
                logger.error(f"EscalationService.list_escalations: DB connection error: {e}")
                return []

        try:
            query = session.query(EscalationTicket)
            if client_id:
                query = query.filter(EscalationTicket.client_id == client_id)
            if status:
                query = query.filter(EscalationTicket.status == status)

            query = query.order_by(desc(EscalationTicket.created_at))
            records = query.offset(skip).limit(limit).all()
            return [r.to_dict() for r in records]

        except Exception as e:
            logger.error(f"Error querying escalation tickets from MySQL: {e}", exc_info=True)
            return []

        finally:
            if should_close and session is not None:
                session.close()

    @classmethod
    def count_escalations(
        cls,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        db: Optional[Session] = None
    ) -> int:
        """Count escalation records in MySQL with optional filters."""
        should_close = False
        session = db
        if session is None:
            try:
                session = SessionLocal()
                should_close = True
            except Exception as e:
                logger.error(f"EscalationService.count_escalations: DB connection error: {e}")
                return 0

        try:
            query = session.query(func.count(EscalationTicket.id))
            if client_id:
                query = query.filter(EscalationTicket.client_id == client_id)
            if status:
                query = query.filter(EscalationTicket.status == status)
            return int(query.scalar() or 0)

        except Exception as e:
            logger.error(f"Error counting escalation tickets from MySQL: {e}", exc_info=True)
            return 0

        finally:
            if should_close and session is not None:
                session.close()
