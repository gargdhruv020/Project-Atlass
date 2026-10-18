"""
Chat Endpoint: POST /chat
Handles AI Market Research Copilot queries with validation, authentication, and structured citations.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import require_api_key, validate_client
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.core.config import settings

router = APIRouter(tags=["Chat"])

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Submit query to Market Research Copilot",
    description=(
        "Executes agentic market research retrieval, enforcing client purchase entitlements, "
        "conflict analysis, derived metric calculation, and automatic escalation."
    )
)
async def chat_endpoint(
    request: Request,
    chat_req: ChatRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    # 1. Validate request payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request body exceeds allowed maximum size."
        )

    # 2. Validate client ID exists in MySQL
    client = validate_client(chat_req.client_id, db=db)

    # 3. Invoke ChatService
    response = ChatService.process_chat(
        db=db,
        client_id=client.id,
        query=chat_req.query,
        conversation_id=chat_req.conversation_id,
        report_id=chat_req.report_id
    )

    return response
