# Django Blog REST API

Training project for a Django blog and its Post REST API. The repository contains the work completed for Phases 1 through 5. Phase 5 is implemented in the application and covered by tests. Docker, a live Redis server, and a Celery worker were not started, so those integrations are not described as verified.

| Phase | Status in this repository |
| --- | --- |
| 1. Django Foundations | Partially implemented |
| 2. Django REST Framework | Implemented for the Post API |
| 3. API Architecture & Clean Structure | Partially implemented |
| 4. Advanced Django ORM | Implemented |
| 5. Production & Scaling | Implemented in code and tests. Docker and live Redis/Celery were not started. |

The API is built with Django 5.2 and Django REST Framework. Posts support create, read, update, and delete. Public clients can read posts. Creating, updating, and deleting a post requires a token.

## Phase 1 – Django Foundations

**Status: partially implemented.**

The Django project is `config`, and the application is `blog`.

- `config/settings.py` loads environment variables, configures SQLite, and installs the blog app, Django REST Framework, and token authentication.
- `config/urls.py` routes `/admin/`, `/blog/`, and `/api-token-auth/`.
- `GET /blog/` is a function view that returns the plain-text response `Welcome to my Blog!`.
- `blog/admin.py` exists, and no blog models are registered with the admin site.
- The project has no template directory, form classes, or static-file directory.

### Models and relationships

`blog/models.py` defines four models:

| Model | Fields and relationships |
| --- | --- |
| `Post` | `title` (max length 200), `content`, `created_at` (set on creation), `is_published` (default `False`), optional `author`, and `categories` |
| `Author` | `name` and `email` |
| `AuthorProfile` | One-to-one with `Author` (`related_name="profile"`), `bio`, cascade delete |
| `Category` | `name`, many-to-many with `Post` (`related_name="posts"`) |

`Post.author` is optional (`null=True`, `blank=True`). Primary keys are Django's automatic `BigAutoField`.

### Migrations

| Migration | Change |
| --- | --- |
| `blog/migrations/0001_initial.py` | Creates `Post` |
| `blog/migrations/0002_author_post_author.py` | Creates `Author` and adds the nullable foreign key on `Post` |
| `blog/migrations/0003_authorprofile.py` | Creates `AuthorProfile` |
| `blog/migrations/0004_category_post_categories.py` | Creates `Category` and the many-to-many relationship |

### ORM usage and limits

Application code creates posts, orders them by `id`, and filters them with the custom `published()` and `unpublished()` queryset methods. `Author`, `AuthorProfile`, and `Category` are defined and migrated. They are not used by the API, serializer, service, admin, or tests.

## Phase 2 – Django REST Framework

**Status: implemented for the Post API.**

`PostViewSet` is a `ModelViewSet` registered with a `DefaultRouter` at `api/posts`. The router root view is disabled, so `/blog/` remains the blog home page.

### CRUD

| Method | URL | Access |
| --- | --- | --- |
| `GET` | `/blog/api/posts/` | Public list |
| `POST` | `/blog/api/posts/` | Authenticated create |
| `GET` | `/blog/api/posts/<id>/` | Public retrieve |
| `PUT` | `/blog/api/posts/<id>/` | Authenticated full update |
| `PATCH` | `/blog/api/posts/<id>/` | Authenticated partial update |
| `DELETE` | `/blog/api/posts/<id>/` | Authenticated delete |

The serializer fields are `id`, `title`, `content`, `is_published`, and read-only `created_at`. `author` and `categories` are not exposed.

### Authentication and permissions

`REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` contains only `TokenAuthentication`. The view permission is `IsAuthenticatedOrReadOnly`.

- `GET` requests do not require a token.
- `POST`, `PUT`, `PATCH`, and `DELETE` require `Authorization: Token <token>`.
- A missing or invalid token receives HTTP 401.
- `POST /api-token-auth/` accepts `username` and `password` and returns a token. This is Django REST Framework's built-in token view.

### Pagination, filtering, and search

- Pagination uses page number pagination with `page_size = 2`. The list is ordered by `id`.
- A list response includes `count`, `next`, `previous`, and `results`.
- `?page=` selects a page.
- `?search=` searches `title` and `content`.
- `?is_published=true` returns published posts.
- `?is_published=false` returns unpublished posts.
- These two values are case-insensitive.
- Omitting `is_published` returns all posts.
- Any other value, such as `yes`, returns HTTP 400.

### Serializer validation

- A title containing `spam`, in any letter case, is rejected.
- A title that is exactly equal to the content is rejected.
- Invalid input returns HTTP 400.

### Automated tests

`blog/tests.py` contains `PostApiTests` with 22 tests. They cover public reads, authenticated writes, invalid tokens, validation, partial and full updates, deletion, pagination, search, published filtering, and one request that combines filtering, search, and pagination.

The full blog suite, including the Phase 4 and Phase 5 tests, is described under Testing.

## Phase 3 – API Architecture & Clean Structure

**Status: partially implemented.**

| Piece | What exists |
| --- | --- |
| Service layer | `create_post()` in `blog/services.py` creates a post from `title`, `content`, and `is_published`. `PostViewSet.perform_create()` calls it. Updates and deletes still use the serializer save path. |
| Custom QuerySet | `PostQuerySet.published()` and `PostQuerySet.unpublished()` filter on `is_published`. The list view calls these methods. |
| Custom manager | `PublishedManager` filters to published posts and is attached as `Post.published`. The API uses the queryset methods above. |
| Signals | `log_post_created` writes an INFO log when a post is created. `BlogConfig.ready()` imports the signal module. |
| Logging | The `blog` logger writes to the console at INFO with the format `{levelname} {name} {message}`. |
| Environment variables | `python-dotenv` loads `.env`. `SECRET_KEY` is required. `DEBUG` is `True` only when its value is the text `True`. Phase 5 adds hosts, HTTPS settings, CORS, cache, Celery, and throttle rates. |

Validation remains in the serializer. Published filtering remains in the view. Settings live in one module, `config/settings.py`. Phase 4 tests cover the newer service helpers and queryset methods. `PublishedManager` still has no direct test.

## Phase 4 – Advanced Django ORM

**Status: implemented.**

The Post API response is unchanged. These features live in the models, `blog/expressions.py`, `blog/services.py`, and `Phase4OrmTests`. Migration `blog/migrations/0005_phase4_indexes_and_constraints.py` adds the index and constraints. Migrations `0001` through `0004` were not edited.

| Topic | Implementation |
| --- | --- |
| Indexes | `blog_post_published_id_idx` on `Post (is_published, id)`, matching the filtered list query. |
| Constraints | A post title must be non-empty (`title > ''`). A post title must differ from its content. `Author.email` is unique. `Category.name` is unique. |
| Custom function | `CharLength` calls the database `LENGTH` function. `PostQuerySet.with_title_length()` annotates `title_length`. |
| Raw SQL | `published_post_count_raw()` runs `SELECT COUNT(*)` with the published flag passed as a bound parameter. |
| Performance tuning | `published_post_count()` uses the ORM `count()` method, which is one query. |
| Query optimization | `with_author()` uses `select_related("author")`. `with_categories()` uses `prefetch_related("categories")`. The list endpoint does not use them, because the serializer does not read those relations. |
| Transactions | `create_author_with_profile()` inserts both rows inside `transaction.atomic()`. A failure rolls both back. |
| `select_for_update` | `publish_post()` loads the row with `select_for_update()` inside `transaction.atomic()` and saves `is_published=True`. |
| Bulk operations | `bulk_create_posts()` and `bulk_set_published()` use `bulk_create()` and `bulk_update()`. Neither calls `Model.save()`, and neither sends `pre_save` or `post_save`. `create_post()` is still a single `create()` and still sends the create signal. |

### SQLite limitations

The database engine is still SQLite. These limits are covered by the tests:

- `connection.features.has_select_for_update` is false. Django accepts `select_for_update()` and then omits `FOR UPDATE` from the SQL. The tests check that SQL and the feature flag. They do not claim that a row lock was taken or that another connection was blocked.
- A Django `CheckConstraint` cannot use the `title__length` transform. The non-empty rule is the direct comparison `title > ''`.
- Unique email and category-name checks use SQLite's default case-sensitive comparison.
- Search still uses a leading-wildcard `LIKE`, so the new index does not speed up `?search=`.

`python manage.py makemigrations --check --dry-run` reported `No changes detected`. `python manage.py migrate` reported `No migrations to apply` after `0005` had already been applied. The existing development rows were kept: 6 posts, 1 author, 1 profile, and 1 category.

## Phase 5 – Production & Scaling

**Status: implemented in the application.** The Django test suite covers the settings, the async status view, CORS, the local-memory cache, the Celery task called in-process, and API throttling. It does not start Gunicorn, Uvicorn, Redis, a Celery worker, or Docker.

`STATIC_URL` is set. `STATIC_ROOT` is not.

### Environment and security

`config/environment.py` parses the values. `config/settings.py` applies them.

| Variable | Safe example | Behavior |
| --- | --- | --- |
| `SECRET_KEY` | `replace-with-a-long-random-string` | Required. There is no fallback. |
| `DEBUG` | `True` | On only when the value is the text `True`. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated. Blank means an empty list. `*` is rejected. |
| `USE_HTTPS` | `False` | On only when the value is the text `True`. |
| `SQLITE_PATH` | unset locally | Blank keeps `db.sqlite3`. Docker sets `/data/db.sqlite3`. |

When `USE_HTTPS` is false, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, and `SECURE_HSTS_PRELOAD` are false, and `SECURE_HSTS_SECONDS` is `0`. Local HTTP and the test client keep working.

When `USE_HTTPS` is `True`, those flags turn on and `SECURE_HSTS_SECONDS` is `31536000` (one year). The Docker Compose stack sets `USE_HTTPS` to `False`.

Django's existing middleware still sends `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin`, and `X-Frame-Options: DENY`. No Content-Security-Policy is set.

### WSGI, ASGI, and servers

`WSGI_APPLICATION` is `config.wsgi.application`. `ASGI_APPLICATION` is `config.asgi.application`. The post API stays synchronous.

| Server | Package | Command |
| --- | --- | --- |
| Development | Django | `python manage.py runserver` |
| ASGI | Uvicorn 0.54.0 | `uvicorn config.asgi:application` |
| WSGI | Gunicorn 26.2.0 | `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1` |

Gunicorn cannot start on Windows because it needs Unix process forking. It is the server inside the Linux image. Uvicorn can run on Windows. Neither server was started during this work, so serving HTTP with them is not verified. The tests import both application callables and call the status view through Django's test client.

`GET /blog/api/status/` is an async view. It returns `{"status": "ok"}` and does not query the database. `PostViewSet` is still synchronous.

### CORS

`django-cors-headers` 4.9.0 is installed. `CorsMiddleware` sits after `SecurityMiddleware` and before `CommonMiddleware`.

`CORS_ALLOWED_ORIGINS` is a comma-separated list of origins, such as `http://localhost:3000`. A blank value allows no cross-origin origin. `*` is rejected. `CORS_ALLOW_ALL_ORIGINS` and `CORS_ALLOW_CREDENTIALS` are `False`.

An allowed `Origin` is echoed in `Access-Control-Allow-Origin`. Any other origin gets the normal response without that header.

### Redis caching

The `redis` package is 8.1.0. Django's cache uses it only when `REDIS_URL` is set, for example `redis://127.0.0.1:6379/0`. A blank `REDIS_URL` uses the local-memory cache. Tests use that backend and do not open a Redis connection. A running Redis server was not tested.

`cached_published_post_count()` stores the published-post count at `blog:published-post-count` for 60 seconds. The value is the same for every caller, including zero. Post changes can leave it stale until the timeout. `published_post_count()` and the post list are not cached.

### Celery

Celery is 5.6.3. `config/celery.py` reads settings with the `CELERY_` prefix, and `config/__init__.py` loads that app.

A blank `CELERY_BROKER_URL` uses the in-memory broker `memory://` and runs tasks in-process. A URL such as `redis://127.0.0.1:6379/0` leaves tasks for a worker.

`log_published_post_count` reads the published-post count and logs it. It does not write to the database. Creating a post does not dispatch it. The synchronous `log_post_created` signal still runs in the request.

On Windows, a worker needs the solo pool:

```powershell
celery -A config worker --loglevel=info --pool=solo
```

That command was not run. No worker consumed a task from Redis.

### Rate limits

Django REST Framework's `AnonRateThrottle` and `UserRateThrottle` protect the post API. Counters live in the default Django cache.

| Client | Variable | Default |
| --- | --- | --- |
| Anonymous, including an invalid token | `ANON_THROTTLE_RATE` | `60/minute` |
| Authenticated | `USER_THROTTLE_RATE` | `240/minute` |

A blank variable uses the default. A custom value looks like `120/hour`. The two counters are separate. `GET /blog/api/status/` is not throttled. Several processes share counters only when `REDIS_URL` points at one Redis server. That shared setup was not tested.

### Docker

`Dockerfile` builds a Python 3.11 image, installs `requirements.txt`, and runs Gunicorn as one worker. `.dockerignore` keeps `.env`, the virtual environment, Git metadata, and local databases out of the build context.

`docker-compose.yml` defines three services:

| Service | Role |
| --- | --- |
| `web` | Migrates, then serves Gunicorn on port 8000. |
| `redis` | Cache on database 0 and the Celery broker on database 1. |
| `worker` | `celery -A config worker --loglevel=info --concurrency=1`, after the web health check. The worker does not migrate. |

`web` and `worker` share the named volume `sqlite_data` at `/data/db.sqlite3`. Compose sets `REDIS_URL` to `redis://redis:6379/0` and `CELERY_BROKER_URL` to `redis://redis:6379/1`. `SECRET_KEY` comes from the shell or the gitignored `.env` file. It is not written into the image.

Docker is not installed on the machine used for this work. `docker compose config` was not run, and no container was started. The commands below are the intended local workflow, not a verified deployment.

```powershell
docker compose up --build
docker compose logs -f
docker compose down
```

`docker compose down` stops the services and keeps `sqlite_data`. `docker compose down -v` deletes that volume and the SQLite file inside it. Redis data is not stored on a volume.

SQLite still has one writer at a time. The stack therefore uses one Gunicorn worker and one Celery process.

## Project structure

```text
django-phase1-training/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── environment.py
│   ├── celery.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── blog/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── serializers.py
    ├── services.py
    ├── tasks.py
    ├── expressions.py
    ├── signals.py
    ├── tests.py
    ├── test_phase5_security.py
    ├── test_phase5_servers.py
    ├── test_phase5_cors.py
    ├── test_phase5_cache.py
    ├── test_phase5_celery.py
    ├── test_phase5_throttling.py
    └── migrations/
        ├── __init__.py
        ├── 0001_initial.py
        ├── 0002_author_post_author.py
        ├── 0003_authorprofile.py
        ├── 0004_category_post_categories.py
        └── 0005_phase4_indexes_and_constraints.py
```

Local files that also exist and must stay out of version control:

- `.env`
- `.venv/` and `venv/`
- `db.sqlite3`, other SQLite files, and their journal files
- `__pycache__/` and bytecode

## Setup

Python 3.11 or newer is expected. `requirements.txt` pins the stack, including Django 5.2.18, djangorestframework 3.18.3, django-cors-headers 4.9.0, gunicorn 26.2.0, uvicorn 0.54.0, redis 8.1.0, celery 5.6.3, and python-dotenv 1.2.4.

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies and create the local environment file:

```bash
pip install -r requirements.txt
```

Windows:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Edit `.env` and replace the `SECRET_KEY` placeholder with a long random string of your own. Leave `DEBUG=True` and `USE_HTTPS=False` for local HTTP. Django raises `KeyError` on startup if `SECRET_KEY` is missing, because settings read it with `os.environ["SECRET_KEY"]`. The safe names and example values are listed under Phase 5. Do not commit `.env`.

On Windows PowerShell, from the project directory:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py test blog
python manage.py runserver
```

`runserver` is the local development server. To start the ASGI server on Windows instead:

```powershell
uvicorn config.asgi:application
```

Uvicorn was not started during this work. Gunicorn is not a Windows command. Use it inside the Docker image, or on macOS or Linux:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1
```

The home page is [http://127.0.0.1:8000/blog/](http://127.0.0.1:8000/blog/). The status view is [http://127.0.0.1:8000/blog/api/status/](http://127.0.0.1:8000/blog/api/status/).

`python manage.py test blog` uses a temporary test database and removes it when the run finishes. With `REDIS_URL` and `CELERY_BROKER_URL` left blank, the tests do not need Redis.

### Docker

Docker Desktop was not available when this file was written, so the stack has not been built or started. When Docker is installed, run these commands from the project directory. `SECRET_KEY` must be in the shell or in the gitignored `.env` file. Compose reads that file for substitution and does not copy it into the image.

```powershell
docker compose up --build
docker compose logs -f
docker compose down
```

`docker compose down` stops the containers and keeps the `sqlite_data` volume. `docker compose down -v` deletes that volume, including the SQLite database stored there. Redis is not kept on a volume.

## API endpoints

Base URL for the examples below: `http://127.0.0.1:8000`.

| Method | Endpoint | Authentication |
| --- | --- | --- |
| `GET` | `/blog/` | Public |
| `GET` | `/blog/api/status/` | Public. Returns `{"status": "ok"}`. |
| `GET` | `/blog/api/posts/` | Public |
| `GET` | `/blog/api/posts/<id>/` | Public |
| `POST` | `/api-token-auth/` | Public. Send `username` and `password`. |
| `POST` | `/blog/api/posts/` | Token required |
| `PUT` | `/blog/api/posts/<id>/` | Token required |
| `PATCH` | `/blog/api/posts/<id>/` | Token required |
| `DELETE` | `/blog/api/posts/<id>/` | Token required |

Send the token on write requests:

```http
Authorization: Token <token>
Content-Type: application/json
```

Create a post:

```http
POST /blog/api/posts/
```

```json
{
  "title": "First post",
  "content": "Post body",
  "is_published": false
}
```

`is_published` may be omitted. A new post then defaults to unpublished.

List published posts whose title or content matches a search term, on page 2:

```http
GET /blog/api/posts/?is_published=true&search=First&page=2
```

`/admin/` is Django's admin site. Blog models are not registered there.

## Testing

The automated suite is the `blog` app. `blog/tests.py` holds `PostApiTests` (22 API tests) and `Phase4OrmTests` (18 ORM tests). Phase 5 adds `test_phase5_security.py`, `test_phase5_servers.py`, `test_phase5_cors.py`, `test_phase5_cache.py`, `test_phase5_celery.py`, and `test_phase5_throttling.py`.

Covered behavior:

- public list and retrieve
- HTTP 401 for unauthenticated create, update, partial update, and delete
- rejection of an invalid token
- create with the default unpublished flag, and create with `is_published` set to true
- rejection of spam titles and identical title and content
- partial update of one field, including changing `is_published` from false to true
- full update and delete
- page 1 and page 2 with page size 2
- search by title or content, including an empty result
- published and unpublished filters, including uppercase and mixed-case values
- HTTP 400 for an invalid `is_published` value
- one combined filter, search, and pagination request

`Phase4OrmTests` covers the composite index, all four database constraints, `CharLength`, the raw published count, the one-query ORM count, `select_related` and `prefetch_related` query counts, transaction rollback, `publish_post()`, the SQLite `select_for_update` limitation, bulk create, bulk update, and the fact that `create_post()` still sends `post_save`.

The Phase 5 tests cover environment parsing, HTTPS settings, baseline security headers, the async status response, loading the WSGI and ASGI callables, CORS allow and deny, the cached published count on the local-memory cache, the Celery task run with `apply()`, and anonymous and authenticated throttling at `1/minute`.

Verified result: `python manage.py test blog` reported `Ran 84 tests in 27.951s` and `OK`.

The suite does not test the home page, the token-login endpoint, missing-post 404 responses, `PublishedManager`, or the admin site. It does not test real row locking, because SQLite does not provide it through Django's `select_for_update()`. It does not connect to Redis, start a Celery worker, start Gunicorn or Uvicorn, or build the Docker stack.

## Security notes

Do not commit these paths:

- `.env` — local `SECRET_KEY`, `DEBUG`, and any other local settings
- `.venv/` or `venv/` — the virtual environment
- `db.sqlite3` and other SQLite files — they can contain users, tokens, and posts

`.gitignore` lists `.env`, both virtual-environment directory names, `__pycache__/`, bytecode, `db.sqlite3`, other `*.sqlite3` files, and SQLite journal files. `.dockerignore` also excludes `.git`, `.env`, virtual environments, caches, and database files. `.env.example` stays in version control and contains placeholders only.

Do not put a real secret key, token, or password in the README, in `.env.example`, in Compose, or in source code. Generate a unique `SECRET_KEY` in your own `.env`.

This project is a local training application. It has not been deployed. `DEBUG` is intended to be on for local HTTP, `USE_HTTPS` stays `False` unless you terminate TLS, and the database is still SQLite.
