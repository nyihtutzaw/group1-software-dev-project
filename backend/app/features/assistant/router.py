from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.config import get_settings
from app.features.assistant import service
from app.features.assistant.schemas import AssistantStatusOut, ChatIn

router = APIRouter(prefix="/admin/assistant", tags=["F5 assistant"])


@router.get("", response_model=AssistantStatusOut)
def assistant_status(_: User = Depends(require_roles(Role.ADMIN))) -> AssistantStatusOut:
    """Whether the assistant is set up here, and which docs it answers from."""
    names, _prompt = service.knowledge()
    return AssistantStatusOut(
        enabled=service.is_configured(),
        model=get_settings().openrouter_model,
        documents=list(names),
    )


@router.post(
    "/chat",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/plain": {}}, "description": "The answer, streamed"}},
)
def chat(body: ChatIn, user: User = Depends(require_roles(Role.ADMIN))) -> StreamingResponse:
    """Answer the last question; the answer streams back as plain text. Nothing is stored."""
    if not service.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The assistant is not set up on this server (no OpenRouter API key or no docs).",
        )
    if not service.limiter.allow(user.id, get_settings().assistant_requests_per_minute):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many questions in a minute. Wait a moment and ask again.",
            headers={"Retry-After": "60"},
        )
    try:
        upstream = service.open_stream(body.messages)
    except service.AssistantError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return StreamingResponse(
        service.answer_text(upstream),
        media_type="text/plain; charset=utf-8",
        # No caching anywhere, and no proxy buffering that would hold the answer back.
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
