"""
Escalation Service
Manages analyst escalation tickets with persistent storage.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.observability.logger import logger

ESCALATION_FILE = Path(settings.DOCUMENTS_DIR) / "escalations.json"
_lock = threading.Lock()

class EscalationService:
    @staticmethod
    def _read_records() -> List[Dict[str, Any]]:
        if not ESCALATION_FILE.exists():
            return []
        try:
            with open(ESCALATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading escalations file: {e}")
            return []

    @staticmethod
    def _write_records(records: List[Dict[str, Any]]) -> None:
        ESCALATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(ESCALATION_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving escalations: {e}")

    @classmethod
    def create_escalation(
        cls,
        client_id: str,
        query_text: str,
        reason: str = "Low retrieval confidence or client entitlement restriction",
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Create and store a new analyst escalation ticket."""
        with _lock:
            records = cls._read_records()
            ticket_num = f"ESC-{len(records) + 1:04d}"
            ticket = {
                "ticket_id": ticket_num,
                "client_id": client_id,
                "query_text": query_text,
                "status": "open",
                "priority": priority,
                "reason": reason,
                "created_at": datetime.now().isoformat()
            }
            records.append(ticket)
            cls._write_records(records)
            logger.info(f"Created escalation ticket {ticket_num} for client {client_id}")
            return ticket

    @classmethod
    def list_escalations(
        cls,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve escalation tickets filtered by client and status."""
        with _lock:
            records = cls._read_records()
        
        filtered = records
        if client_id:
            filtered = [r for r in filtered if r.get("client_id") == client_id]
        if status:
            filtered = [r for r in filtered if r.get("status") == status]
            
        return filtered[skip:skip + limit]

    @classmethod
    def count_escalations(cls, client_id: Optional[str] = None) -> int:
        """Count escalation records."""
        with _lock:
            records = cls._read_records()
        if client_id:
            return len([r for r in records if r.get("client_id") == client_id])
        return len(records)
