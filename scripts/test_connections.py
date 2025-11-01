import os
import sys
import socket
from contextlib import closing
from pathlib import Path
from typing import Optional

# Load .env directly to avoid importing full app Settings (which validates many fields)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _ROOT / ".env"
if load_dotenv is not None and _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)


def mask(url: str) -> str:
    if not url:
        return ""
    # Basic masking for credentials in URLs
    try:
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                creds, host = rest.split("@", 1)
                return f"{scheme}://***:***@{host}"
        return url
    except Exception:
        return url


def preflight_dns(name: str, host: Optional[str], port: Optional[int]) -> None:
    if not host:
        print(f"{name} host missing; skipping DNS preflight")
        return
    try:
        infos = socket.getaddrinfo(host, port or 0)
        addrs = sorted({i[4][0] for i in infos})
        print(f"{name} DNS OK: {host} -> {', '.join(addrs)}")
    except Exception as e:
        print(f"{name} DNS ERROR: cannot resolve {host}:{port or ''} -> {e}")


def test_postgres(db_url: str) -> str:
    from sqlalchemy import text
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    url = make_url(db_url)
    preflight_dns("Postgres", url.host, url.port)

    # Supabase typically requires TLS; advise if sslmode is missing
    if "sslmode" not in (url.query or {}):
        print("Note: sslmode not present in DATABASE_URL; if using Supabase, append '?sslmode=require'")

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar()
    return f"Postgres OK: {version}"


def test_redis(redis_url: str) -> str:
    import redis
    from urllib.parse import urlparse

    parsed = urlparse(redis_url)
    preflight_dns("Redis", parsed.hostname, parsed.port)

    r = redis.from_url(redis_url, decode_responses=True)
    pong = r.ping()
    return f"Redis OK: PING={'PONG' if pong else 'NO'}"


def main() -> int:
    print("Testing connections with configured environment...\n")

    db_url = os.getenv("DATABASE_URL", "")
    redis_url = os.getenv("REDIS_URL", "")

    if not db_url:
        print("DATABASE_URL not set in environment/.env")
        return 1
    if not redis_url:
        print("REDIS_URL not set in environment/.env")
        return 1

    print(f"DATABASE_URL: {mask(db_url)}")
    print(f"REDIS_URL:    {mask(redis_url)}\n")

    # Postgres
    try:
        msg = test_postgres(db_url)
        print(msg)
    except Exception as e:
        print(f"Postgres ERROR: {e}")
        return 1

    # Redis
    try:
        msg = test_redis(redis_url)
        print(msg)
    except Exception as e:
        print(f"Redis ERROR: {e}")
        return 1

    print("\nAll connections succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
