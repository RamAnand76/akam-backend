# Akam — Backend API Contract
**Version**: 2.0.0  
**Status**: Production  
**Last Updated**: 2026-07-06  
**Base URL**: `https://api.akam.app/v1`  
**Protocol**: HTTPS only. HTTP → 301 redirect. WSS for real-time.

---

## Purpose of This Document

This contract is the **single source of truth** for building the Akam backend end-to-end.  
An agentic code editor consuming this document must produce:

- A **FastAPI** application (Python 3.12+)
- **PostgreSQL 16** + **pgvector** for graph and vector storage
- **Redis 7** for caching, rate limiting, session management
- **SQLAlchemy 2.0** ORM (async) for all database access — zero raw SQL
- **Celery + Redis** for background jobs
- **Pydantic v2** for all request/response validation
- **Alembic** for database migrations
- **pytest + httpx** for test suite (minimum 80% coverage)
- **Docker + docker-compose** for local development
- **Structlog** for structured JSON logging
- Security that meets or exceeds FAANG production standards

Every endpoint in this document maps to exactly one FastAPI router, one Pydantic request model, one Pydantic response model, and one or more SQLAlchemy queries — all ownership-scoped to the authenticated user.

---

## Project Structure

```
akam-backend/
├── app/
│   ├── main.py                    # FastAPI app factory, middleware registration
│   ├── config.py                  # Pydantic Settings (env vars)
│   ├── dependencies.py            # Shared FastAPI dependencies (auth, db, rate limit)
│   ├── exceptions.py              # Custom exception classes + handlers
│   ├── middleware/
│   │   ├── security_headers.py    # HSTS, CSP, X-Frame-Options etc.
│   │   ├── request_id.py          # X-Request-ID injection
│   │   ├── rate_limit.py          # Redis-backed rate limiting
│   │   └── logging.py             # Structlog request/response logging
│   ├── routers/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── graph.py
│   │   ├── clusters.py
│   │   ├── events.py
│   │   ├── nudges.py
│   │   ├── briefing.py
│   │   ├── search.py
│   │   ├── digest.py
│   │   └── user.py
│   ├── models/
│   │   ├── db/                    # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── message.py
│   │   │   ├── node.py
│   │   │   ├── edge.py
│   │   │   ├── cluster.py
│   │   │   ├── cluster_membership.py
│   │   │   ├── cluster_edge.py
│   │   │   ├── event.py
│   │   │   ├── event_panel.py
│   │   │   ├── event_panel_item.py
│   │   │   ├── nudge.py
│   │   │   ├── pattern.py
│   │   │   └── relationship_score.py
│   │   └── schemas/               # Pydantic request/response schemas
│   │       ├── common.py          # ApiResponse, Pagination, ErrorDetail
│   │       ├── auth.py
│   │       ├── chat.py
│   │       ├── graph.py
│   │       ├── clusters.py
│   │       ├── events.py
│   │       ├── nudges.py
│   │       ├── briefing.py
│   │       ├── search.py
│   │       ├── digest.py
│   │       └── user.py
│   ├── services/
│   │   ├── auth_service.py        # JWT creation, validation, revocation
│   │   ├── chat_service.py        # Message processing pipeline
│   │   ├── graph_service.py       # Node/edge CRUD + weight computation
│   │   ├── cluster_service.py     # Clustering algorithm
│   │   ├── embedding_service.py   # multilingual-e5-small wrapper
│   │   ├── gemini_service.py      # Gemini API client (text, voice, entity extraction)
│   │   ├── nudge_service.py       # Nudge generation + delivery
│   │   ├── briefing_service.py    # Briefing synthesis
│   │   ├── pattern_service.py     # Pattern detection
│   │   └── search_service.py      # Semantic search + graph reranking
│   ├── workers/
│   │   ├── celery_app.py
│   │   ├── tasks/
│   │   │   ├── graph_tasks.py     # Async graph updates
│   │   │   ├── cluster_tasks.py   # Background clustering
│   │   │   ├── nudge_tasks.py     # Scheduled nudge evaluation
│   │   │   ├── digest_tasks.py    # Sunday digest generation
│   │   │   └── cleanup_tasks.py   # Expired token purge, audio deletion
│   ├── security/
│   │   ├── jwt.py                 # RS256 token creation/validation
│   │   ├── permissions.py         # Object-level ownership checks
│   │   ├── sanitiser.py           # Input sanitisation + prompt injection guard
│   │   └── crypto.py              # Timing-safe comparisons, key rotation
│   └── db/
│       ├── session.py             # Async SQLAlchemy session factory
│       ├── redis.py               # Redis client factory
│       └── migrations/            # Alembic migrations
│           └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_chat.py
│   ├── test_graph.py
│   ├── test_clusters.py
│   ├── test_events.py
│   ├── test_nudges.py
│   ├── test_security.py           # IDOR, injection, rate limit tests
│   └── test_websocket.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt               # pinned exact versions
├── alembic.ini
├── .env.example
└── pyproject.toml
```

---

## Standard Response Envelope

**Every endpoint** returns this exact envelope. No exceptions.

### Success
```json
{
  "status": "success",
  "data": { },
  "meta": {
    "request_id": "01J4MXYZ...",
    "timestamp": "2026-07-06T10:30:00.123Z",
    "version": "2.0.0"
  }
}
```

### Success — Paginated List
```json
{
  "status": "success",
  "data": {
    "items": [],
    "pagination": {
      "cursor": "uuid",
      "has_more": true,
      "total_count": 247,
      "limit": 20
    }
  },
  "meta": {
    "request_id": "01J4MXYZ...",
    "timestamp": "2026-07-06T10:30:00.123Z",
    "version": "2.0.0"
  }
}
```

### Error
```json
{
  "status": "error",
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "The requested node does not exist.",
    "field": null,
    "details": [],
    "doc_url": "https://docs.akam.app/errors/ENTITY_NOT_FOUND"
  },
  "meta": {
    "request_id": "01J4MXYZ...",
    "timestamp": "2026-07-06T10:30:00.123Z",
    "version": "2.0.0"
  }
}
```

### Validation Error (422)
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "field": null,
    "details": [
      {
        "field": "content",
        "message": "String too long. Max 10000 characters.",
        "value_received": null
      },
      {
        "field": "language",
        "message": "Must be one of: en, ml",
        "value_received": "fr"
      }
    ],
    "doc_url": "https://docs.akam.app/errors/VALIDATION_ERROR"
  },
  "meta": {
    "request_id": "01J4MXYZ...",
    "timestamp": "2026-07-06T10:30:00.123Z",
    "version": "2.0.0"
  }
}
```

### Pydantic Schema (common.py)
```python
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Any
from datetime import datetime
import uuid

T = TypeVar("T")

class Meta(BaseModel):
    request_id: str
    timestamp: datetime
    version: str = "2.0.0"

class Pagination(BaseModel):
    cursor: str | None = None
    has_more: bool
    total_count: int
    limit: int

class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination

class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    value_received: Any = None

class ApiError(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: list[ErrorDetail] = []
    doc_url: str

class ApiResponse(BaseModel, Generic[T]):
    status: str                   # "success" | "error"
    data: T | None = None
    error: ApiError | None = None
    meta: Meta
```

---

## Standard Headers

### Required on Every Request
```
Authorization: Bearer <access_token>    # All authenticated endpoints
Content-Type: application/json          # POST/PATCH requests
X-Client-Version: 1.0.0                 # Flutter app version
X-Device-Platform: android | ios
Idempotency-Key: <uuid>                 # Required on all POST (create) endpoints
```

### Required on Every Response
```
X-Request-ID: <ulid>                    # Echoed request ID for tracing
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1720086400           # Unix epoch
Retry-After: 60                         # Only on 429 responses
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Cache-Control: no-store, max-age=0      # All authenticated endpoints
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## Idempotency

All `POST` endpoints that create resources support idempotency.  
Client sends `Idempotency-Key: <uuid>` header.  
Server caches the response in Redis for **24 hours**.  
Duplicate requests with same key within 24h return the **cached response** with `HTTP 200` and header `Idempotent-Replayed: true`.

```python
# Implementation: idempotency middleware checks Redis before handler runs
# Key format: f"idempotency:{user_id}:{idempotency_key}"
# TTL: 86400 seconds
```

---

## Error Code Registry

| Code | HTTP Status | When to Use |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing, invalid, or expired access token |
| `TOKEN_EXPIRED` | 401 | Access token expired (client should refresh) |
| `TOKEN_REVOKED` | 401 | Token explicitly revoked (force logout) |
| `FORBIDDEN` | 403 | Valid token, resource belongs to another user |
| `ENTITY_NOT_FOUND` | 404 | Resource ID valid format but does not exist for this user |
| `VALIDATION_ERROR` | 422 | Pydantic validation failure — see `details` array |
| `IDEMPOTENCY_CONFLICT` | 409 | Same idempotency key, different request body |
| `RATE_LIMITED` | 429 | Per-user or per-IP rate limit exceeded |
| `QUOTA_EXCEEDED` | 429 | Daily quota for AI calls exceeded |
| `MEDIA_TOO_LARGE` | 413 | File upload exceeds size limit |
| `UNSUPPORTED_MEDIA` | 415 | Audio MIME type not allowed |
| `AI_UNAVAILABLE` | 503 | Gemini API down — retry with exponential backoff |
| `INTERNAL_ERROR` | 500 | Unexpected server error — logged, never exposes stack trace |
| `PROMPT_INJECTION_DETECTED` | 400 | User content detected attempting to manipulate AI system prompt |
| `DELETION_IN_PROGRESS` | 409 | User data deletion already in progress |

---

---

# 1. Authentication

**Router**: `app/routers/auth.py`  
**Service**: `app/services/auth_service.py`  
**Security**: `app/security/jwt.py`

### JWT Specification
- Algorithm: **RS256** (2048-bit RSA keypair, never HS256)
- Access token TTL: **3600 seconds (1 hour)**
- Refresh token TTL: **2592000 seconds (30 days)**
- Refresh token rotation: enabled — each refresh invalidates old refresh token
- Revocation: `jti` (JWT ID) stored in Redis with TTL = remaining token lifetime
- Claims: `sub` (user_id), `jti`, `iat`, `exp`, `device_id`, `scope`

---

### `POST /auth/register`

Register a new user account.

**Auth**: None  
**Idempotency**: Required (`Idempotency-Key` header)  
**Rate limit**: 5 req/IP/min, 3 burst

**Request body**:
```json
{
  "name": "Ramanand R",
  "language": "en",
  "device_id": "android-uuid-string",
  "fcm_token": "firebase-token-string",
  "device_platform": "android"
}
```

**Validation**:
| Field | Type | Rules |
|---|---|---|
| `name` | string | required, 1–100 chars, strip null bytes |
| `language` | enum | required, `en` \| `ml` |
| `device_id` | string | required, 10–200 chars, alphanumeric + `-_` |
| `fcm_token` | string | required, 10–500 chars, alphanumeric + `-_:` |
| `device_platform` | enum | required, `android` \| `ios` |

**Response `201`**:
```json
{
  "status": "success",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_expires_in": 2592000
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Rate limit: 3 accounts per `device_id` per 24h (Redis counter)
- No email required for MVP — `device_id` is the identity anchor
- User row created with `status: active`

---

### `POST /auth/refresh`

Exchange a refresh token for a new access token + new refresh token.

**Auth**: None (refresh token in body)  
**Rate limit**: 10 req/user/min

**Request body**:
```json
{
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_expires_in": 2592000
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Old refresh token's `jti` blacklisted in Redis immediately on use
- New `jti` generated for both new tokens
- If old refresh token already blacklisted → `TOKEN_REVOKED` 401
- After 5 consecutive refresh failures from same IP → block IP for 15 min

---

### `POST /auth/logout`

Revoke current session.

**Auth**: Bearer token required  
**Rate limit**: 5 req/user/min

**Request body**:
```json
{
  "refresh_token": "eyJ..."
}
```

**Response `200`**:
```json
{
  "status": "success",
  "data": { "revoked": true },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Blacklists both access token `jti` and refresh token `jti` in Redis
- Closes all WebSocket connections for this session via Redis pub/sub signal

---

### `POST /auth/logout_all`

Revoke all sessions for this user. Used when device lost or account compromise suspected.

**Auth**: Bearer token required  
**Rate limit**: 2 req/user/hour

**Response `200`**:
```json
{
  "status": "success",
  "data": { "sessions_revoked": 4 },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Increments `token_generation` counter in `users` table
- All existing JWTs for this user become invalid (generation mismatch check)
- Closes all WebSocket connections via Redis pub/sub

---

### `PUT /auth/device`

Update FCM token (called on app launch if token changed).

**Auth**: Bearer token required

**Request body**:
```json
{
  "fcm_token": "new-firebase-token",
  "device_platform": "android"
}
```

**Response `200`**:
```json
{
  "status": "success",
  "data": { "updated": true },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

---

# 2. Chat — Messages & Branched Conversations

**Router**: `app/routers/chat.py`  
**Service**: `app/services/chat_service.py`  
**Background**: `app/workers/tasks/graph_tasks.py`

### Data Model: Message
```python
class Message(Base):
    __tablename__ = "messages"
    id                 = Column(UUID, primary_key=True, default=uuid4)
    user_id            = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    content            = Column(Text, nullable=False)
    role               = Column(Enum("user","assistant"), nullable=False)
    input_mode         = Column(Enum("text","voice"), default="text")
    language           = Column(Enum("en","ml"), default="en")
    parent_message_id  = Column(UUID, ForeignKey("messages.id"), nullable=True)
    branch_depth       = Column(Integer, default=0)
    branch_index       = Column(Integer, default=0)
    display_mode       = Column(Enum("bubble","large_question","pattern_insight"), default="bubble")
    suggested_replies  = Column(ARRAY(Text), default=[])
    intent_detected    = Column(String(50), nullable=True)
    session_date       = Column(Date, nullable=False)
    embedding          = Column(Vector(384), nullable=True)
    is_deleted         = Column(Boolean, default=False)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes
    __table_args__ = (
        Index("ix_messages_user_session", "user_id", "session_date"),
        Index("ix_messages_user_parent", "user_id", "parent_message_id"),
    )
```

---

### `POST /chat/messages`

Send a new root-level message. Triggers full AI pipeline.

**Auth**: Bearer token required  
**Idempotency**: Required  
**Rate limit**: 100 req/user/day, 20 req/user/min

**Request body**:
```json
{
  "content": "Had a long call with Rahul today. He got the job offer.",
  "language": "en",
  "input_mode": "text",
  "session_date": "2026-07-06",
  "client_message_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Validation**:
| Field | Type | Rules |
|---|---|---|
| `content` | string | required, 1–10000 chars, strip null bytes, prompt injection scan |
| `language` | enum | required, `en` \| `ml` |
| `input_mode` | enum | required, `text` \| `voice` |
| `session_date` | date | required, not future, not older than 1 year |
| `client_message_id` | UUID | required, used as idempotency dedup key |

**Response `201`**:
```json
{
  "status": "success",
  "data": {
    "message": {
      "message_id": "uuid",
      "client_message_id": "uuid",
      "content": "Had a long call with Rahul today. He got the job offer.",
      "role": "user",
      "parent_message_id": null,
      "branch_depth": 0,
      "branch_index": 0,
      "session_date": "2026-07-06",
      "created_at": "2026-07-06T10:30:00.123Z"
    },
    "ai_response": {
      "message_id": "uuid",
      "content": "That's exciting news about Rahul! Want me to remember the job offer details?",
      "role": "assistant",
      "display_mode": "bubble",
      "suggested_replies": ["Yes, save it", "Just note he got an offer"],
      "pattern_triggered": false,
      "pattern_id": null
    },
    "processing": {
      "intent_detected": "journal",
      "entities_extracted": ["Rahul", "job offer"],
      "graph_updated": true,
      "clusters_updated": ["uuid"]
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**AI Pipeline** (executed synchronously for response, graph updates async):
```
1. Prompt injection scan → reject if detected (400 PROMPT_INJECTION_DETECTED)
2. Intent classification (Gemini Flash, max_tokens=10)
3. Entity extraction (Gemini Flash, structured JSON output)
4. AI response generation (Gemini Flash, streaming)
5. Return response to client
6. [ASYNC via Celery] Embed message, update graph nodes/edges, cluster assignment
```

---

### `POST /chat/messages/voice`

Send a voice message via Gemini STT.

**Auth**: Bearer token required  
**Idempotency**: Required  
**Rate limit**: 20 req/user/day, 5 req/user/min  
**Content-Type**: `multipart/form-data`

**Request fields**:
| Field | Type | Rules |
|---|---|---|
| `audio_file` | binary | required, max 10MB (enforced at nginx), magic byte validated |
| `language` | string | required, `en` \| `ml` |
| `session_date` | string | required, ISO date |
| `client_message_id` | string | required, UUID format |
| `parent_message_id` | string | optional, UUID format |

**Allowed MIME types** (magic byte validated, extension ignored):
- `audio/wav` → magic: `52 49 46 46`
- `audio/x-m4a` → magic: `00 00 00 XX 66 74 79 70`
- `audio/webm` → magic: `1A 45 DF A3`
- `audio/ogg` → magic: `4F 67 67 53`

**Response `201`**:
```json
{
  "status": "success",
  "data": {
    "transcript": "Had a long call with Rahul today. He got the job offer.",
    "language_detected": "en",
    "audio_duration_ms": 4200,
    "message": { "...same as POST /chat/messages..." },
    "ai_response": { "...same as POST /chat/messages..." },
    "processing": { "...same as POST /chat/messages..." }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Audio file stored to temp storage, sent to Gemini, **deleted immediately** after transcript returned
- Audio never persisted to any database or object storage
- If Gemini STT fails → `AI_UNAVAILABLE` 503

---

### `POST /chat/messages/branch`

Add a branch child to an existing message. Implements the branched chat UI (Image 4).

**Auth**: Bearer token required  
**Idempotency**: Required  
**Rate limit**: 200 req/user/day, 30 req/user/min

**Request body**:
```json
{
  "parent_message_id": "uuid",
  "content": "Don't want to cook",
  "language": "en",
  "input_mode": "text",
  "client_message_id": "uuid"
}
```

**Validation**:
| Field | Type | Rules |
|---|---|---|
| `parent_message_id` | UUID | required, must exist, must belong to auth user, `branch_depth` < 10 |
| `content` | string | required, 1–10000 chars |
| `language` | enum | required, `en` \| `ml` |

**Response `201`**:
```json
{
  "status": "success",
  "data": {
    "message": {
      "message_id": "uuid",
      "parent_message_id": "uuid",
      "branch_depth": 1,
      "branch_index": 0,
      "content": "Don't want to cook",
      "role": "user",
      "created_at": "2026-07-06T10:30:05.000Z"
    },
    "ai_response": {
      "message_id": "uuid",
      "content": "Got it — delivery tonight. Any cuisine preference?",
      "display_mode": "large_question",
      "suggested_replies": ["Indian", "Chinese", "Anything works"]
    },
    "siblings": [
      {
        "message_id": "uuid",
        "content": "Delivery is ok",
        "branch_index": 1
      }
    ]
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- `branch_index` auto-assigned as count of existing siblings
- `branch_depth` = parent's `branch_depth` + 1
- Max `branch_depth` = 10 → `VALIDATION_ERROR` if exceeded
- AI context includes full branch ancestry for coherent response

---

### `GET /chat/messages`

Fetch paginated message thread. Cursor-based pagination.

**Auth**: Bearer token required  
**Rate limit**: 500 req/user/day

**Query parameters**:
| Param | Type | Default | Rules |
|---|---|---|---|
| `session_date` | date | today | ISO date, not future |
| `cursor` | UUID | null | last `message_id` from previous page |
| `limit` | int | 50 | 1–100 |
| `direction` | enum | `before` | `before` \| `after` |
| `include_branches` | bool | true | include branch children inline |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "message_id": "uuid",
        "content": "Here are some notes from my voice memo.",
        "role": "user",
        "input_mode": "voice",
        "transcript": "Here are some notes from my voice memo.",
        "language": "en",
        "parent_message_id": null,
        "branch_depth": 0,
        "branch_index": 0,
        "display_mode": "bubble",
        "suggested_replies": [],
        "children": [
          {
            "message_id": "uuid",
            "content": "Don't want to cook",
            "branch_depth": 1,
            "branch_index": 0,
            "children": []
          },
          {
            "message_id": "uuid",
            "content": "Delivery is ok",
            "branch_depth": 1,
            "branch_index": 1,
            "children": []
          }
        ],
        "cluster_memberships": [
          {
            "cluster_id": "uuid",
            "cluster_label": "Daily routines",
            "membership_weight": 0.78
          }
        ],
        "created_at": "2026-07-06T09:41:00.000Z"
      }
    ],
    "pagination": {
      "cursor": "uuid",
      "has_more": true,
      "total_count": 247,
      "limit": 50
    },
    "session_label": "Today"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `POST /chat/messages/suggested_reply`

User tapped a suggested reply chip.

**Auth**: Bearer token required  
**Idempotency**: Required  
**Rate limit**: Inherits from `POST /chat/messages`

**Request body**:
```json
{
  "reply_text": "Thinking about something Chinese",
  "parent_ai_message_id": "uuid",
  "client_message_id": "uuid"
}
```

**Response `201`**: Same shape as `POST /chat/messages`

---

### `DELETE /chat/messages/{message_id}`

Soft-delete a message and all branch children.

**Auth**: Bearer token required  
**Rate limit**: 50 req/user/day

**Path param**: `message_id` — UUID v4, verified to belong to auth user

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "deleted_count": 3,
    "message_id": "uuid"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Soft delete: sets `is_deleted = true`, never hard deletes
- Graph nodes/edges referencing this message remain (memory persists)
- Hard delete only via `DELETE /user/data`

---

---

# 3. Memory Graph

**Router**: `app/routers/graph.py`  
**Service**: `app/services/graph_service.py`

### Data Models
```python
class Node(Base):
    __tablename__ = "nodes"
    id            = Column(UUID, primary_key=True, default=uuid4)
    user_id       = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    label         = Column(String(200), nullable=False)
    type          = Column(Enum("person","event","promise","topic","emotion","place"), nullable=False)
    display_type  = Column(String(50), nullable=False)
    body_preview  = Column(Text, nullable=True)
    tags          = Column(ARRAY(String), default=[])
    pos_x         = Column(Float, nullable=True)
    pos_y         = Column(Float, nullable=True)
    embedding     = Column(Vector(384), nullable=True)
    is_active     = Column(Boolean, default=True)
    metadata_json = Column(JSONB, default={})
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_active   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_nodes_user_type", "user_id", "type"),
        Index("ix_nodes_embedding", "embedding", postgresql_using="ivfflat"),
    )

class Edge(Base):
    __tablename__ = "edges"
    id              = Column(UUID, primary_key=True, default=uuid4)
    user_id         = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    source_node_id  = Column(UUID, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id  = Column(UUID, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    weight          = Column(Float, nullable=False, default=0.0)
    edge_type       = Column(String(50), nullable=True)
    co_occurrence   = Column(Integer, default=0)
    llm_labeled     = Column(Boolean, default=False)
    last_decay      = Column(DateTime(timezone=True), server_default=func.now())
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source_node_id", "target_node_id"),
        Index("ix_edges_user_weight", "user_id", "weight"),
    )
```

---

### `GET /graph`

Fetch full graph — nodes + edges — for canvas rendering.

**Auth**: Bearer token required  
**Rate limit**: 200 req/user/day  
**Cache**: Redis, TTL 60s, invalidated on graph update

**Query parameters**:
| Param | Type | Default | Rules |
|---|---|---|---|
| `type_filter` | string | null | comma-separated node types |
| `limit` | int | 100 | 1–200 |
| `min_edge_weight` | float | 0.0 | 0.0–1.0 |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "nodes": [
      {
        "node_id": "uuid",
        "label": "Textbook Shopping List",
        "type": "topic",
        "display_type": "current_context",
        "body_preview": "University Physics, The Gay Science, Dawn of Everything...",
        "tags": ["Fall 2023", "Planning"],
        "position": { "x": 0.52, "y": 0.61 },
        "is_active": true,
        "edge_count": 4,
        "last_active": "2026-07-01T14:22:00Z"
      }
    ],
    "edges": [
      {
        "edge_id": "uuid",
        "source_node_id": "uuid",
        "target_node_id": "uuid",
        "weight": 0.87,
        "edge_type": "mentioned-by",
        "llm_labeled": true
      }
    ],
    "graph_stats": {
      "total_nodes": 34,
      "total_edges": 89,
      "strongest_node_label": "Amma",
      "most_active_topic": "Akam app"
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `GET /graph/nodes/{node_id}`

Fetch single node with full neighbour detail.

**Auth**: Bearer token required  
**Ownership**: `node.user_id == auth.user_id` — else 404

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "node_id": "uuid",
    "label": "Textbook Shopping List",
    "type": "topic",
    "display_type": "current_context",
    "body_preview": "University Physics...",
    "tags": ["Fall 2023", "Planning"],
    "position": { "x": 0.52, "y": 0.61 },
    "is_active": true,
    "edge_count": 4,
    "last_active": "2026-07-01T14:22:00Z",
    "neighbours": [
      {
        "node_id": "uuid",
        "label": "Norris Bookstore",
        "display_type": "location",
        "edge_weight": 0.91,
        "edge_type": "location",
        "edge_id": "uuid"
      }
    ],
    "related_messages": [
      {
        "message_id": "uuid",
        "content_preview": "Need to buy Physics and Philosophy textbooks...",
        "created_at": "2026-06-28T14:00:00Z"
      }
    ]
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `PATCH /graph/nodes/{node_id}`

Update node label, tags, or position.

**Auth**: Bearer token required  
**Ownership**: Verified before update

**Request body** (all fields optional):
```json
{
  "label": "Updated Label",
  "tags": ["tag1", "tag2"],
  "position": { "x": 0.45, "y": 0.38 }
}
```

**Validation**:
| Field | Rules |
|---|---|
| `label` | 1–200 chars if provided |
| `tags` | max 10 tags, each max 50 chars |
| `position.x` | 0.0–1.0 float |
| `position.y` | 0.0–1.0 float |

**Response `200`**: Updated node object

---

### `DELETE /graph/nodes/{node_id}`

Delete a node and cascade-delete all its edges.

**Auth**: Bearer token required  
**Ownership**: Verified before delete

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "deleted": true,
    "edges_removed": 4,
    "node_id": "uuid"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `GET /graph/subgraph`

Ego-subgraph around a node (for focus/tap on canvas).

**Auth**: Bearer token required

**Query parameters**:
| Param | Type | Default |
|---|---|---|
| `node_id` | UUID | required |
| `depth` | int | 1 (max 2) |

**Response `200`**: Same shape as `GET /graph` but scoped to subgraph

---

---

# 4. Memory List — Clusters

**Router**: `app/routers/clusters.py`  
**Service**: `app/services/cluster_service.py`  
**Background**: `app/workers/tasks/cluster_tasks.py`

### Data Models
```python
class Cluster(Base):
    __tablename__ = "clusters"
    id              = Column(UUID, primary_key=True, default=uuid4)
    user_id         = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    label           = Column(String(200), nullable=False)
    card_style      = Column(Enum(
                        "stacked_cards","date_quote","label_only",
                        "image_grid","standard"), default="standard")
    color_accent    = Column(String(7), nullable=True)   # #hex validated
    centroid        = Column(Vector(384), nullable=True)
    member_count    = Column(Integer, default=0)
    is_manual       = Column(Boolean, default=False)     # manually created by user
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    last_active     = Column(DateTime(timezone=True), server_default=func.now())

class MessageClusterMembership(Base):
    __tablename__ = "message_cluster_memberships"
    message_id      = Column(String, nullable=False)     # SQLite message ID
    cluster_id      = Column(UUID, ForeignKey("clusters.id", ondelete="CASCADE"))
    user_id         = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    weight          = Column(Float, nullable=False)       # 0.60–1.0
    is_partial      = Column(Boolean, default=False)      # weight < 0.80
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (PrimaryKeyConstraint("message_id", "cluster_id"),)

class ClusterEdge(Base):
    __tablename__ = "cluster_edges"
    id              = Column(UUID, primary_key=True, default=uuid4)
    user_id         = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    cluster_a       = Column(UUID, ForeignKey("clusters.id", ondelete="CASCADE"))
    cluster_b       = Column(UUID, ForeignKey("clusters.id", ondelete="CASCADE"))
    weight          = Column(Float, nullable=False)
    shared_count    = Column(Integer, default=1)
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    __table_args__ = (UniqueConstraint("cluster_a", "cluster_b"),)
```

---

### `GET /clusters`

Fetch all clusters. Memory List screen.

**Auth**: Bearer token required  
**Rate limit**: 500 req/user/day  
**Cache**: Redis, TTL 30s per user

**Query parameters**:
| Param | Type | Default |
|---|---|---|
| `cursor` | UUID | null |
| `limit` | int | 20 (max 50) |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "cluster_id": "uuid",
        "label": "Personality Quiz",
        "card_style": "stacked_cards",
        "color_accent": "#8B5CF6",
        "preview": {
          "type": "text_cards",
          "snippets": [
            "In what ways do you usually feel most energized and alive?",
            "The comp is of the..."
          ]
        },
        "message_count": 12,
        "last_active": "2026-07-06T08:22:00Z",
        "tags": [],
        "cross_cluster_links": [
          {
            "cluster_id": "uuid",
            "label": "Job search thoughts",
            "edge_weight": 0.87
          }
        ]
      }
    ],
    "pagination": {
      "cursor": "uuid",
      "has_more": true,
      "total_count": 14,
      "limit": 20
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `GET /clusters/{cluster_id}`

Cluster detail — messages with multi-membership context.

**Auth**: Bearer token required  
**Ownership**: `cluster.user_id == auth.user_id`

**Query parameters**:
| Param | Type | Default |
|---|---|---|
| `cursor` | UUID | null |
| `limit` | int | 30 (max 100) |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "cluster": {
      "cluster_id": "uuid",
      "label": "Personality Quiz",
      "card_style": "stacked_cards",
      "color_accent": "#8B5CF6",
      "message_count": 12,
      "cross_cluster_links": [
        {
          "cluster_id": "uuid",
          "label": "Job search thoughts",
          "edge_weight": 0.87,
          "shared_message_count": 3
        }
      ]
    },
    "items": [
      {
        "message_id": "uuid",
        "content": "In what ways do you usually feel most energized and alive?",
        "role": "user",
        "created_at": "2026-07-06T09:00:00Z",
        "membership_weight": 0.94,
        "is_partial_member": false,
        "also_in_clusters": [
          {
            "cluster_id": "uuid",
            "cluster_label": "Career thoughts",
            "membership_weight": 0.71
          }
        ]
      }
    ],
    "pagination": {
      "cursor": "uuid",
      "has_more": true,
      "total_count": 12,
      "limit": 30
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `POST /clusters`

Manually create a cluster.

**Auth**: Bearer token required  
**Idempotency**: Required  
**Rate limit**: 20 req/user/day

**Request body**:
```json
{
  "label": "My custom cluster",
  "color_accent": "#6D28D9"
}
```

**Validation**:
| Field | Rules |
|---|---|
| `label` | required, 1–200 chars |
| `color_accent` | optional, `#[0-9A-Fa-f]{6}` regex |

**Response `201`**: Cluster object with `is_manual: true`

---

### `PATCH /clusters/{cluster_id}`

Rename or recolor.

**Auth**: Bearer token required  
**Ownership**: Verified

**Request body** (all optional):
```json
{
  "label": "New name",
  "color_accent": "#EC4899"
}
```

**Response `200`**: Updated cluster object

---

### `DELETE /clusters/{cluster_id}`

Delete cluster. Messages reassigned automatically via Celery task.

**Auth**: Bearer token required  
**Ownership**: Verified

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "deleted": true,
    "messages_queued_for_reassignment": 12,
    "reassignment_job_id": "celery-task-uuid"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

---

# 5. Events

**Router**: `app/routers/events.py`  
**Service**: `app/services/event_service.py`

### Data Models
```python
class Event(Base):
    __tablename__ = "events"
    id                  = Column(UUID, primary_key=True, default=uuid4)
    user_id             = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    title               = Column(String(200), nullable=False)
    emoji               = Column(String(10), nullable=True)
    date_start          = Column(Date, nullable=False)
    date_end            = Column(Date, nullable=True)
    status              = Column(Enum("upcoming","past","cancelled"), default="upcoming")
    linked_cluster_id   = Column(UUID, ForeignKey("clusters.id"), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

class EventPanel(Base):
    __tablename__ = "event_panels"
    id          = Column(UUID, primary_key=True, default=uuid4)
    event_id    = Column(UUID, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    type        = Column(Enum("plans","trips","invited","custom"), nullable=False)
    label       = Column(String(100), nullable=False)
    color       = Column(String(7), nullable=True)
    sort_order  = Column(Integer, default=0)

class EventPanelItem(Base):
    __tablename__ = "event_panel_items"
    id                  = Column(UUID, primary_key=True, default=uuid4)
    panel_id            = Column(UUID, ForeignKey("event_panels.id", ondelete="CASCADE"))
    user_id             = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    text                = Column(String(500), nullable=True)
    done                = Column(Boolean, default=False)
    image_url           = Column(String(2000), nullable=True)
    location            = Column(String(500), nullable=True)
    person_name         = Column(String(200), nullable=True)
    person_node_id      = Column(UUID, ForeignKey("nodes.id"), nullable=True)
    sort_order          = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
```

---

### `GET /events`

**Auth**: Bearer token required  
**Rate limit**: 200 req/user/day

**Query parameters**:
| Param | Type | Default |
|---|---|---|
| `status` | enum | `upcoming` |
| `limit` | int | 20 (max 50) |
| `cursor` | UUID | null |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "event_id": "uuid",
        "title": "Christmas party!!Yay!",
        "emoji": "🎄",
        "date_start": "2026-12-24",
        "date_end": "2026-12-28",
        "date_label": "24 Dec - 28 Dec",
        "status": "upcoming",
        "panels": [
          {
            "panel_id": "uuid",
            "type": "plans",
            "label": "Plans",
            "color": "#1E3A5F",
            "sort_order": 0,
            "items": [
              {
                "item_id": "uuid",
                "text": "Buy groceries",
                "done": false,
                "sort_order": 0
              }
            ]
          },
          {
            "panel_id": "uuid",
            "type": "trips",
            "label": "Trips",
            "color": "#1A3A2A",
            "sort_order": 1,
            "items": [
              {
                "item_id": "uuid",
                "text": "Route to cabin",
                "image_url": "https://cdn.akam.app/media/uuid.jpg",
                "location": null,
                "done": false
              }
            ]
          },
          {
            "panel_id": "uuid",
            "type": "invited",
            "label": "Invited",
            "color": "#3B2A1A",
            "sort_order": 2,
            "items": [
              {
                "item_id": "uuid",
                "person_name": "Marie",
                "person_node_id": "uuid",
                "done": false
              }
            ]
          }
        ],
        "linked_cluster_id": "uuid",
        "created_at": "2026-07-01T10:00:00Z",
        "updated_at": "2026-07-05T18:30:00Z"
      }
    ],
    "pagination": {
      "cursor": "uuid",
      "has_more": false,
      "total_count": 2,
      "limit": 20
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `POST /events`

**Auth**: Bearer token required  
**Idempotency**: Required  
**Rate limit**: 50 req/user/day

**Request body**:
```json
{
  "title": "Trip to Namibia",
  "emoji": "🌵",
  "date_start": "2027-03-03",
  "date_end": "2027-03-10",
  "panels": [
    {
      "type": "plans",
      "label": "Plans",
      "items": [
        { "text": "Check visa" },
        { "text": "Book safari" }
      ]
    }
  ]
}
```

**Validation**:
| Field | Rules |
|---|---|
| `title` | required, 1–200 chars |
| `emoji` | optional, max 10 chars |
| `date_start` | required, valid date |
| `date_end` | optional, >= `date_start` |
| `panels` | optional, max 10 panels |
| `panels[].type` | enum: `plans` \| `trips` \| `invited` \| `custom` |
| `panels[].items` | max 100 items per panel |
| `panels[].items[].text` | max 500 chars |
| `panels[].items[].image_url` | validated against CDN allowlist if provided |

**Response `201`**: Full event object

---

### `PATCH /events/{event_id}`

**Auth**: Bearer token required  
**Ownership**: `event.user_id == auth.user_id`

**Request body** (all optional):
```json
{
  "title": "Updated title",
  "emoji": "🎉",
  "date_start": "2027-03-03",
  "date_end": "2027-03-12",
  "status": "upcoming"
}
```

**Response `200`**: Updated event object (without panels — fetch separately)

---

### `DELETE /events/{event_id}`

**Auth**: Bearer token required  
**Ownership**: Verified  
**Cascade**: Deletes all panels and items

**Response `200`**:
```json
{
  "status": "success",
  "data": { "deleted": true, "event_id": "uuid" },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `POST /events/{event_id}/panels`

Add a panel to an event.

**Auth**: Bearer token required  
**Ownership**: `event.user_id == auth.user_id`

**Request body**:
```json
{
  "type": "invited",
  "label": "Invited",
  "color": "#3B2A1A"
}
```

**Response `201`**: Panel object (empty items array)

---

### `POST /events/{event_id}/panels/{panel_id}/items`

Add an item to a panel.

**Auth**: Bearer token required  
**Ownership**: Verified through event → panel → item chain

**Request body (plans item)**:
```json
{ "text": "Pack sunscreen", "done": false }
```

**Request body (trips item)**:
```json
{
  "text": "Wildlife drive",
  "image_url": "https://cdn.akam.app/media/uuid.jpg",
  "location": "Etosha National Park"
}
```

**Request body (invited item)**:
```json
{
  "person_name": "Marie",
  "person_node_id": "uuid"
}
```

**Response `201`**: Panel item object

---

### `PATCH /events/{event_id}/panels/{panel_id}/items/{item_id}`

Update item (check off, rename).

**Auth**: Bearer token required  
**Ownership**: Verified through full chain

**Request body** (all optional):
```json
{ "done": true, "text": "Buy groceries" }
```

**Response `200`**: Updated item object

---

### `DELETE /events/{event_id}/panels/{panel_id}/items/{item_id}`

**Auth**: Bearer token required  
**Ownership**: Verified

**Response `200`**: `{ "deleted": true }`

---

### `POST /events/{event_id}/link`

Link event to a memory cluster.

**Auth**: Bearer token required  
**Ownership**: Both event and cluster verified

**Request body**:
```json
{
  "cluster_id": "uuid",
  "node_id": "uuid"
}
```

**Response `200`**: `{ "linked": true }`

---

---

# 6. Nudges — Proactive AI

**Router**: `app/routers/nudges.py`  
**Service**: `app/services/nudge_service.py`  
**Background**: `app/workers/tasks/nudge_tasks.py`

### Data Model
```python
class Nudge(Base):
    __tablename__ = "nudges"
    id                  = Column(UUID, primary_key=True, default=uuid4)
    user_id             = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    type                = Column(Enum(
                            "relationship_drift","pattern_insight","memory_unlock",
                            "event_reminder","sunday_digest","brainrot_warning",
                            "proactive_question"), nullable=False)
    priority            = Column(Enum("high","medium","low"), default="medium")
    title               = Column(String(200), nullable=False)
    body                = Column(Text, nullable=False)
    person_node_id      = Column(UUID, ForeignKey("nodes.id"), nullable=True)
    cluster_id          = Column(UUID, ForeignKey("clusters.id"), nullable=True)
    pattern_id          = Column(UUID, nullable=True)
    cta_primary_json    = Column(JSONB, nullable=True)
    cta_secondary_json  = Column(JSONB, nullable=True)
    deep_link           = Column(String(500), nullable=True)
    action_taken        = Column(String(50), nullable=True)
    shown               = Column(Boolean, default=False)
    shown_at            = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    expires_at          = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_nudges_user_shown", "user_id", "shown"),
    )
```

---

### `GET /nudges`

Fetch pending nudges for current session (shown as bottom sheets).

**Auth**: Bearer token required  
**Rate limit**: 100 req/user/day

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "nudge_id": "uuid",
        "type": "relationship_drift",
        "priority": "high",
        "title": "Arjun misses you",
        "body": "You haven't talked about Arjun in 45 days. Last time, he mentioned he was applying for his MSc.",
        "person_node_id": "uuid",
        "cluster_id": null,
        "pattern_id": null,
        "cta_primary": {
          "label": "Brief me",
          "action": "open_briefing",
          "payload": { "person_node_id": "uuid" }
        },
        "cta_secondary": {
          "label": "Dismiss",
          "action": "dismiss",
          "payload": null
        },
        "deep_link": "akam://briefing?person_id=uuid",
        "created_at": "2026-07-06T09:00:00Z",
        "expires_at": "2026-07-07T09:00:00Z"
      }
    ],
    "pagination": {
      "cursor": null,
      "has_more": false,
      "total_count": 1,
      "limit": 10
    },
    "unread_count": 1
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `POST /nudges/{nudge_id}/action`

Record user interaction with a nudge.

**Auth**: Bearer token required  
**Ownership**: `nudge.user_id == auth.user_id`

**Request body**:
```json
{
  "action": "cta_primary"
}
```

**Validation**: `action` enum: `cta_primary` \| `cta_secondary` \| `dismiss`

**Response `200`**:
```json
{
  "status": "success",
  "data": { "recorded": true, "nudge_id": "uuid" },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `GET /nudges/history`

**Auth**: Bearer token required

**Query parameters**: `limit` (default 20, max 50), `cursor`

**Response `200`**: Paginated list of past nudges with `action_taken` and `shown_at`

---

### `GET /nudges/preferences`

**Auth**: Bearer token required

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "enabled": true,
    "max_per_day": 2,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "timezone": "Asia/Kolkata",
    "types_enabled": {
      "relationship_drift": true,
      "pattern_insight": true,
      "memory_unlock": true,
      "event_reminder": true,
      "sunday_digest": true,
      "brainrot_warning": true,
      "proactive_question": true
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `PATCH /nudges/preferences`

**Auth**: Bearer token required

**Request body** (all optional):
```json
{
  "max_per_day": 3,
  "quiet_hours_start": "23:00",
  "timezone": "Asia/Kolkata",
  "types_enabled": { "brainrot_warning": false }
}
```

**Response `200`**: Updated preferences object

---

### `POST /nudges/screentime`

Flutter app reports daily screen time. Backend evaluates brainrot_warning.

**Auth**: Bearer token required  
**Rate limit**: 5 req/user/day (once per screen-time reporting window)

**Request body**:
```json
{
  "date": "2026-07-06",
  "total_minutes": 312,
  "social_media_minutes": 148,
  "akam_minutes": 18,
  "app_breakdown": [
    { "app_name": "Instagram", "minutes": 72 },
    { "app_name": "YouTube", "minutes": 54 }
  ]
}
```

**Validation**:
| Field | Rules |
|---|---|
| `date` | required, ISO date, not future, not older than 7 days |
| `total_minutes` | required, 0–1440 |
| `social_media_minutes` | required, 0–1440 |
| `akam_minutes` | required, 0–1440 |
| `app_breakdown[].app_name` | max 100 chars, strip null bytes |
| `app_breakdown[].minutes` | 0–1440 |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "nudge_triggered": true,
    "nudge_id": "uuid",
    "nudge_body": "You've spent 148 minutes on social media today. Your real relationships are waiting."
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

---

# 7. Briefing

**Router**: `app/routers/briefing.py`  
**Service**: `app/services/briefing_service.py`  
**Cache**: Redis, TTL 6h, invalidated on new message mentioning person

---

### `GET /briefing`

**Auth**: Bearer token required  
**Rate limit**: 50 req/user/day  
**Cache**: `briefing:{user_id}:{node_id}` → 6h TTL

**Query parameters**:
| Param | Type | Rules |
|---|---|---|
| `query` | string | optional, fuzzy person name search, max 200 chars |
| `node_id` | UUID | optional, exact node lookup |
| `force_refresh` | bool | default false, bypasses Redis cache |

*One of `query` or `node_id` required.*

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "person": {
      "node_id": "uuid",
      "name": "Rahul",
      "relationship_score": 0.82,
      "score_label": "Strong",
      "score_delta": "+0.06",
      "last_mentioned_days_ago": 1
    },
    "summary": "Rahul recently got a job offer from a Bangalore startup and is weighing a relocation decision.",
    "last_discussed": [
      "Job offer from Bangalore startup",
      "Stressed about relocation",
      "Asked for apartment broker contact"
    ],
    "open_promises": [
      {
        "promise_id": "uuid",
        "text": "You said you'd send the broker contact",
        "mentioned_days_ago": 3,
        "source_message_id": "uuid"
      }
    ],
    "patterns": [
      "You feel motivated after talking to Rahul about career topics"
    ],
    "watch_for": "He may be anxious about relocation — avoid pressing for a decision.",
    "conversation_starters": [
      "How's the Bangalore decision going?",
      "Did the offer terms improve?"
    ],
    "cached": false,
    "generated_at": "2026-07-06T10:30:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `GET /briefing/people`

Recent people chips for briefing search screen.

**Auth**: Bearer token required

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "node_id": "uuid",
        "name": "Rahul",
        "relationship_score": 0.82,
        "last_mentioned_days_ago": 1
      }
    ],
    "pagination": {
      "cursor": null,
      "has_more": false,
      "total_count": 6,
      "limit": 6
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

---

# 8. Search

**Router**: `app/routers/search.py`  
**Service**: `app/services/search_service.py`

---

### `POST /search`

Semantic search across messages and clusters.

**Auth**: Bearer token required  
**Rate limit**: 100 req/user/day, 20 req/user/min

**Request body**:
```json
{
  "query": "what Rahul said about the job",
  "scope": "all",
  "cluster_id": null,
  "limit": 5
}
```

**Validation**:
| Field | Rules |
|---|---|
| `query` | required, 1–500 chars, strip null bytes |
| `scope` | enum: `all` \| `messages` \| `clusters` \| `events` |
| `cluster_id` | optional UUID, ownership verified if provided |
| `limit` | 1–20, default 5 |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "result_id": "uuid",
        "type": "message",
        "content_preview": "Rahul mentioned he got the job offer from the Bangalore startup",
        "relevance_score": 0.94,
        "created_at": "2026-06-28T14:00:00Z",
        "cluster_badges": [
          { "cluster_id": "uuid", "label": "Career conversations" },
          { "cluster_id": "uuid", "label": "Conversations with Rahul" }
        ],
        "message_id": "uuid"
      }
    ],
    "pagination": {
      "cursor": null,
      "has_more": false,
      "total_count": 3,
      "limit": 5
    },
    "query_language": "en"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

---

# 9. Weekly Digest

**Router**: `app/routers/digest.py`  
**Background**: `app/workers/tasks/digest_tasks.py` (Sunday 8pm, user timezone)  
**Cache**: Redis, TTL 24h

---

### `GET /digest/weekly`

**Auth**: Bearer token required  
**Rate limit**: 20 req/user/day

**Query parameters**:
| Param | Type | Default |
|---|---|---|
| `week` | string | current ISO week (e.g. `2026-W27`) |

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "week_label": "Jun 30 – Jul 6",
    "week": "2026-W27",
    "stats": {
      "memories_added": 23,
      "people_mentioned": 8,
      "conversations": 31
    },
    "relationships": {
      "strengthening": [
        {
          "node_id": "uuid",
          "name": "Amma",
          "score": 0.94,
          "delta": "+0.06",
          "delta_direction": "up"
        }
      ],
      "needs_attention": [
        {
          "node_id": "uuid",
          "name": "Arjun",
          "score": 0.61,
          "delta": "-0.09",
          "delta_direction": "down"
        }
      ]
    },
    "top_pattern": {
      "pattern_id": "uuid",
      "text": "You talked about Akam 6 times this week — more than any other topic."
    },
    "memory_unlock": {
      "message_id": "uuid",
      "text": "3 months ago you said you wanted to read Sapiens. You haven't mentioned it since.",
      "cta_label": "Tell Akam about it now"
    },
    "generated_at": "2026-07-06T20:00:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

---

# 10. User & Preferences

**Router**: `app/routers/user.py`

---

### `GET /user/me`

**Auth**: Bearer token required

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "name": "Ramanand R",
    "language": "en",
    "device_platform": "android",
    "member_since": "2026-07-01",
    "graph_stats": {
      "total_nodes": 847,
      "total_edges": 2341,
      "total_clusters": 34,
      "total_messages": 1204,
      "strongest_connection": "Amma",
      "most_active_topic": "Akam app"
    }
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `PATCH /user/me`

**Auth**: Bearer token required

**Request body** (all optional):
```json
{
  "name": "Ramanand R",
  "language": "ml"
}
```

**Response `200`**: Updated user object

---

### `PATCH /user/preferences`

**Auth**: Bearer token required

**Request body** (all optional):
```json
{
  "language": "ml",
  "timezone": "Asia/Kolkata",
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "08:00",
  "sunday_digest_enabled": true,
  "nudges_per_day": 2
}
```

**Validation**:
| Field | Rules |
|---|---|
| `timezone` | Valid IANA timezone string |
| `quiet_hours_start` | `HH:MM` format |
| `quiet_hours_end` | `HH:MM` format |
| `nudges_per_day` | 0–5 |

**Response `200`**: Updated preferences object

---

### `POST /user/export`

Request full data export (async).

**Auth**: Bearer token required  
**Rate limit**: 2 req/user/day

**Response `202`**:
```json
{
  "status": "success",
  "data": {
    "export_id": "uuid",
    "status": "processing",
    "estimated_minutes": 2
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

---

### `GET /user/export/{export_id}`

Poll export status.

**Auth**: Bearer token required  
**Ownership**: `export.user_id == auth.user_id`

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "export_id": "uuid",
    "status": "ready",
    "download_url": "https://cdn.akam.app/exports/signed-uuid.json",
    "expires_at": "2026-07-07T10:00:00Z",
    "file_size_bytes": 204800
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Download URL: pre-signed S3/R2 URL, single-use, 24h TTL

---

### `DELETE /user/data`

Permanently delete all user data.

**Auth**: Bearer token required  
**Rate limit**: 1 req/user/day

**Request body**:
```json
{
  "confirmation": "DELETE MY DATA"
}
```

**Validation**: `confirmation` must equal exact string `DELETE MY DATA` — case-sensitive

**Response `200`**:
```json
{
  "status": "success",
  "data": {
    "deletion_ticket_id": "uuid",
    "status": "initiated",
    "steps": {
      "sessions_revoked": true,
      "db_rows_deleted": true,
      "cache_flushed": true,
      "media_deletion_queued": true,
      "backup_purge_queued": true
    },
    "completion_estimated": "2026-08-05T00:00:00Z"
  },
  "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
}
```

**Implementation notes**:
- Steps 1–3 synchronous
- Steps 4–5 async Celery tasks
- User cannot log in after this endpoint is called (`status: deleted`)

---

---

# 11. WebSocket — Real-Time

**Endpoint**: `wss://api.akam.app/v1/ws`  
**Auth**: JWT in query param `?token=<access_token>`  
**Protocol**: JSON messages, UTF-8

### Connection Lifecycle
```
Client connects  → server validates JWT (rejects if invalid/expired/revoked)
                 → server sends `connection_established`
Every 30s        → client sends `ping` → server responds `pong`
Every 15min      → server sends `auth_refresh_required` → client sends `token_refresh`
                 → if no refresh within 60s → server closes connection (code 4001)
On JWT revocation→ server closes all connections for user (code 4002)
```

---

### Server → Client Events

#### `connection_established`
```json
{
  "type": "connection_established",
  "connection_id": "uuid",
  "server_time": "2026-07-06T10:30:00Z",
  "rate_limit": { "messages_per_min": 60 }
}
```

#### `ai_response_token`
Streaming AI response — token by token.
```json
{
  "type": "ai_response_token",
  "request_message_id": "uuid",
  "response_message_id": "uuid",
  "token": "That's exciting news",
  "is_final": false,
  "sequence": 1
}
```
```json
{
  "type": "ai_response_token",
  "request_message_id": "uuid",
  "response_message_id": "uuid",
  "token": "about Rahul!",
  "is_final": true,
  "sequence": 14,
  "full_response": {
    "message_id": "uuid",
    "content": "That's exciting news about Rahul!",
    "display_mode": "bubble",
    "suggested_replies": ["Yes, save it", "Just note he got an offer"],
    "pattern_triggered": false
  }
}
```

#### `graph_updated`
```json
{
  "type": "graph_updated",
  "affected_node_ids": ["uuid", "uuid"],
  "new_edge_count": 2,
  "pattern_triggered": true,
  "pattern_id": "uuid"
}
```

#### `cluster_updated`
```json
{
  "type": "cluster_updated",
  "message_id": "uuid",
  "memberships": [
    { "cluster_id": "uuid", "label": "Daily routines", "weight": 0.82 }
  ]
}
```

#### `nudge_push`
Real-time nudge when app is open.
```json
{
  "type": "nudge_push",
  "nudge": {
    "nudge_id": "uuid",
    "type": "relationship_drift",
    "priority": "high",
    "title": "Arjun misses you",
    "body": "You haven't talked about Arjun in 45 days...",
    "cta_primary": {
      "label": "Brief me",
      "action": "open_briefing",
      "payload": { "person_node_id": "uuid" }
    },
    "cta_secondary": { "label": "Dismiss", "action": "dismiss", "payload": null },
    "deep_link": "akam://briefing?person_id=uuid"
  }
}
```

#### `proactive_message`
AI initiates a conversation.
```json
{
  "type": "proactive_message",
  "message": {
    "message_id": "uuid",
    "content": "You haven't mentioned Arjun in a while — last time, he was applying for his MSc.",
    "role": "assistant",
    "display_mode": "large_question",
    "suggested_replies": ["Yes, brief me", "Not now"],
    "trigger": "relationship_drift",
    "person_node_id": "uuid"
  }
}
```

#### `auth_refresh_required`
```json
{
  "type": "auth_refresh_required",
  "reason": "token_expiring",
  "expires_in_seconds": 300
}
```

#### `connection_closed`
```json
{
  "type": "connection_closed",
  "code": 4001,
  "reason": "token_expired"
}
```

Close codes: `4001` token_expired · `4002` token_revoked · `4003` rate_limited · `4004` server_maintenance

---

### Client → Server Events

#### `ping`
```json
{ "type": "ping", "client_time": "2026-07-06T10:30:00Z" }
```

#### `token_refresh`
```json
{ "type": "token_refresh", "access_token": "eyJ..." }
```

#### `nudge_action`
```json
{ "type": "nudge_action", "nudge_id": "uuid", "action": "cta_primary" }
```

#### `message_typing`
```json
{ "type": "message_typing", "session_date": "2026-07-06" }
```

**WebSocket security**:
- Max message size: 64KB — larger messages → connection closed (code 1009)
- Rate limit: 60 events/min per connection — excess ignored, not closed
- No anonymous connections — JWT required on connect
- JWT re-validated against Redis blacklist every 15 minutes
- Max 2 concurrent WebSocket connections per user

---

---

# 12. Security — FAANG Standard

**Router**: `app/security/`  
**Middleware**: `app/middleware/`

---

## 12.1 Authentication & Token Security

### JWT — RS256

```python
# app/security/jwt.py

from jose import JWTError, jwt
from cryptography.hazmat.primitives import serialization
import uuid, redis

ALGORITHM     = "RS256"
ACCESS_TTL    = 3600          # 1 hour
REFRESH_TTL   = 2592000       # 30 days

def create_access_token(user_id: str, device_id: str) -> str:
    payload = {
        "sub":       user_id,
        "jti":       str(uuid.uuid4()),
        "iat":       int(time.time()),
        "exp":       int(time.time()) + ACCESS_TTL,
        "device_id": device_id,
        "scope":     "user",
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise UnauthorizedException("TOKEN_INVALID")
    
    # Check revocation list
    if redis_client.get(f"revoked_jti:{payload['jti']}"):
        raise UnauthorizedException("TOKEN_REVOKED")
    
    # Check token generation (logout_all support)
    user_gen = redis_client.get(f"token_gen:{payload['sub']}")
    if user_gen and int(user_gen) > payload.get("gen", 0):
        raise UnauthorizedException("TOKEN_REVOKED")
    
    return payload

def revoke_token(jti: str, ttl: int):
    redis_client.setex(f"revoked_jti:{jti}", ttl, "1")
```

### Token Storage
- Access + refresh tokens: **Flutter Secure Storage** only (Android Keystore / iOS Keychain)
- Never: SharedPreferences, SQLite, logs, analytics
- Cleared on uninstall

---

## 12.2 Transport Security

```
TLS version:    1.2 minimum, 1.3 preferred
Certificate:    Let's Encrypt with auto-renewal (90-day certs)
Pinning:        Enforced in Flutter app (SPKI hash pinning)
HTTP:           Redirected 301 → HTTPS at load balancer, then refused
WebSocket:      WSS only (wss://)
```

**FastAPI security middleware**:
```python
# app/middleware/security_headers.py

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options":    "nosniff",
    "X-Frame-Options":           "DENY",
    "Referrer-Policy":           "no-referrer",
    "Cache-Control":             "no-store, max-age=0",
    "Permissions-Policy":        "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy":   "default-src 'none'; frame-ancestors 'none'",
}

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    response.headers["X-Request-ID"] = request.state.request_id
    return response
```

---

## 12.3 Input Validation & Sanitisation

```python
# app/security/sanitiser.py

import re
from html import escape

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above|prior)\s+instructions",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"disregard\s+",
    r"act\s+as\s+",
    r"pretend\s+(you|to)",
    r"jailbreak",
    r"dan\s+mode",
    r"<\|.*?\|>",              # token injection attempts
    r"\[INST\]",               # Llama instruction tokens
    r"###\s*Human:",           # common prompt formats
]

def scan_for_prompt_injection(text: str) -> bool:
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False

def sanitise_string(value: str) -> str:
    value = value.replace("\x00", "")           # strip null bytes
    value = "".join(c for c in value
                    if c.isprintable() or c in "\n\r\t")
    return value.strip()

def safe_llm_prompt(system_template: str, user_content: str) -> list[dict]:
    """
    Always uses separate message roles.
    User content NEVER placed in system role.
    Hard separator prevents context escape.
    """
    sanitised = sanitise_string(user_content)
    sanitised = sanitised.replace("{", "{{").replace("}", "}}")
    return [
        {"role": "system", "content": system_template},
        {"role": "user",   "content": f"---USER INPUT---\n{sanitised}\n---END USER INPUT---"},
    ]
```

**Field-level validation rules enforced in Pydantic schemas**:

| Field | Max length | Pattern | Extra |
|---|---|---|---|
| `content` (message) | 10,000 | any unicode | null byte strip, injection scan |
| `label` | 200 | any unicode | null byte strip |
| `query` (search) | 500 | any unicode | null byte strip |
| `name` | 100 | `[\w\s\-']+` | strip control chars |
| `title` (event) | 200 | any unicode | null byte strip |
| `fcm_token` | 500 | `[A-Za-z0-9\-_:]+` | strict allowlist |
| `language` | 2 | `en\|ml` | enum only |
| `color_accent` | 7 | `#[0-9A-Fa-f]{6}` | regex enforced |
| `image_url` | 2000 | HTTPS only | CDN allowlist: `cdn.akam.app` |
| UUID fields | 36 | UUID v4 regex | validated before any DB lookup |
| `confirmation` | 14 | exact string | case-sensitive equality |

**Audio file validation**:
```python
MAGIC_BYTES = {
    b"\x52\x49\x46\x46": "audio/wav",
    b"\x1A\x45\xDF\xA3": "audio/webm",
    b"\x4F\x67\x67\x53": "audio/ogg",
}

def validate_audio_magic(content: bytes) -> str:
    for magic, mime_type in MAGIC_BYTES.items():
        if content[:len(magic)] == magic:
            return mime_type
    # Check M4A (variable offset)
    if content[4:8] == b"ftyp":
        return "audio/x-m4a"
    raise ValidationError("UNSUPPORTED_MEDIA", "Audio format not supported")
```

---

## 12.4 Object-Level Authorisation (IDOR Prevention)

**FastAPI dependency — enforced on every resource endpoint**:
```python
# app/security/permissions.py

async def verify_node_ownership(
    node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Node:
    node = await db.execute(
        select(Node).where(
            Node.id == node_id,
            Node.user_id == current_user.id   # ownership always scoped
        )
    )
    node = node.scalar_one_or_none()
    if not node:
        raise EntityNotFoundException("ENTITY_NOT_FOUND")   # same 404 for missing AND forbidden
    return node

# Same pattern for: cluster, event, panel, panel_item, nudge, message
# Router usage:
@router.get("/graph/nodes/{node_id}")
async def get_node(node: Node = Depends(verify_node_ownership)):
    ...
```

**404 vs 403 policy**: Always return `404 ENTITY_NOT_FOUND` for both "doesn't exist" and "belongs to another user". Prevents enumeration of other users' resource IDs.

**PostgreSQL Row-Level Security (defence in depth)**:
```sql
ALTER TABLE nodes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE edges    ENABLE ROW LEVEL SECURITY;
ALTER TABLE clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE nudges   ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation ON nodes
  USING (user_id = current_setting('app.current_user_id', true)::uuid);
-- Repeated for all tables above
```

---

## 12.5 Rate Limiting

**Three-layer enforcement**:
1. **nginx** — IP-level coarse limiting (DDoS protection)
2. **FastAPI middleware** — per-user fine-grained limiting (Redis sliding window)
3. **Celery** — AI call quotas enforced before dispatching to Gemini

```python
# app/middleware/rate_limit.py

async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    burst: int = 0
) -> RateLimitResult:
    """Sliding window rate limit using Redis sorted sets."""
    now = time.time()
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zadd(key, {str(uuid4()): now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)
    _, _, count, _ = await pipe.execute()

    remaining = max(0, limit - count)
    reset = int(now + window_seconds)

    if count > limit + burst:
        raise RateLimitException(limit, remaining, reset)

    return RateLimitResult(limit=limit, remaining=remaining, reset=reset)
```

**Complete rate limit table**:

| Endpoint | Per user/day | Per user/min | Burst | Per IP/min |
|---|---|---|---|---|
| `POST /auth/register` | — | — | 3 | 5 |
| `POST /auth/refresh` | 50 | 10 | 5 | 20 |
| `POST /auth/logout` | 20 | 5 | 3 | 10 |
| `POST /auth/logout_all` | 2 | 1 | 1 | 5 |
| `POST /chat/messages` | 100 | 20 | 10 | — |
| `POST /chat/messages/voice` | 20 | 5 | 3 | — |
| `POST /chat/messages/branch` | 200 | 30 | 15 | — |
| `GET /briefing` | 50 | 10 | 5 | — |
| `POST /search` | 100 | 20 | 10 | — |
| `GET /graph` | 200 | 30 | 20 | — |
| `POST /nudges/screentime` | 5 | 2 | 2 | — |
| `POST /user/export` | 2 | 1 | 1 | — |
| `DELETE /user/data` | 1 | 1 | 1 | — |
| All other GETs | 500 | 60 | 30 | — |
| WebSocket events (client→server) | — | 60/connection | — | — |

**IP block policy**: 5 consecutive `429` from same IP within 60s → Redis block for 15 min → Logged for analysis

---

## 12.6 Brute Force & Enumeration Prevention

```python
# Timing-safe token comparison — prevents timing attacks
import hmac

def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())

# UUID v4 for all resource IDs — prevents sequential enumeration
# Never: integer auto-increment IDs

# Identical error timing for 404 vs 403
# Both sleep minimum 50ms before returning to prevent timing enumeration
async def verify_ownership_with_timing_protection(node_id, user_id, db):
    start = time.monotonic()
    result = await db.execute(select(Node).where(
        Node.id == node_id, Node.user_id == user_id
    ))
    node = result.scalar_one_or_none()
    elapsed = time.monotonic() - start
    min_response = 0.050  # 50ms minimum
    if elapsed < min_response:
        await asyncio.sleep(min_response - elapsed)
    if not node:
        raise HTTPException(status_code=404, detail="ENTITY_NOT_FOUND")
    return node
```

---

## 12.7 Data Privacy

### AI/Gemini data handling
- User content never logged server-side beyond structured error traces (no message content in logs)
- Gemini API called server-side only — API key never exposed to Flutter client
- Audio files stored in temp memory only, never written to disk or object storage, deleted within 60 seconds of receiving STT response
- Gemini response content validated — if AI response leaks system prompt content → discard + re-prompt + alert

### Deletion guarantee (5-step)
```
Step 1 [sync]:  Revoke all JWT sessions (Redis blacklist)
Step 2 [sync]:  PostgreSQL cascade delete (nodes, edges, clusters, events, nudges, patterns, relationship_scores, messages)
Step 3 [sync]:  Redis cache flush for user namespace
Step 4 [async, <24h]: CDN media files deleted (signed delete requests)
Step 5 [async, <30d]: Cold storage backup purge
```

### Export security
- Export files: JSON, signed S3/R2 URL, single-use, 24h expiry
- Export URL never stored in DB — generated on demand, delivered once

---

## 12.8 Infrastructure Security

```yaml
# Secrets management — never hardcoded
# All via environment variables (Railway/Render secret injection)

Required environment variables:
  DATABASE_URL:           postgresql+asyncpg://...
  REDIS_URL:              redis://...
  JWT_PRIVATE_KEY:        -----BEGIN RSA PRIVATE KEY----- (2048-bit minimum)
  JWT_PUBLIC_KEY:         -----BEGIN PUBLIC KEY-----
  GEMINI_API_KEY:         AIza...
  FCM_SERVICE_ACCOUNT:    {...json...}
  CDN_BASE_URL:           https://cdn.akam.app
  ALLOWED_ORIGINS:        https://akam.app
  SENTRY_DSN:             https://...
```

**Dependency security**:
```bash
# CI pipeline — build fails on any of these
pip-audit --requirement requirements.txt    # Python CVE scan
safety check -r requirements.txt            # additional CVE database
bandit -r app/ -ll                          # Python SAST (high/medium severity)
```

**Database hardening**:
- PostgreSQL: not exposed to public internet, VPC-only
- Redis: AUTH password required, not exposed to public internet, VPC-only
- All DB connections over TLS
- PgBouncer connection pooling (max 20 connections per app instance)
- Slow query log: queries > 500ms logged (without query parameters that could contain PII)

---

## 12.9 Structured Logging — What To Log and What Not To Log

```python
# app/middleware/logging.py — structlog configuration

NEVER_LOG = [
    "content",          # message content
    "transcript",       # voice transcript
    "label",            # node labels (could be person names)
    "access_token",     # tokens
    "refresh_token",
    "fcm_token",
    "audio_file",       # binary
    "query",            # search queries
    "body",             # briefing body
]

def sanitise_log_record(record: dict) -> dict:
    return {k: "[REDACTED]" if k in NEVER_LOG else v
            for k, v in record.items()}

# Every request log contains:
# request_id, user_id (hashed SHA-256), endpoint, method,
# status_code, latency_ms, error_code (if any), client_version, device_platform
```

---

## 12.10 OWASP API Security Top 10 (2023) — Full Mitigation Map

| # | Risk | Akam Mitigation |
|---|---|---|
| API1 | Broken Object Level Auth | Per-resource ownership dependency on every endpoint. PostgreSQL RLS as second layer. UUID v4 IDs. |
| API2 | Broken Authentication | RS256 JWT. Refresh token rotation. Redis revocation. 5-failure IP block. Timing-safe comparisons. |
| API3 | Broken Object Property Auth | Pydantic schema with explicit `model_config = {"extra": "forbid"}` — unknown fields rejected |
| API4 | Unrestricted Resource Consumption | Three-layer rate limiting. File size enforced at nginx. Audio deleted in <60s. Daily AI quotas. |
| API5 | Broken Function Level Auth | Scope field in JWT. No admin routes exposed publicly. All routes require Bearer token. |
| API6 | Unrestricted Access to Sensitive Flows | `DELETE /user/data` requires exact string confirmation + 1/day rate limit. Export limited to 2/day. |
| API7 | Server-Side Request Forgery | No user-supplied URLs fetched server-side. CDN URLs validated against allowlist before storage. No outbound HTTP from user input. |
| API8 | Security Misconfiguration | Security headers middleware. No debug endpoints in production. No stack traces in error responses. HSTS preload. |
| API9 | Improper Inventory Management | OpenAPI schema auto-generated from FastAPI. All endpoints documented. `/docs` endpoint disabled in production. |
| API10 | Unsafe Consumption of APIs | Gemini responses validated before returning to client. AI output never trusted as safe — always sanitised. Gemini SDK used (not raw HTTP). |

---

## 12.11 Security Testing Requirements

The test suite (`tests/test_security.py`) must cover:

```python
# IDOR tests — attempt to access another user's resources
def test_cannot_access_another_users_node():
def test_cannot_access_another_users_cluster():
def test_cannot_access_another_users_event():
def test_cannot_access_another_users_nudge():
def test_cannot_access_another_users_message():

# Injection tests
def test_prompt_injection_rejected():
def test_null_byte_stripped():
def test_sql_injection_via_uuid_param():

# Auth tests
def test_expired_token_rejected():
def test_revoked_token_rejected():
def test_logout_all_invalidates_all_sessions():
def test_refresh_token_rotation():

# Rate limit tests
def test_rate_limit_enforced_per_user():
def test_rate_limit_headers_present():
def test_ip_blocked_after_5_consecutive_429s():

# Input validation tests
def test_oversized_content_rejected():
def test_invalid_uuid_param_rejected():
def test_invalid_color_accent_rejected():
def test_future_session_date_rejected():
def test_branch_depth_limit_enforced():

# WebSocket tests
def test_ws_rejects_invalid_token():
def test_ws_closes_on_token_revocation():
def test_ws_rate_limit_per_connection():
def test_ws_max_message_size_enforced():
```

---

---

# 13. Background Jobs (Celery)

**Broker + backend**: Redis  
**Workers**: `app/workers/`

| Task | Trigger | Description |
|---|---|---|
| `process_message_graph` | After every chat message | Embed message, update nodes/edges, tier 1+2 weights |
| `llm_label_edge` | When new edge crosses 0.75 threshold | Single Gemini call to classify edge type |
| `cluster_message` | After every 5 new messages | Soft multi-cluster assignment |
| `recompute_cross_cluster_edges` | After cluster assignment | Geometric mean cross-cluster weights |
| `check_patterns` | After every 5 new messages | Scan for high-weight edge clusters (>0.80) |
| `evaluate_nudges` | Daily, 9am + 6pm + 9pm user timezone | Relationship drift, memory unlock, event reminders |
| `generate_weekly_digest` | Sunday 8pm user timezone | Full digest generation via Gemini |
| `apply_edge_decay` | Daily, 2am | Temporal decay on all edges not reinforced in 7d |
| `recluster_all` | Every 50 new messages | Full re-evaluation of cluster memberships |
| `delete_expired_audio` | Every 5 minutes | Hard-delete any temp audio older than 5 minutes |
| `purge_expired_tokens` | Hourly | Remove expired JTI entries from Redis |
| `compute_relationship_scores` | Daily, 3am | Recompute all relationship health scores |

---

# 14. Database Migrations

All migrations via **Alembic**. Zero manual SQL in production.

```bash
# Create migration
alembic revision --autogenerate -m "add_cluster_edge_table"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Migration files stored in `app/db/migrations/versions/`. Every migration includes both `upgrade()` and `downgrade()` functions.

---

# 15. Environment Variables Reference

```bash
# Required — app will not start without these

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/akam
REDIS_URL=redis://:password@localhost:6379/0
JWT_PRIVATE_KEY_PATH=/run/secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/run/secrets/jwt_public.pem
GEMINI_API_KEY=AIza...
FCM_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Optional — defaults shown

APP_ENV=production                    # development | staging | production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://akam.app
CDN_BASE_URL=https://cdn.akam.app
SENTRY_DSN=                           # empty = Sentry disabled
MAX_UPLOAD_SIZE_MB=10
EMBEDDING_MODEL=multilingual-e5-small
GEMINI_FLASH_MODEL=gemini-1.5-flash
GEMINI_PRO_MODEL=gemini-1.5-pro
REDIS_CACHE_TTL_GRAPH=60
REDIS_CACHE_TTL_BRIEFING=21600        # 6h
REDIS_CACHE_TTL_CLUSTERS=30
CELERY_CONCURRENCY=4
```

---

*Akam API Contract v2.0 — Production Engineering Document*  
*This document is the complete specification for end-to-end backend implementation.*  
*Every endpoint, schema, security control, and background job is defined here.*  
*An agentic code editor consuming this document should produce a fully working, production-ready FastAPI backend without requiring additional clarification.*
