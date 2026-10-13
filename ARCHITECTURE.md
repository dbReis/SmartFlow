# SmartFlow Architecture

This document explains how SmartFlow is organised, how its parts interact, how the data is modelled, and which assumptions and trade-offs shaped it. It is meant to be read before the code.

Status markers: ✅ implemented · 🚧 planned

---

## 1. Purpose and scope

SmartFlow is an asynchronous REST API that lets users of a web application give **useful rated feedback**: a rating with an optional note, discussed through comments, whose comments are weighted by community notations (−1, 0, +1). It is the API that will be handed over to a front-end team.

| Part | Scope | Status |
|---|---|---|
| **Part 1, User feedback** (required) | Post feedback (rating 1–5, optional note) | ✅ |
| | Comment on a feedback | ✅ |
| | Give a notation (−1, 0, +1) to a comment | ✅ (one-per-user rule 🚧, see §2) |
| | Browse feedback and their comments (`GET` endpoints) | 🚧 |
| **Part 2, Product Manager view** (optional) | Categorise feedback, set a status (open, closed backlog, closed solved, closed rejected), merge similar feedback | 🚧 |

The goal is a **minimum viable product**: a small, correct, well-structured API rather than a large feature set.

---

## 2. Assumptions and interpretations

The assignment leaves some points open. These are the interpretations the implementation follows.

| Topic | Assumption | Why | Status |
|---|---|---|---|
| **Notation values** | Notations are **−1, 0 and +1**. The assignment writes "(+1, 0, 1)", which we read as a typo for −1. | Three distinct values are needed for "mitigating" importance; "+1" and "1" would be the same value. | ✅ |
| **What receives a notation** | Notations are given to **comments**, not to feedback directly. | Part 1 says "give a (+1, 0, 1) notation to other user's comments". | ✅ |
| **Rating** | Required, an integer from **1 (bad) to 5 (very good)**. | Assignment: "a rating (1=bad, 5=very good)". | ✅ |
| **Note** | **Optional** free text. | Assignment: "a note (optional description of the issue)". | ✅ |
| **Comments** | Any number of comments can be posted on any feedback. Blank comments are rejected. | "A user can give several comments or feedback." | ✅ |
| **User identity** | Users will be **identified, not authenticated**: the client sends its user id in an `X-User-Id` header. There is no login. | The assignment does not ask for authentication; identity is still needed for the two rules below. | 🚧 |
| **One notation per user** | A user can give **at most one notation per comment**. | "A user can only give 1 notation." | 🚧 needs user identity |
| **Own comments** | A user cannot give a notation to their own comment. | "Notation to **other** users' comments." | 🚧 needs user identity |
| **Hosting** | The API is hosted on a platform that runs Python services (e.g. Render or Fly.io). GitHub Pages can only host static files, so it can host a front end or the API documentation, not the API itself. | Delivery asks for "a hosted version"; GitHub Pages cannot run a Tornado server. | 🚧 |

---

## 3. Overview

```mermaid
flowchart LR
    client["Front end / API client"] -->|HTTP + JSON| tornado

    subgraph app["SmartFlow (one Python process, one event loop)"]
        tornado["Tornado Application<br/>(routes)"] --> handlers["Handlers<br/>HTTP layer"]
        handlers --> services["Services<br/>business rules"]
        services --> storage["Storage<br/>repositories"]
        schemas["Schemas<br/>request / response shapes"] -.used by.- handlers
        models["Models<br/>table definitions"] -.used by.- storage
        config["Settings<br/>(environment)"] -.-> tornado
        logging["Structured logging<br/>(structlog)"] -.-> tornado
    end

    storage -->|asyncpg, SSL| db[("PostgreSQL<br/>Neon")]
```

The application is split into **layers**. A request travels down through them and the response travels back up. Each layer only talks to the one below it.

| Layer | Folder | Responsibility | Knows about HTTP? | Knows about SQL? |
|---|---|---|---|---|
| **Handlers** | `handlers/` | Parse and validate the request body, open the request's transaction, call a service, turn the result or a domain error into JSON and a status code | Yes | No |
| **Schemas** | `schemas/` | Pydantic models describing what a client may send (`…Create`) and what the API returns (`…Out`) | No | No |
| **Services** | `services/` | Business rules: a comment needs an existing feedback, a notation needs an existing comment; raise domain errors (`services/errors.py`) | No | No |
| **Repositories** | `storage/repository/` | All database access for one table. They `flush` but never `commit`: the caller owns the transaction | No | Yes |
| **Models** | `models/` | SQLAlchemy table definitions and their constraints | No | Declares the schema |

**Why layers:** each rule lives in exactly one place, each layer can be tested on its own (services without HTTP, repositories without services), and the database or the identity mechanism can change without touching the handlers.

**Schemas vs. models.** Both describe data, for different audiences. A model is the **table** (`Feedback` with its `CHECK` constraint). A schema is the **API contract**: `FeedbackCreate` has no `id` because the client never sends one; `FeedbackOut` has one because the API returns it. The same `IntEnum`s (`RatingValue`, `NotationValue`) are used by both, so the API and the database agree on the allowed values.

---

## 4. Project layout

```
src/smartflow/
├── __main__.py              ✅ Entry point: settings → logging → engine → connection check → tables → app → serve
├── app.py                   ✅ make_app(): builds the Tornado Application and its route table
├── config.py                ✅ Settings, read from SMARTFLOW_* environment variables and .env
├── log_config.py            ✅ structlog setup (plain console / JSON) and the access log
├── openapi.py               ✅ OpenAPI 3.1 spec built from the Pydantic schemas
├── handlers/
│   ├── base.py              ✅ BaseHandler: session injection, JSON body parsing, JSON errors
│   ├── docs.py              ✅ GET /openapi.json (Swagger UI at /docs comes from swagger-ui-py)
│   ├── health.py            ✅ GET /api/health
│   ├── feedback.py          ✅ POST /api/feedback
│   ├── comments.py          ✅ POST /api/feedback/{id}/comments
│   └── notation.py          ✅ POST /api/comments/{id}/notation
├── schemas/                 ✅ feedback.py, comment.py, notation.py (…Create / …Out), error.py (error shape)
├── services/
│   ├── errors.py            ✅ FeedbackNotFoundError, CommentNotFoundError
│   └── *_service.py         ✅ feedback, comment, notation
├── storage/
│   ├── database.py          ✅ Async engine, session factory, startup connection check, table creation
│   └── repository/          ✅ feedback, comment, notation repositories
└── models/                  ✅ Feedback, Comment, Notation tables (see §5)
tests/                       ✅ pytest suite (logging ✅, API / services / storage 🚧)
.github/workflows/           ✅ ci.yml: lint, unit tests, integration tests, Docker build
```

The project uses the **src layout** (`src/smartflow/`), so the tests run against the installed package rather than loose files.

---

## 5. Data model

### 5.1 Entity-relationship diagram

```mermaid
erDiagram
    FEEDBACK ||--o{ COMMENT : "is discussed by"
    COMMENT  ||--o{ NOTATION : "is rated by"

    FEEDBACK {
        int      id PK
        smallint rating "1..5, required"
        text     note "optional"
    }
    COMMENT {
        int      id PK
        int      feedback_id FK "→ feedback.id, cascade"
        text     comment "the comment text"
    }
    NOTATION {
        int      id PK
        int      comment_id FK "→ comment.id, cascade"
        smallint notation "-1, 0 or +1"
    }
```

- One **feedback** has zero or more **comments**.
- One **comment** has zero or more **notations**.
- A comment's **score** is `SUM(notation)` over its notations. A feedback's comments can be ordered by score to surface the most useful discussion.

### 5.2 Tables

**`feedback`**, a rated statement about the application

| Column | Type | Rules | Status |
|---|---|---|---|
| `id` | integer | primary key | ✅ |
| `rating` | smallint | required; `CHECK (rating IN (1, 2, 3, 4, 5))` | ✅ |
| `note` | text | optional (nullable) | ✅ |
| `user_id` | varchar(64) | the author, from `X-User-Id` | 🚧 |
| `created_at` | timestamptz | set by the database (`now()`) | 🚧 |

**`comment`**, a message in the discussion of one feedback

| Column | Type | Rules | Status |
|---|---|---|---|
| `id` | integer | primary key | ✅ |
| `feedback_id` | integer | required; foreign key to `feedback.id`, `ON DELETE CASCADE`; indexed | ✅ |
| `comment` | text | required | ✅ |
| `user_id` | varchar(64) | the author, needed to forbid notations on one's own comment | 🚧 |
| `created_at` | timestamptz | set by the database (`now()`) | 🚧 |

**`notation`**, a −1 / 0 / +1 on one comment

| Column | Type | Rules | Status |
|---|---|---|---|
| `id` | integer | primary key | ✅ |
| `comment_id` | integer | required; foreign key to `comment.id`, `ON DELETE CASCADE` | ✅ |
| `notation` | smallint | required; `CHECK (notation IN (-1, 0, 1))` | ✅ |
| `user_id` | varchar(64) | who gave the notation | 🚧 |
| (table) | | `UNIQUE (comment_id, user_id)`: one notation per user per comment | 🚧 |

### 5.3 Modelling decisions

- **Rules are enforced by the database as well as by the API.** The API validates input to give clear errors (422). The database `CHECK` and foreign-key constraints guarantee the rules regardless of where data comes from, including bugs. Once users are identified, `UNIQUE (comment_id, user_id)` will be the reliable protection against two simultaneous notations by the same user.
- **Ratings and notations are stored as small integers, not PostgreSQL `ENUM`s.** Their meaning is numeric: a comment's score is `SUM(notation)` and a feedback's average is `AVG(rating)`. Python `IntEnum`s (`RatingValue`, `NotationValue`) give the values readable names in code, and the `CHECK` constraints are generated from those enums so the allowed values are defined once.
- **Cascading deletes.** Deleting a feedback deletes its comments, and deleting a comment deletes its notations, inside the database (`ON DELETE CASCADE`). There are no orphaned rows.
- **Predictable constraint names.** A naming convention on `Base.metadata` gives every constraint a stable name (`pk_feedback`, `fk_comment_feedback_id_feedback`, `ck_notation_notation_value`). Errors then name the exact rule that failed, and constraints can be changed later by name.
- **Users are not modelled yet.** When identity is added (§2), `user_id` columns will be plain strings from the `X-User-Id` header, without a `users` table. If authentication is added later, a `users` table can be introduced and those columns turned into foreign keys.
- **Part 2 columns are not created yet.** `status`, `category` (a new table) and `merged_into_id` will be added when the Product Manager view is built.

---

## 6. API

### 6.1 Endpoints

All requests and responses use JSON.

| Method | Path | Body | Success | Errors | Status |
|---|---|---|---|---|---|
| `GET` | `/api/health` | — | `200 {"status": "ok"}` | — | ✅ |
| `GET` | `/docs` | — | Swagger UI (interactive documentation) | — | ✅ |
| `GET` | `/openapi.json` | — | OpenAPI 3.1 spec of the endpoints below | — | ✅ |
| `POST` | `/api/feedback` | `{"rating": 1–5, "note": "…" (optional)}` | `201` + feedback | 400, 422 | ✅ |
| `POST` | `/api/feedback/{feedback_id}/comments` | `{"comment": "…"}` | `201` + comment | 400, 404 (feedback), 422 | ✅ |
| `POST` | `/api/comments/{comment_id}/notation` | `{"notation": -1, 0 or 1}` | `201` + notation | 400, 404 (comment), 422 | ✅ |
| `GET` | `/api/feedback` | — | list of feedback | — | 🚧 |
| `GET` | `/api/feedback/{feedback_id}/comments` | — | comments with their score | 404 | 🚧 |

Successful `POST`s return **201 Created** with the created resource and a `Location` header. Resource ids in paths are matched with `\d{1,9}`: digits only, and small enough for a PostgreSQL `INTEGER`. Any other id matches no route and returns 404.

**Nested URLs.** A comment always belongs to one feedback, so it is created under it (`/api/feedback/{id}/comments`) and the feedback id comes from the path, not the body. The same applies to notations under a comment.

### 6.2 Documentation (OpenAPI / Swagger)

The API is described by an **OpenAPI 3.1** spec (`openapi.py`). Request and response shapes are generated from the same Pydantic schemas the handlers validate with, so the documentation cannot drift from the real validation rules; only the paths are listed by hand.

The running app serves it at **`/openapi.json`**, and an interactive **Swagger UI** at **`/docs`**. The Swagger UI page and its assets come from the `swagger-ui-py` package (no CDN), registered with one call in `app.py`. The spec has no `servers` entry, so Swagger's "Try it out" calls the server the page was opened from: no CORS setup is needed.

### 6.3 Errors

Every error returned by an API handler has the same shape:

```json
{"error": {"code": 422, "message": "rating: Input should be 1, 2, 3, 4 or 5"}}
```

| Code | When | Example message |
|---|---|---|
| **400** | The body is not valid JSON | `Request body must be valid JSON` |
| **404** | A referenced resource does not exist | `Feedback not found`, `Comment not found` |
| **405** | The URL exists but not for this method | `Method Not Allowed` |
| **422** | Valid JSON, invalid values. One `field: problem` per invalid field, joined with `;` | `rating: Field required; ratting: Extra inputs are not permitted` |
| **500** | Unexpected server error. The response never contains a traceback; it goes to the logs | `Internal Server Error` |

**How errors flow through the layers.** Validation happens in `BaseHandler.parse_body`, which raises `HTTPError(400/422)`. Services know nothing about HTTP: they raise **domain errors** (`FeedbackNotFoundError`, `CommentNotFoundError`), and the handler translates them into `HTTPError(404)`. Tornado then calls `BaseHandler.write_error`, the single place where every error body is written. Services check that a referenced resource exists *before* inserting, so a missing feedback is a clear 404 instead of a foreign-key violation surfacing as a 500.

Unknown fields are rejected (`extra="forbid"`), so a typo such as `"ratting"` is reported instead of silently ignored.

---

## 7. Request lifecycle

What happens when a comment is posted:

```mermaid
sequenceDiagram
    participant C as Client
    participant T as Tornado
    participant H as CommentsHandler
    participant S as comment_service
    participant R as Repositories
    participant DB as PostgreSQL

    C->>T: POST /api/feedback/42/comments {"comment": "Same here"}
    T->>H: new handler, initialize(session_maker), prepare()
    H->>H: parse_body(CommentCreate) → 400 / 422 on bad input
    H->>H: open transaction (session_maker.begin())
    H->>S: create_comment(session, 42, data)
    S->>R: get_feedback(42)
    R->>DB: SELECT (await: the event loop serves other requests meanwhile)
    alt feedback missing
        S-->>H: FeedbackNotFoundError
        H-->>C: 404 {"error": {"code": 404, "message": "Feedback not found"}}
    else feedback exists
        S->>R: add_comment(42, "Same here")
        R->>DB: INSERT + flush (id assigned)
        S-->>H: Comment
        H->>H: end of transaction block → COMMIT
        H-->>C: 201 Created + CommentOut JSON
    end
    T->>T: access log line (method, path, status)
```

**Asynchronous model.** Tornado serves every request on **one thread** with an event loop. All database access is asynchronous (SQLAlchemy's async API over the `asyncpg` driver), so while one request waits for PostgreSQL, the loop keeps serving others. A blocking call anywhere in a handler would freeze every request, which is why synchronous database drivers are not used.

**Sessions and transactions.** The application has **one engine** (one connection pool). Each request opens **one session and one transaction** with `session_maker.begin()`: it commits when the block ends successfully and rolls back if anything inside raises, so a request never leaves half its changes behind. Repositories only `flush` (send the SQL and get generated ids); they never commit. The session factory is injected into handlers through Tornado's `initialize()` hook rather than imported globally, so tests can provide their own database.

---

## 8. Startup and configuration

### 8.1 Startup sequence (`__main__.py`) ✅

1. Read **settings** from the environment.
2. Configure **logging**, first, so that everything after it is formatted consistently.
3. Create the async **engine** (this does not connect yet).
4. **Connection check**: open one connection and run `SELECT 1`. If the database is unreachable or the credentials are wrong, the process stops here with a logged error instead of starting and failing on the first request ("fail fast").
5. **Create missing tables** (`Base.metadata.create_all`). Tables that already exist are left unchanged.
6. Create the **session factory** and build the **Tornado application** with it.
7. Listen on the configured host and port.
8. On shutdown (Ctrl+C), **dispose** of the engine so pooled connections are closed cleanly.

### 8.2 Configuration ✅

All configuration comes from environment variables with the `SMARTFLOW_` prefix, read and validated at startup by `pydantic-settings`. A local `.env` file (never committed) can provide them during development. Invalid values stop the application at startup with a clear message.

| Variable | Default | Purpose |
|---|---|---|
| `SMARTFLOW_DATABASE_URL` | **required** | `postgresql+asyncpg://user:password@host/dbname` |
| `SMARTFLOW_DB_ECHO` | `false` | Log every SQL statement (debugging) |
| `SMARTFLOW_HOST` | `0.0.0.0` | Interface to listen on |
| `SMARTFLOW_PORT` | `8888` | Port to listen on |
| `SMARTFLOW_DEBUG` | `false` | Tornado debug mode (auto-reload) |
| `SMARTFLOW_LOG_LEVEL` | `DEBUG` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SMARTFLOW_LOG_FORMAT` | `console` | `console` (readable) or `json` (production) |

### 8.3 Environments

| Environment | Database | Notes |
|---|---|---|
| Local development | Neon **dev** branch | URL in the developer's `.env` |
| Tests and CI | PostgreSQL container | 🚧 Throwaway database, no secrets needed |
| Production | Neon **prod** branch | URL stored as a secret on the hosting platform |

**PostgreSQL everywhere.** The same database type is used in every environment, so tests exercise the same behaviour as production (types, constraints, SQL dialect) and the code has no database-specific branches.

**Neon specifics** handled in `storage/database.py`: SSL is required; `pool_pre_ping` detects connections dropped while a Neon branch was suspended; a 10-second connection timeout keeps a wrong host from blocking startup for a minute. The **direct** (non-pooled) Neon endpoint is used, because the pooled one breaks `asyncpg`'s prepared statements.

---

## 9. Logging ✅

All logs, including Tornado's and SQLAlchemy's own, go through **structlog** with a single format:

- **console** (development): `2026-10-10T11:27:14Z info method=GET path=/api/health status=200`, with the level coloured when writing to a terminal.
- **json** (production): one JSON object per line, ready to be filtered by field in a log platform.

Events are logged as an **event name plus fields** (`log.info("comment_created", comment_id=7, feedback_id=42)`), never as formatted sentences, so they stay searchable. Each module has its own logger (`structlog.get_logger(__name__)`).

| Level | Used for | Examples |
|---|---|---|
| **DEBUG** | Internal steps, for debugging | `settings_loaded`, `database_engine_created`, `routes_registered`, `request_received`, `request_body_parsed`, `feedback_inserted` |
| **INFO** | Normal events worth recording | `database_connected` (with connection time), `tables_ready`, `server_started`, `feedback_created`, `comment_created`, `request_validation_failed` |
| **WARNING** | Requests rejected by the API (4xx) | the access-log line of a 404 or 422 |
| **ERROR** | Server-side failures that need fixing | `database_connection_failed`, `tables_creation_failed`, 5xx access-log lines |

Client mistakes are never logged as errors: an error log always means something on the server needs attention. Every request produces one access-log line whose level follows the status code. **Secrets and user content are never logged**: not the database URL, and not the text of notes or comments (only ids and, for feedback, whether a note exists).

---

## 10. Testing strategy 🚧

| Layer | What the tests prove | Database |
|---|---|---|
| **API** (largest share) | Every endpoint: success response and **each documented error code** (§6.3) | Real PostgreSQL (container) |
| **Services** | Business rules (resource existence, and later the one-notation-per-user and own-comment rules) | Fake repositories, no database |
| **Storage** | Queries, ordering and pagination, and that the constraints really reject bad data | Real PostgreSQL (container) |

Tests never use the Neon databases. CI runs linting (ruff), formatting checks and the test suite on every push.

---

## 11. Key decisions and trade-offs

| Decision | Alternatives considered | Reason | Trade-off |
|---|---|---|---|
| **Tornado** with fully async I/O | — | Required by the assignment; suited to many concurrent, I/O-bound requests | Every library in the request path must be async |
| **PostgreSQL on Neon** | Supabase, SQLite | Relational data with constraints and transactions; Neon is plain PostgreSQL with a free tier that does not expire and branches for dev/prod | First request after idle waits ~1 s while Neon resumes |
| **SQLAlchemy 2 (async ORM)** | Raw SQL with `asyncpg` | Models describe the schema once; queries are built in Python; standard tooling | An extra library to learn |
| **Pydantic schemas** for requests and responses | Manual checks in handlers | Declarative validation, clear per-field errors, unknown fields rejected | — |
| **PostgreSQL in every environment** | SQLite for tests | Tests match production; no database-specific code paths | Tests and local runs need a PostgreSQL container |
| **One transaction per request, owned by the handler** | Commit inside repositories | All writes of a request succeed or fail together | Handlers must open the transaction |
| **Domain errors translated in handlers** | Services raising HTTP errors | Services stay independent of HTTP and reusable | One `try/except` per handler |
| **One error shape `{code, message}`** | Structured per-field error lists | Simple and consistent for every client | Clients cannot map errors to fields without reading the message |
| **Header identification (`X-User-Id`)** (planned) | JWT authentication | Not required by the assignment; keeps the MVP small; isolated in one place so it can be replaced | Clients can claim any identity |
| **`create_all` for the schema** | Alembic migrations | Simpler for the MVP | Cannot alter existing tables (see §12) |
| **structlog** | stdlib `logging`, loguru | Structured fields, JSON in production, works with Tornado's and SQLAlchemy's stdlib loggers | Some configuration code |
| **pydantic-settings** | `os.getenv` | One validated list of settings; fails at startup on bad values | — |

---

## 12. Known limitations and future work

- **No user identity yet.** Notations are not tied to a user, so the "one notation per user" and "no notation on one's own comment" rules are not enforced: any client can give any number of notations. Next step: read `X-User-Id` in `BaseHandler`, add `user_id` columns and `UNIQUE (comment_id, user_id)` on `notation`.
- **No authentication.** Even with `X-User-Id`, identity would come from a header the client controls. A later step: JWT (PyJWT) with a `users` table; only the identity-reading code in `BaseHandler` would change.
- **No read endpoints yet.** Feedback and comments can be created but not listed (`GET`), so the "browse" part of the assignment is still open.
- **No schema migrations.** Tables are created with `Base.metadata.create_all` on every server start, which creates missing tables but never alters existing ones. A table that already exists with an older shape (for example, missing a column added to the model later) is skipped **silently**: startup succeeds and the first query using the new column fails. During development, the workaround is to drop the affected tables on the dev branch and restart. Before any schema change on a database that holds data (for example the Part 2 columns), versioned migrations with **Alembic** should be introduced.
- **Unknown URLs return Tornado's default HTML 404**, not the JSON error shape of §6.3. A catch-all handler (`default_handler_class`) extending `BaseHandler` would make every response JSON.
- **No automated API tests yet.** They need the PostgreSQL test container (§10).
- **Single process.** One Tornado process serves all requests. Scaling out means running several instances behind a load balancer; the application keeps no state in memory, so this needs no code change.
- **Rate limiting and abuse protection** are out of scope for the MVP.
