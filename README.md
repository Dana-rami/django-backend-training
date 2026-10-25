# Django Blog REST API

Training project for a Django blog and its Post REST API. The repository contains the work completed for Phases 1, 2, and 3. Phases 4 and 5 are currently study topics and are not implemented in this project.

| Phase | Status in this repository |
| --- | --- |
| 1. Django Foundations | Partially implemented |
| 2. Django REST Framework | Implemented for the Post API |
| 3. API Architecture & Clean Structure | Partially implemented |
| 4. Advanced Django ORM | Not implemented |
| 5. Production & Scaling | Not implemented |

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

The latest run of `python manage.py test blog` reported **22 tests, OK**.

## Phase 3 – API Architecture & Clean Structure

**Status: partially implemented.**

| Piece | What exists |
| --- | --- |
| Service layer | `create_post()` in `blog/services.py` creates a post from `title`, `content`, and `is_published`. `PostViewSet.perform_create()` calls it. Updates and deletes still use the serializer save path. |
| Custom QuerySet | `PostQuerySet.published()` and `PostQuerySet.unpublished()` filter on `is_published`. The list view calls these methods. |
| Custom manager | `PublishedManager` filters to published posts and is attached as `Post.published`. The API uses the queryset methods above. |
| Signals | `log_post_created` writes an INFO log when a post is created. `BlogConfig.ready()` imports the signal module. |
| Logging | The `blog` logger writes to the console at INFO with the format `{levelname} {name} {message}`. |
| Environment variables | `python-dotenv` loads `.env`. `SECRET_KEY` is required. `DEBUG` is `True` only when its value is the text `True`. |

Validation remains in the serializer. Published filtering remains in the view. Settings live in one module, `config/settings.py`. There are no direct tests for the service, queryset, manager, or signal.

## Phase 4 – Advanced Django ORM

**Status: not implemented.**

These topics are being studied and are not present in the application code:

- database indexes
- database constraints
- query optimization
- transactions
- `select_for_update`
- bulk operations

Django's normal primary-key and foreign-key indexes are created by the existing migrations. There are no custom indexes, constraints, annotations, raw SQL queries, transactions, row locks, or bulk create/update operations in this project.

## Phase 5 – Production & Scaling

**Status: not implemented.**

These topics are being studied and are not configured in this project:

- production WSGI or ASGI servers
- async views
- caching
- background tasks
- rate limiting
- Docker
- CORS
- production security configuration

`config/wsgi.py` and `config/asgi.py` are the default files created by `startproject`. The database is SQLite. `ALLOWED_HOSTS` is empty. `STATIC_URL` is set, and `STATIC_ROOT` is not. No Gunicorn, Uvicorn, Redis, Celery, Docker, CORS, or rate-limit configuration is included.

## Project structure

```text
django-phase1-training/
├── manage.py
├── requirements.txt
├── .gitignore
├── .env.example
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
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
    ├── signals.py
    ├── tests.py
    └── migrations/
        ├── __init__.py
        ├── 0001_initial.py
        ├── 0002_author_post_author.py
        ├── 0003_authorprofile.py
        └── 0004_category_post_categories.py
```

Local files that also exist and must stay out of version control:

- `.env`
- `.venv/`
- `db.sqlite3`
- `__pycache__/`

## Setup

Python 3.11 or newer is expected. The pinned stack is in `requirements.txt` (Django 5.2.18, djangorestframework 3.18.3, and python-dotenv 1.2.4).

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

Edit `.env` and replace the `SECRET_KEY` placeholder with a long random string of your own. Leave `DEBUG=True` for local development. Django raises `KeyError` on startup if `SECRET_KEY` is missing, because settings read it with `os.environ["SECRET_KEY"]`.

Apply migrations and start the development server:

```bash
python manage.py migrate
python manage.py runserver
```

The home page is [http://127.0.0.1:8000/blog/](http://127.0.0.1:8000/blog/).

Run the blog tests:

```bash
python manage.py test blog
```

The test command uses a temporary test database and removes it when the run finishes.

## API endpoints

Base URL for the examples below: `http://127.0.0.1:8000`.

| Method | Endpoint | Authentication |
| --- | --- | --- |
| `GET` | `/blog/` | Public |
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

The automated suite is `blog/tests.py`, class `PostApiTests`. It has 22 tests and uses Django REST Framework's `APITestCase`.

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

Verified result: `python manage.py test blog` reported `Ran 22 tests` and `OK`.

The suite does not test the home page, the token-login endpoint, missing-post 404 responses, signals, `create_post()`, the queryset methods, relationships, or the admin site.

## Security notes

Do not commit these paths:

- `.env` — local `SECRET_KEY` and `DEBUG`
- `.venv/` — the virtual environment
- `db.sqlite3` — the local database, which can contain users, tokens, and posts

`.gitignore` already lists all three, along with `__pycache__/`.

`.env.example` contains placeholders only. Do not put a real secret key, token, or password in the README, in `.env.example`, or in source code. Generate a unique `SECRET_KEY` in your own `.env`.

This project is a local training application. It is not a production deployment: `DEBUG` is intended to be on locally, `ALLOWED_HOSTS` is empty, the database is SQLite, and production security settings are not configured.
