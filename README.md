# SmartFlow

Async RESTful API for rated user feedback, built with Python and Tornado. Users post feedback (a rating from 1 to 5 and an optional note), discuss it in comments and give comments a notation (−1, 0 or +1). Product Managers put feedback into categories, set its status and merge duplicates.

## Try it online

| What | URL |
|---|---|
| **Web UI** | https://smartflow-ui.onrender.com |
| **API documentation (Swagger)** | https://smartflow-cjud.onrender.com/docs |
| Health check | https://smartflow-cjud.onrender.com/api/health |

Both services run on Render's free tier, which puts them to sleep when idle: the **first request can take up to a minute** while they wake up.

The Product Manager features need a PM key. For the hosted version it is shared separately, together with the links above.

## How the work was planned

I split the assignment into user stories (for example *US-03 · Table creation*) and developed each one on its own branch. The board with every story is on Trello: [SmartFlow board](https://trello.com/invite/b/6ac928ffcabaab1e1a028b46/ATTI76b91df616a4bd10e834c43e53c25deeB42FFD10/smartflow).

Note: since this is an MVP for an assessment, I kept the stories short and didn't write formal acceptance criteria. I spent the time on the implementation and its tests instead.


## Run it locally with Docker Compose

The only requirement is [Docker](https://docs.docker.com/get-docker/) with Docker Compose (included in Docker Desktop). No account, configuration file or build is needed: Compose pulls the published images and starts the web UI, the API and a PostgreSQL database.

```bash
git clone https://github.com/dbReis/smartflow.git
cd smartflow
docker compose up
```

The first start downloads the images. The application is ready when the log shows `server_started`. Then open:

| What | URL |
|---|---|
| **Web UI** | http://localhost:8080 |
| **API documentation (Swagger)** | http://localhost:8989/docs |
| Health check | http://localhost:8989/api/health |

**PM key (local): `local-pm-key`.** Enter it in the UI's PM mode, or in Swagger with the **Authorize** button, to use the Product Manager features.

**Stop** with `Ctrl+C`. The data is kept between runs. To start again from an empty database:

```bash
docker compose down -v
```

### What Compose starts

| Service | Image | Role |
|---|---|---|
| `psql` | `postgres:18-alpine` | The database. Its data is stored in the `db-data` volume |
| `smartflow` | [`ddosreis/smartflow`](https://hub.docker.com/r/ddosreis/smartflow) | The API (this repository), on port 8989 |
| `smartflow-ui` | [`ddosreis/smartflow-ui`](https://hub.docker.com/r/ddosreis/smartflow-ui) | The web UI, served by nginx on port 8080. nginx forwards `/api` to the API, so the browser only talks to one origin |

Both images are public on Docker Hub, so they can be pulled without logging in.

To run the API from this repository's code instead of the published image, replace `image: ddosreis/smartflow:1.0.0` with `build: .` in `compose.yaml` and start with `docker compose up --build`.

## About the web UI

The focus of this project is the backend: the API, its data model, its validation and error handling, its tests and its delivery. To make the API easy to try, I built the web UI in React with **Claude**, using **spec-driven development**: I described the API contract (the OpenAPI specification served at `/openapi.json`), the screens and the expected behaviour, and the UI was generated and refined against that specification.

The UI lives in its own repository. Its CI pipeline builds a Docker image (nginx serving the built React app) and pushes it to my public Docker Hub registry as [`ddosreis/smartflow-ui`](https://hub.docker.com/r/ddosreis/smartflow-ui). That same image is the one the `smartflow-ui` service in `compose.yaml` pulls and runs.

The API image is published the same way: this repository's CI runs the linting, unit and integration tests, then builds the image, and pushes it to [`ddosreis/smartflow`](https://hub.docker.com/r/ddosreis/smartflow) for version tags.

## Development

The repository includes a **VS Code dev container** (`.devcontainer/`): open the folder in VS Code and choose **Reopen in Container**. It provides Python 3.12, `uv`, and a PostgreSQL for the tests.

```bash
uv sync                    # install the dependencies
python -m smartflow        # run the API (needs a .env, see below)
pytest tests/unit          # unit tests, no database needed
pytest tests/integration   # integration tests, against the dev container's PostgreSQL
ruff check . && ruff format --check .
```

Running the API outside Docker needs a `.env` file in the project root (never committed):

```
SMARTFLOW_DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
SMARTFLOW_PM_API_KEY=any-long-random-value
```
