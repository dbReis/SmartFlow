# SmartFlow

Async RESTful API for rated user feedback, built with Python and Tornado: users post feedback (rating 1–5, optional note), discuss it in comments and give comments a notation (−1, 0, +1); Product Managers categorise feedback, set its status and merge duplicates.

How it is built, and why, is explained in [ARCHITECTURE.md](ARCHITECTURE.md).

## Run it locally with Docker

The only requirement is [Docker](https://docs.docker.com/get-docker/) (with Docker Compose, included in Docker Desktop). Compose starts the whole application from published images: the web UI, the API and a PostgreSQL database. No account, configuration file or build is needed.

```bash
git clone https://github.com/dbReis/smartflow.git
cd smartflow
docker compose up
```

The first start downloads the images. The application is ready when the log shows `server_started`. Then open:

| What | Where |
|---|---|
| **The web UI** | http://localhost:8080 |
| Interactive API documentation (Swagger) | http://localhost:8888/docs |
| Health check | http://localhost:8888/api/health |

The images are [`ddosreis/smartflow`](https://hub.docker.com/r/ddosreis/smartflow) (API) and [`ddosreis/smartflow-ui`](https://hub.docker.com/r/ddosreis/smartflow-ui) (UI, served by nginx, which forwards `/api` to the API). To run the API from this repository's code instead, replace `image: ddosreis/smartflow:1.0.0` with `build: .` in `compose.yaml` and start with `docker compose up --build`.

**Product Manager features** (status, category, merge, creating categories) need the PM key. Locally it is **`local-pm-key`**: enter it in the UI's PM mode, or in Swagger via **Authorize**. To use your own key instead, start with `SMARTFLOW_PM_API_KEY=your-key docker compose up`.

**Port already in use?** If 8888 or 8080 is taken on your machine, choose other host ports: `SMARTFLOW_API_PORT=8889 SMARTFLOW_UI_PORT=8081 docker compose up`.

**Stop** with `Ctrl+C`. Data is kept between runs; to start again from an empty database:

```bash
docker compose down -v
```

## Try it with curl

```bash
# Post a feedback
curl -X POST localhost:8888/api/feedback -d '{"rating": 2, "note": "Loading is slow"}'

# Comment on it, and rate the comment
curl -X POST localhost:8888/api/feedback/1/comments -d '{"comment": "Same for me on mobile"}'
curl -X POST localhost:8888/api/comments/1/notation -d '{"notation": 1}'

# Browse: the feedback list, then its comments ranked by score
curl localhost:8888/api/feedback
curl localhost:8888/api/feedback/1/comments

# As a Product Manager: close it as solved
curl -X PUT localhost:8888/api/feedback/1/status \
  -H "Authorization: Bearer local-pm-key" -d '{"status": "closed_solved"}'
```

Every error comes back in the same shape, for example `{"error": {"code": 422, "message": "rating: Input should be 1, 2, 3, 4 or 5"}}`.

## Development

The repository includes a **VS Code dev container** (`.devcontainer/`): open the folder in VS Code and choose **Reopen in Container**. It provides Python 3.12, `uv`, and a PostgreSQL for the tests.

```bash
uv sync                    # install dependencies
python -m smartflow        # run the API (needs a .env, see below)
pytest tests/unit          # unit tests, no database needed
pytest tests/integration   # integration tests, against the dev container's PostgreSQL
ruff check . && ruff format --check .
```

Running the API outside Docker needs a `.env` file in the project root (never committed), for example:

```
SMARTFLOW_DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
SMARTFLOW_PM_API_KEY=any-long-random-value
```

All settings are listed in [ARCHITECTURE.md](ARCHITECTURE.md#82-configuration-).
