"""Optional neatlogs tracing. Off unless setup() succeeds, so tests and offline runs work unchanged.

neatlogs.init() must run before the LLM library is imported (see llm.py, which imports openai lazily).
Each process uses one workflow name: "recallops-baseline" or "recallops-agent".
"""
from __future__ import annotations

import functools
import os

_enabled = False


def setup(workflow_name: str, tags: list[str] | None = None) -> bool:
    global _enabled
    if os.environ.get("RECALLOPS_TRACE", "1") == "0":
        return False
    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("NEATLOGS_API_KEY"):
        print("tracing: NEATLOGS_API_KEY not set, running untraced")
        return False
    import neatlogs

    neatlogs.init(workflow_name=workflow_name, tags=tags or [])
    _enabled = True
    return True


def enabled() -> bool:
    return _enabled


def span(kind: str, name: str | None = None, **kw):
    """neatlogs.span when tracing is on, a no-op otherwise. Resolved at call time, so decorating at import is safe."""

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not _enabled:
                return fn(*args, **kwargs)
            import neatlogs

            return neatlogs.span(kind, name or fn.__name__, **kw)(fn)(*args, **kwargs)

        return wrapper

    return deco


def wrap_client(client):
    if not _enabled:
        return client
    import neatlogs

    return neatlogs.wrap(client)


def log(msg: str, **data) -> None:
    if _enabled:
        import neatlogs

        neatlogs.log(msg, **data)


def flush() -> dict | None:
    """Flush spans and return neatlogs' own delivery counters (no secrets in them)."""
    if _enabled:
        import neatlogs

        neatlogs.flush()
        try:
            return dict(neatlogs.get_delivery_diagnostics())
        except Exception:
            return None
    return None
