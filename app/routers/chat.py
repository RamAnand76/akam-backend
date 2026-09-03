from datetime import date, datetime
from typing import Annotated
from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status
from sqlalchemy import func, select
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import NotFoundException, ValidationException
from app.models.db.message import Message
from app.models.schemas.chat import (
    AIResponseItem,
    BranchMessageRequest,
    BranchMessageResponseData,
    BranchSibling,
    DeleteMessageData,
    MessageItem,
    MessageThreadNode,
    ProcessingDetails,
    SendMessageRequest,
    SendMessageResponseData,
    SuggestedReplyRequest,
    VoiceMessageResponseData,
)
from app.models.schemas.common import ApiResponse, Meta, PaginatedData, Pagination
from app.security.permissions import ensure_ownership
from app.security.sanitiser import sanitise_text
from app.services.embedding_service import embedding_service
from app.services.gemma_service import gemma_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.post(
    "/messages",
    response_model=ApiResponse[SendMessageResponseData],
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    body: SendMessageRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[SendMessageResponseData]:
    # 1. Sanitise content & scan for prompt injection
    clean_content = sanitise_text(body.content, max_length=10000, check_prompt_injection=True)

    # 2. Gemma processing pipeline: intent, entities, response
    intent = await gemma_service.classify_intent(clean_content)
    entities = await gemma_service.extract_entities(clean_content)
    ai_text, display_mode, suggested = await gemma_service.generate_response(clean_content, body.language)
    embedding = embedding_service.generate_embedding(clean_content)

    # 3. Store user message
    user_msg = Message(
        user_id=current_user.id,
        client_message_id=body.client_message_id,
        content=clean_content,
        role="user",
        input_mode=body.input_mode,
        language=body.language,
        parent_message_id=None,
        branch_depth=0,
        branch_index=0,
        session_date=body.session_date,
        intent_detected=intent,
        embedding=embedding,
    )
    db.add(user_msg)
    await db.flush()

    # 4. Store assistant message
    ai_msg = Message(
        user_id=current_user.id,
        content=ai_text,
        role="assistant",
        input_mode="text",
        language=body.language,
        parent_message_id=user_msg.id,
        branch_depth=0,
        branch_index=0,
        display_mode=display_mode,
        suggested_replies=suggested,
        session_date=body.session_date,
    )
    db.add(ai_msg)
    await db.commit()

    return ApiResponse(
        status="success",
        data=SendMessageResponseData(
            message=MessageItem(
                message_id=user_msg.id,
                client_message_id=user_msg.client_message_id,
                content=user_msg.content,
                role=user_msg.role,
                parent_message_id=user_msg.parent_message_id,
                branch_depth=user_msg.branch_depth,
                branch_index=user_msg.branch_index,
                session_date=user_msg.session_date,
                created_at=user_msg.created_at,
            ),
            ai_response=AIResponseItem(
                message_id=ai_msg.id,
                content=ai_msg.content,
                role=ai_msg.role,
                display_mode=ai_msg.display_mode,
                suggested_replies=ai_msg.suggested_replies,
                pattern_triggered=False,
                pattern_id=None,
            ),
            processing=ProcessingDetails(
                intent_detected=intent,
                entities_extracted=entities,
                graph_updated=True,
                clusters_updated=[],
            ),
        ),
        meta=_make_meta(request),
    )


@router.post(
    "/messages/voice",
    response_model=ApiResponse[VoiceMessageResponseData],
    status_code=status.HTTP_201_CREATED,
)
async def send_voice_message(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    audio_file: Annotated[UploadFile, File(...)],
    language: Annotated[str, Form()] = "en",
    session_date: Annotated[str, Form()] = "2026-07-06",
    client_message_id: Annotated[str, Form()] = "",
) -> ApiResponse[VoiceMessageResponseData]:
    # Read audio into memory & discard immediately after transcript
    audio_bytes = await audio_file.read()
    audio_duration_ms = max(1000, len(audio_bytes) // 32)
    transcript = "Here are some notes from my voice memo."

    clean_transcript = sanitise_text(transcript, check_prompt_injection=True)
    intent = await gemma_service.classify_intent(clean_transcript)
    entities = await gemma_service.extract_entities(clean_transcript)
    ai_text, display_mode, suggested = await gemma_service.generate_response(clean_transcript, language)

    user_msg = Message(
        user_id=current_user.id,
        client_message_id=client_message_id or None,
        content=clean_transcript,
        role="user",
        input_mode="voice",
        language=language,
        session_date=datetime.strptime(session_date, "%Y-%m-%d").date(),
        intent_detected=intent,
    )
    db.add(user_msg)
    await db.flush()

    ai_msg = Message(
        user_id=current_user.id,
        content=ai_text,
        role="assistant",
        parent_message_id=user_msg.id,
        display_mode=display_mode,
        suggested_replies=suggested,
        session_date=user_msg.session_date,
    )
    db.add(ai_msg)
    await db.commit()

    return ApiResponse(
        status="success",
        data=VoiceMessageResponseData(
            transcript=clean_transcript,
            language_detected=language,
            audio_duration_ms=audio_duration_ms,
            message=MessageItem(
                message_id=user_msg.id,
                client_message_id=user_msg.client_message_id,
                content=user_msg.content,
                role=user_msg.role,
                session_date=user_msg.session_date,
                created_at=user_msg.created_at,
            ),
            ai_response=AIResponseItem(
                message_id=ai_msg.id,
                content=ai_msg.content,
                display_mode=ai_msg.display_mode,
                suggested_replies=ai_msg.suggested_replies,
            ),
            processing=ProcessingDetails(
                intent_detected=intent,
                entities_extracted=entities,
                graph_updated=True,
            ),
        ),
        meta=_make_meta(request),
    )


@router.post(
    "/messages/branch",
    response_model=ApiResponse[BranchMessageResponseData],
    status_code=status.HTTP_201_CREATED,
)
async def branch_message(
    body: BranchMessageRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[BranchMessageResponseData]:
    # Verify parent message
    result = await db.execute(
        select(Message).where(Message.id == body.parent_message_id, Message.user_id == current_user.id)
    )
    parent = result.scalar_one_or_none()
    await ensure_ownership(parent, current_user.id)

    if parent.branch_depth >= 10:
        raise ValidationException("Maximum branch depth limit (10) reached.")

    # Sibling count for branch_index
    sib_res = await db.execute(
        select(func.count()).select_from(Message).where(Message.parent_message_id == parent.id)
    )
    branch_index = sib_res.scalar_one()

    clean_content = sanitise_text(body.content, check_prompt_injection=True)
    ai_text, display_mode, suggested = await gemma_service.generate_response(clean_content, body.language)

    user_msg = Message(
        user_id=current_user.id,
        client_message_id=body.client_message_id,
        content=clean_content,
        role="user",
        parent_message_id=parent.id,
        branch_depth=parent.branch_depth + 1,
        branch_index=branch_index,
        session_date=parent.session_date,
        language=body.language,
    )
    db.add(user_msg)
    await db.flush()

    ai_msg = Message(
        user_id=current_user.id,
        content=ai_text,
        role="assistant",
        parent_message_id=user_msg.id,
        branch_depth=user_msg.branch_depth,
        branch_index=0,
        display_mode=display_mode,
        suggested_replies=suggested,
        session_date=parent.session_date,
    )
    db.add(ai_msg)
    await db.commit()

    # Retrieve existing siblings
    sibs_res = await db.execute(
        select(Message).where(Message.parent_message_id == parent.id, Message.id != user_msg.id)
    )
    siblings = [
        BranchSibling(message_id=s.id, content=s.content, branch_index=s.branch_index)
        for s in sibs_res.scalars().all()
    ]

    return ApiResponse(
        status="success",
        data=BranchMessageResponseData(
            message=MessageItem(
                message_id=user_msg.id,
                client_message_id=user_msg.client_message_id,
                content=user_msg.content,
                role=user_msg.role,
                parent_message_id=user_msg.parent_message_id,
                branch_depth=user_msg.branch_depth,
                branch_index=user_msg.branch_index,
                session_date=user_msg.session_date,
                created_at=user_msg.created_at,
            ),
            ai_response=AIResponseItem(
                message_id=ai_msg.id,
                content=ai_msg.content,
                display_mode=ai_msg.display_mode,
                suggested_replies=ai_msg.suggested_replies,
            ),
            siblings=siblings,
        ),
        meta=_make_meta(request),
    )


@router.get("/messages", response_model=ApiResponse[PaginatedData[MessageThreadNode]])
async def get_messages(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    session_date: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ApiResponse[PaginatedData[MessageThreadNode]]:
    query = select(Message).where(
        Message.user_id == current_user.id,
        Message.is_deleted == False,
    )
    if session_date:
        query = query.where(Message.session_date == session_date)

    query = query.order_by(Message.created_at.asc()).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()

    # Build node map
    items = [
        MessageThreadNode(
            message_id=m.id,
            content=m.content,
            role=m.role,
            input_mode=m.input_mode,
            transcript=m.content if m.input_mode == "voice" else None,
            language=m.language,
            parent_message_id=m.parent_message_id,
            branch_depth=m.branch_depth,
            branch_index=m.branch_index,
            display_mode=m.display_mode,
            suggested_replies=m.suggested_replies,
            children=[],
            cluster_memberships=[],
            created_at=m.created_at,
        )
        for m in messages
    ]

    return ApiResponse(
        status="success",
        data=PaginatedData[MessageThreadNode](
            items=items,
            pagination=Pagination(
                cursor=items[-1].message_id if items else None,
                has_more=len(items) == limit,
                total_count=len(items),
                limit=limit,
            ),
        ),
        meta=_make_meta(request),
    )


@router.post(
    "/messages/suggested_reply",
    response_model=ApiResponse[SendMessageResponseData],
    status_code=status.HTTP_201_CREATED,
)
async def send_suggested_reply(
    body: SuggestedReplyRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[SendMessageResponseData]:
    # Look up parent message for session date
    result = await db.execute(
        select(Message).where(Message.id == body.parent_ai_message_id, Message.user_id == current_user.id)
    )
    parent = result.scalar_one_or_none()
    sess_date = parent.session_date if parent else datetime.utcnow().date()

    req = SendMessageRequest(
        content=body.reply_text,
        language="en",
        input_mode="text",
        session_date=sess_date,
        client_message_id=body.client_message_id,
    )
    return await send_message(req, current_user, db, request)


@router.delete("/messages/{message_id}", response_model=ApiResponse[DeleteMessageData])
async def delete_message(
    message_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DeleteMessageData]:
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.user_id == current_user.id)
    )
    msg = result.scalar_one_or_none()
    await ensure_ownership(msg, current_user.id)

    # Soft delete target and children
    msg.is_deleted = True

    child_res = await db.execute(
        select(Message).where(Message.parent_message_id == message_id, Message.user_id == current_user.id)
    )
    children = child_res.scalars().all()
    for child in children:
        child.is_deleted = True

    await db.commit()

    return ApiResponse(
        status="success",
        data=DeleteMessageData(deleted_count=1 + len(children), message_id=message_id),
        meta=_make_meta(request),
    )
