"""Parse environment values used by Django settings."""

from urllib.parse import urlsplit

HSTS_ONE_YEAR = 60 * 60 * 24 * 365
DEFAULT_ANON_THROTTLE_RATE = "60/minute"
DEFAULT_USER_THROTTLE_RATE = "240/minute"
_THROTTLE_PERIODS = {
    "s",
    "sec",
    "second",
    "m",
    "min",
    "minute",
    "h",
    "hour",
    "d",
    "day",
}


def parse_allowed_hosts(value):
    """Return host names from a comma-separated environment value.

    Blank input returns an empty list. The wildcard "*" is rejected.
    """
    if value is None:
        return []
    hosts = []
    for part in value.split(","):
        host = part.strip()
        if not host:
            continue
        if host == "*":
            raise ValueError(
                "ALLOWED_HOSTS must list host names. '*' is not allowed."
            )
        hosts.append(host)
    return hosts


def https_enabled(value):
    """Return True only when the value is the text True.

    This matches the project's DEBUG rule: only the exact text "True" enables
    the setting. "true", "1", and a missing value stay off.
    """
    if value is None:
        value = "False"
    return value == "True"


def security_settings(use_https):
    """Return the transport-security settings for one USE_HTTPS value.

    When use_https is false, redirects, secure cookies, and HSTS stay off so
    local HTTP and the test client keep working.
    """
    enabled = bool(use_https)
    return {
        "SECURE_SSL_REDIRECT": enabled,
        "SESSION_COOKIE_SECURE": enabled,
        "CSRF_COOKIE_SECURE": enabled,
        "SECURE_HSTS_SECONDS": HSTS_ONE_YEAR if enabled else 0,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": enabled,
        "SECURE_HSTS_PRELOAD": enabled,
    }


def parse_cors_allowed_origins(value):
    """Return browser origins from a comma-separated environment value.

    Blank input returns an empty list. "*" is rejected, so this parser
    cannot allow every origin.
    """
    if value is None:
        return []
    origins = []
    for part in value.split(","):
        origin = part.strip()
        if not origin:
            continue
        if origin == "*":
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must list origins. '*' is not allowed."
            )
        parsed = urlsplit(origin)
        if parsed.scheme == "" or parsed.netloc == "":
            raise ValueError(
                "CORS_ALLOWED_ORIGINS entries need a scheme and host, "
                "such as http://localhost:3000. "
                f"Got {origin!r}."
            )
        if parsed.path or parsed.query or parsed.fragment:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS entries must not include a path. "
                f"Got {origin!r}."
            )
        origins.append(origin)
    return origins


def parse_throttle_rate(value, default):
    """Return one DRF throttle rate.

    Blank input returns the default. A rate looks like ``60/minute``.
    """
    if value is None or not value.strip():
        return default
    rate = value.strip()
    count, separator, period = rate.partition("/")
    if (
        not separator
        or not count.isdigit()
        or int(count) < 1
        or period not in _THROTTLE_PERIODS
    ):
        raise ValueError(
            "Throttle rates must look like 60/minute. "
            f"Got {rate!r}."
        )
    return rate


def cache_settings(redis_url):
    """Return Django cache settings for one REDIS_URL value.

    A blank value uses the local-memory cache so development and tests do
    not need a Redis server. A non-blank value selects Django's Redis cache.
    """
    if redis_url is None or not redis_url.strip():
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "blog-default",
            }
        }
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_url.strip(),
        }
    }


def celery_config(broker_url):
    """Return Celery settings for one CELERY_BROKER_URL value.

    A blank value runs tasks in this process and uses an in-memory broker,
    so development and tests do not need Redis. A non-blank value is the
    broker URL, and tasks are left for a worker.
    """
    if broker_url is None or not broker_url.strip():
        return {
            "broker_url": "memory://",
            "task_always_eager": True,
            "task_eager_propagates": True,
        }
    return {
        "broker_url": broker_url.strip(),
        "task_always_eager": False,
        "task_eager_propagates": True,
    }
