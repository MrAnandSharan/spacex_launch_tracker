# Technical Documentation — SpaceX Launch Tracker

A FastAPI service that fetches SpaceX v4 data with an `httpx` client, caches responses in Redis, exposes JSON APIs for analytics, and serves simple HTML dashboards via Jinja2 templates. Tests use `pytest` + `pytest-asyncio`. The app is containerized with Docker and orchestrated with a `docker-compose` including Redis for caching.


## Features
- Filter launches by date range, rocket name, success/failure, and launch site
- Statistics:
  - Success rate by rocket
  - Launches per launchpad
  - Launch frequency by month/year
- CSV/JSON export
- HTML dashboards (Jinja2)
- Redis caching with TTL
- Async client, type-hinted models, unit tests

## Tech Stack
FastAPI · httpx · Redis · Pydantic v2 · Jinja2 · Pytest · Docker

---

### Run with Docker (recommended)

```bash
docker-compose up --build
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Run locally (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
## Project Structure

```
app/
  cache.py               # Redis
  config.py              # pydantic Settings
  connection.py          # shared instances
  main.py                # FastAPI app + lifespan
  spacex/
    client.py            # httpx client + Redis caching
    dependency.py        # DI provider
    routers/
      data.py            # data manageent routes
      statistics.py      # statistics routes
    schema.py            # schema for validation
    utils.py             # filtering, pagination, export, stats
templates/
  data.html              # launch dashboard
  statistics.html        # statistics dashboard
tests/
  test_spacex.py         # unit tests
```

## Testing

```bash
pytest -v
```

## Endpoints

### Launches

* `GET /api/v1/launch`
* `GET /api/v1/launch/dashboard`
* `GET /api/v1/launch/export?format=csv`
* `GET /api/v1/launch/export?format=json`

### Statistics

* `GET /api/v1/statistics/success-rate`
* `GET /api/v1/statistics/launch-site`
* `GET /api/v1/statistics/frequency`
* `GET /api/v1/statistics/dashboard`

Visit `http://127.0.0.1:8000/docs` for the Swagger.


## High-level architecture

* **Presentation**

  * FastAPI routers: `data.py: /api/v1/launch/*` and `statistics.py: /api/v1/statistics/*`
  * HTML dashboards: `templates/data.html` and `templates/statistics.html`
* **Application / Domain**

  * `spacex.utils`: functions for filtering, pagination, exports, calculation.
  * `spacex.schema`: Pydantic models for validation.
* **Integration**

  * `spacex.client.SpaceXClient`: async `httpx` client with Redis caching
  * `cache.RedisCache`: Redis wrapper with JSON serialization and TTL
  * `spacex.dependency`: Dependency injection provider
* **Bootstrapping**

  * `main.py`: app factory, lifespan hook (ping/close Redis), router wiring
  * `config.Settings`: Initializing `.env` values.

---

## Key design decisions

1. **FastAPI + Pydantic**

   * I needed to call external endpoints hence I wished this to be lightweight and powerful enough to do the job. Also adding the schema helped me to validate the request and response models adding validation.
2. **`httpx` + Redis caching**

   * Caching added to avoid hitting endpoint repeatedly and also used `https` instead of `requests` package because `httpx` sipports async features and hence we can call the external endpoints in async manner. 
   * Added the initialization of caching in lifespan because I didnt want to start and stop redis connection all the time for each case. 
3. **Separation of concerns**

   * `SpaceXClient` only fetches data. All business logic (filtering, stats, pagination, export) is in `utils.py`.
4. **Dependency Injection**

   * Singleton `SpaceXClient` via `Depends(get_spacex_client)` keeps handlers clean and testable.
5. **Failure & observability**

   * Consistent `try/except` → `HTTPException` with 5xx on internal errors structured logs via `logging`. Logging can be extended by adding more use cases. For example, what if connection goes down to external api or something else. Generally I have added smtp email settings for monitoring database failures.
6. **Container**

   * `Dockerfile` + `docker-compose.yml` uses just one command to start development environment including Redis. 

---

## Code walkthrough

### Boot & configuration

* `app/main.py`

  * Registers routers:

    * `app.include_router(data_router, prefix="/api/v1/launch")`
    * `app.include_router(statistics_router, prefix="/api/v1/statistics")`
  * `lifespan`: `redis_cache.client.ping()` on start and `client.close()` on shutdown.
* `app/config.py`

  * `Settings(BaseSettings)`: uses the contents from `.env` file.
* `app/connection.py`

  * Creates a shared `RedisCache`.

### Integration: Redis & SpaceX

* `app/cache.py` — `RedisCache`

  * `set(key, value, ex=ttl)`: Sets the value in cache.
  * `get(key)`: Gets the value from cache and logs failures.
  * `delete`, `clear_all`: For admin features, currently we are using TTL for invalidation.
* `app/spacex/client.py` — `SpaceXClient`

  * `fetch(endpoint)`:

    1. Check Redis by URL key
    2. If cache miss then `httpx.AsyncClient().get()` and store result in cache with TTL


### Use-case logic

* `app/spacex/utils.py`

  * **`get_launches()`**

    * Fetches `launches`, `rockets`, `launchpads`, and joins by ID
    * Applies filters:

      * Date window (UTC normalized)
      * Rocket name (case-insensitive, via joined `Rocket.name`)
      * Success flag (`success is True/False`)
      * Launch site (via joined `Launchpad.name`)
  * **`paginate()`**

    * Slices `data` and builds `next`/`previous` links from the request URL & query params.
  * **`get_rocket_succes_rate()`**

    * Counts `total` & `success` per rocket ID, maps to rocket names, computes `success_rate = success/total * 100`.
  * **`get_launch_site_rate()`**

    * Counts launches per launchpad name.
  * **`get_launch_frequency()`**

    * Calculates launches by `YYYY` and `YYYY-MM`.
  * **`export_object()`**

    * `json`: attachment `launches.json`
    * `csv`: attachment `launches.csv` with header`id,name,date_utc,rocket,success,launchpad`
---

## Error handling & logging

* All core operations in `utils.py` and `client.py` are wrapped with `try/except`.
* Failures log with `logger.exception(...)` (stack traces preserved), then raise `HTTPException(500, ...)`.
* Redis errors are caught inside `RedisCache` and logged and then the methods return `None`/`False` instead of raising to keep app running.

---

## Caching strategy

* Write policy: Sttoring API response with key being the full request URL.
* Expiry: `CACHE_TTL_SECONDS` (from `.env`), default being 60 seconds.
* Invalidation: TTL-based only (no manual versioning). `clear_all()` exists for admin related stuffs.

---

## Testing

* `tests/test_spacex.py`:
    * `get_launches` filtering (date, rocket name, success)
    * `get_rocket_succes_rate` math (totals and rates)
    * `get_launch_site_rate` counts per pad
    * `get_launch_frequency` monthly/yearly buckets


