# SmartFlow Architecture

This document explains how SmartFlow is organised, how its parts interact, how the data is modelled, and which assumptions and trade-offs shaped it. It is meant to be read before the code.

Status markers: ✅ implemented · 🚧 planned

---

## 1. Purpose and scope

SmartFlow is an asynchronous REST API that lets users of a web application give **useful rated feedback**: a rating with an optional note, discussed through comments, whose comments are weighted by community notations (−1, 0, +1). It is the API that will be handed over to a front-end team.

| Part | Scope | Status |
|---|---|---|
| **Part 1, User feedback** (required) | Post feedback (rating 1–5, optional note), browse feedback, comment on feedback, give a notation to other users' comments | 🚧 data model ✅, endpoints 🚧 |
| **Part 2, Product Manager view** (optional) | Categorise feedback, set a status (open, closed backlog, closed solved, closed rejected), merge similar feedback | 🚧 |

The goal is a **minimum viable product**: a small, correct, well-structured API rather than a large feature set.

---

## 2. Assumptions and interpretations

The assignment leaves some points open. These are the interpretations the implementation follows.

| Topic | Assumption | Why |
|---|---|---|
| **Notation values** | Notations are **−1, 0 and +1**. The assignment writes "(+1, 0, 1)", which we read as a typo for −1. | Three distinct values are needed for "mitigating" importance; "+1" and "1" would be the same value. |
| **What receives a notation** | Notations are given to **comments**, not to feedback directly. | Part 1 says "give a (+1, 0, 1) notation to other user's comments". |
| **One notation per user** | A user can give **at most one notation per comment**. Giving another one replaces the previous one. | "A user can only give 1 notation." Replacing (rather than rejecting) lets users change their mind. |
| **Own comments** | A user **cannot** give a notation to their own comment. | "Notation to **other** users' comments." |
| **Rating** | Required, an integer from **1 (bad) to 5 (very good)**. | Assignment: "a rating (1=bad, 5=very good)". |
| **Note** | **Optional** free text. | Assignment: "a note (optional description of the issue)". |
| **Comments** | A user can post **any number** of comments, on any feedback. | "A user can give several comments or feedback." |
| **User identity** | Users are **identified, not authenticated**: the client sends its user id in an `X-User-Id` header (and later `X-User-Role` (`user` or `pm`)). There is no login. | The assignment does not ask for authentication; identity is still needed for the rules above. See §10. |
| **Hosting** | The API is hosted on a platform that runs Python services (e.g. Render or Fly.io). GitHub Pages can only host static files, so it can host a front end or the API documentation, not the API itself. | Delivery asks for "a hosted version"; GitHub Pages cannot run a Tornado server. |

---

## 3. Overview

```mermaid
flowchart LR
    client["Front end / API client"] -->|HTTP + JSON<br/>X-User-Id header| tornado

    subgraph app["SmartFlow (one Python process, one event loop)"]
        tornado["Tornado Application<br/>(routes)"] --> handlers["Handlers<br/>HTTP layer"]
        handlers --> services["Services<br/>business rules"]
        services --> storage["Storage<br/>repositories, sessions"]
        models["Models<br/>table definitions"] -.used by.- storage
        config["Settings<br/>(environment)"] -.-> tornado
        logging["Structured logging<br/>(structlog)"] -.-> tornado
    end

    storage -->|asyncpg, SSL| db[("PostgreSQL<br/>Neon")]
```

The application is split into **layers**. A request travels down through them and the response travels back up. Each layer only talks to the one below it.

| Layer | Folder | Responsibility | Knows about HTTP? | Knows about SQL? |
|---|---|---|---|---|
| **Handlers** | `handlers/` | Parse and validate the request, read the user identity, call a service, turn the result or error into JSON and a status code | Yes | No |
| **Services** | `services/` | Business rules: one notation per user, no notation on own comments, merge rules (Part 2), transaction boundaries | No | No |
| **Storage** | `storage/` | Engine, sessions and repositories: all database access | No | Yes |
| **Models** | `models/` | SQLAlchemy table definitions and their constraints | No | Declares the schema |

**Why layers:** each rule lives in exactly one place, each layer can be tested on its own (services without a database, repositories without HTTP), and the database or the identity mechanism can change without touching the handlers.

---

## 4. Project layout

```
src/smartflow/
├── __main__.py        ✅ Entry point: settings → logging → engine → connection check → tables → app → serve
├── app.py             ✅ make_app(): builds the Tornado Application and its route table
├── config.py          ✅ Settings, read from SMARTFLOW_* environment variables and .env
├── log_config.py      ✅ structlog setup (plain console / JSON) and the access log
├── handlers/          🚧 HTTP layer (health endpoint ✅, feature endpoints 🚧)
├── services/          🚧 Business rules
├── storage/
│   └── database.py    ✅ Async engine, session factory, startup connection check, table creation
└── models/            ✅ Feedback, Comment, Notation tables (see §5)
tests/                 ✅ pytest suite (logging ✅, API / services / storage 🚧)
.github/workflows/     ✅ CI: lint, formatting, tests
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
        string   user_id "author (planned)"
        datetime created_at "planned"
    }
    COMMENT {
        int      id PK
        int      feedback_id FK "→ feedback.id, cascade"
        text     comment "the comment text"
        string   user_id "author (planned)"
        datetime created_at "planned"
    }
    NOTATION {
        int      id PK
        int      comment_id FK "→ comment.id, cascade"
        string   user_id "who gave it"
        smallint notation "-1, 0 or +1"
    }
```

- One **feedback** has zero or more **comments**.
- One **comment** has zero or more **notations**, at most one per user.
- A comment's **score** is `SUM(notation)` over its notations. A feedback's comments can be ordered by score to surface the most useful discussion.

### 5.2 Tables

**`feedback`**, a rated statement about the application

| Column | Type | Rules | Status |
|---|---|---|---|
| `id` | integer | primary key | ✅ |
| `rating` | smallint | required; `CHECK (rating IN (1, 2, 3, 4, 5))` | ✅ |
| `note` | text | optional (nullable) | ✅ |
| `user_id` | varchar(64) | required; the author, from `X-User-Id` | 🚧 |
| `created_at` | timestamptz | set by the database (`now()`) | 🚧 |

**`comment`**, a message in the discussion of one feedback

| Column | Type | Rules | Status |
|---|---|---|---|
| `id` | integer | primary key | ✅ |
| `feedback_id` | integer | required; foreign key to `feedback.id`, `ON DELETE CASCADE`; indexed | ✅ |
| `comment` | text | required | ✅ |
| `user_id` | varchar(64) | required; the author, needed to forbid notations on one's own comment | 🚧 |
| `created_at` | timestamptz | set by the database (`now()`) | 🚧 |

**`notation`**, one user's −1 / 0 / +1 on one comment

| Column | Type | Rules | Status |
|---|---|---|---|
| `id` | integer | primary key | ✅ |
| `comment_id` | integer | required; foreign key to `comment.id`, `ON DELETE CASCADE` | ✅ |
| `user_id` | varchar(64) | required; who gave the notation | ✅ |
| `notation` | smallint | required; `CHECK (notation IN (-1, 0, 1))` | ✅ |
| (table) | | `UNIQUE (comment_id, user_id)`: one notation per user per comment | ✅ |

### 5.3 Modelling decisions

- **Rules are enforced by the database as well as by the API.** The API validates input to give clear errors (422). The database `CHECK`, `UNIQUE` and foreign-key constraints guarantee the rules regardless of where data comes from, including bugs and concurrent requests. In particular, `UNIQUE (comment_id, user_id)` is the only reliable protection against two simultaneous notations by the same user.
- **Ratings and notations are stored as small integers, not PostgreSQL `ENUM`s.** Their meaning is numeric: a comment's score is `SUM(notation)` and a feedback's average is `AVG(rating)`. Python `IntEnum`s (`RatingValue`, `NotationValue`) give the values readable names in code, and the `CHECK` constraints are generated from those enums so the allowed values are defined once.
- **Cascading deletes.** Deleting a feedback deletes its comments, and deleting a comment deletes its notations, inside the database (`ON DELETE CASCADE`). There are no orphaned rows.
- **Predictable constraint names.** A naming convention on `Base.metadata` gives every constraint a stable name (`pk_feedback`, `fk_comment_feedback_id_feedback`, `uq_notation_comment_id_user_id`, `ck_notation_notation_value`). Errors then name the exact rule that failed, and constraints can be changed later by name.
- **`user_id` is a plain string, without a `users` table.** Users are identified by the `X-User-Id` header (§2). If authentication is added later, a `users` table can be introduced and `user_id` columns turned into foreign keys.
- **Part 2 columns are not created yet.** `status`, `category` (a new table) and `merged_into_id` will be added when the Product Manager view is built.

---

## 6. Request lifecycle

What happens for a typical request, for example posting a comment:

```mermaid
sequenceDiagram
    participant C as Client
    participant T as Tornado
    participant H as Handler
    participant S as Service
    participant R as Repository
    participant DB as PostgreSQL

    C->>T: POST /api/feedback/42/comments (X-User-Id: alice)
    T->>H: new handler instance, initialize(session_maker)
    H->>H: validate JSON body, read X-User-Id
    H->>S: add_comment(feedback_id=42, user_id="alice", text)
    S->>R: open a session (one per request)
    R->>DB: INSERT ... (await, the event loop serves other requests meanwhile)
    DB-->>R: new row
    S->>S: commit
    S-->>H: Comment
    H-->>C: 201 Created + JSON
    T->>T: access log line (method, path, status)
```

**Asynchronous model.** Tornado serves every request on **one thread** with an event loop. All database access is asynchronous (SQLAlchemy's async API over the `asyncpg` driver), so while one request waits for PostgreSQL, the loop keeps serving others. A blocking call anywhere in a handler would freeze every request, which is why synchronous database drivers are not used.

**Sessions.** The application has **one engine** (one connection pool) and creates **one session per request** from a session factory. The factory is injected into handlers through Tornado's `initialize()` hook rather than imported globally, so tests can provide their own database.

---

## 7. Startup and configuration

### 7.1 Startup sequence (`__main__.py`) ✅

1. Read **settings** from the environment.
2. Configure **logging**, first, so that everything after it is formatted consistently.
3. Create the async **engine** (this does not connect yet).
4. **Connection check**: open one connection and run `SELECT 1`. If the database is unreachable or the credentials are wrong, the process stops here with a logged error instead of starting and failing on the first request ("fail fast").
5. **Create missing tables** (`Base.metadata.create_all`). Tables that already exist are left unchanged.
6. Create the **session factory** and build the **Tornado application** with it.
7. Listen on the configured host and port.
8. On shutdown (Ctrl+C), **dispose** of the engine so pooled connections are closed cleanly.

### 7.2 Configuration ✅

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

### 7.3 Environments

| Environment | Database | Notes |
|---|---|---|
| Local development | Neon **dev** branch | URL in the developer's `.env` |
| Tests and CI | PostgreSQL container | 🚧 Throwaway database, no secrets needed |
| Production | Neon **prod** branch | URL stored as a secret on the hosting platform |

**PostgreSQL everywhere.** The same database type is used in every environment, so tests exercise the same behaviour as production (types, constraints, SQL dialect) and the code has no database-specific branches.

**Neon specifics** handled in `storage/database.py`: SSL is required; `pool_pre_ping` detects connections dropped while a Neon branch was suspended; a 10-second connection timeout keeps a wrong host from blocking startup for a minute. The **direct** (non-pooled) Neon endpoint is used, because the pooled one breaks `asyncpg`'s prepared statements.

---

## 8. Logging ✅

All logs, including Tornado's and SQLAlchemy's own, go through **structlog** with a single format:

- **console** (development): `2026-10-10T11:27:14Z info method=GET path=/api/health status=200`, with the level coloured when writing to a terminal.
- **json** (production): one JSON object per line, ready to be filtered by field in a log platform.

Events are logged as an **event name plus fields** (`log.info("server_started", port=8888)`), never as formatted sentences, so they stay searchable. Every request produces one access-log line whose level follows the status code (info < 400, warning 4xx, error 5xx). Secrets such as the database URL are never logged.

---

## 9. Testing strategy 🚧

| Layer | What the tests prove | Database |
|---|---|---|
| **API** (largest share) | Every endpoint: success response and **each documented error code** (400, 401, 403, 404, 409, 422) | Real PostgreSQL (container) |
| **Services** | Business rules (own-comment rule, notation replacement, merge rules) | Fake repositories, no database |
| **Storage** | Queries, ordering and pagination, and that the constraints really reject bad data | Real PostgreSQL (container) |

Tests never use the Neon databases. CI runs linting (ruff), formatting checks and the test suite on every push.

---

## 10. Key decisions and trade-offs

| Decision | Alternatives considered | Reason | Trade-off |
|---|---|---|---|
| **Tornado** with fully async I/O | — | Required by the assignment; suited to many concurrent, I/O-bound requests | Every library in the request path must be async |
| **PostgreSQL on Neon** | Supabase, SQLite | Relational data with constraints and transactions; Neon is plain PostgreSQL with a free tier that does not expire and branches for dev/prod | First request after idle waits ~1 s while Neon resumes |
| **SQLAlchemy 2 (async ORM)** | Raw SQL with `asyncpg` | Models describe the schema once; queries are built in Python; standard tooling | An extra library to learn |
| **PostgreSQL in every environment** | SQLite for tests | Tests match production; no database-specific code paths | Tests and local runs need a PostgreSQL container |
| **Header identification (`X-User-Id`)** | JWT authentication | Not required by the assignment; keeps the MVP small; isolated in one place so it can be replaced | Clients can claim any identity |
| **`create_all` for the schema** | Alembic migrations | Simpler for the MVP | Cannot alter existing tables (see §11) |
| **structlog** | stdlib `logging`, loguru | Structured fields, JSON in production, works with Tornado's and SQLAlchemy's stdlib loggers | Some configuration code |
| **pydantic-settings** | `os.getenv` | One validated list of settings; fails at startup on bad values | — |

---

## 11. Known limitations and future work

- **No authentication.** Identity comes from a header the client controls. Next step: JWT (PyJWT) with a `users` table; only the identity-reading code in the handlers' base class would change.
- **No schema migrations.** Tables are created with `Base.metadata.create_all` on every server start, which creates missing tables but never alters existing ones. A table that already exists with an older shape (for example, missing a column added to the model later) is skipped **silently**: startup succeeds and the first query using the new column fails. During development, the workaround is to drop the tables on the dev branch and restart. Before any schema change on a database that holds data (for example the Part 2 columns), versioned migrations with **Alembic** should be introduced.
