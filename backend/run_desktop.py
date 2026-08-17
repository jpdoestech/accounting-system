"""
Entrypoint for the packaged Windows executable
(scripts/build_exe.bat -> dist/PhilippineAccountingSystem.exe).

Running the .exe does three things:
  1. Applies any pending Alembic migrations to the local SQLite
     database (stored next to the .exe, not inside it -- PyInstaller
     bundles are read-only at runtime).
  2. Starts the FastAPI app with uvicorn.
  3. Opens the default browser to the app once the server is ready,
     since a packaged .exe has no terminal for the user to read a
     "visit http://localhost:8000" message from.

Not used in normal `uvicorn app.main:app --reload` development --
that path is unaffected by anything in this file.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser


def _resource_base_dir() -> str:
    """Directory the .exe was launched from -- where dev.db and .env
    should live (writable, persists next to the .exe)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _bundled_resource_dir() -> str:
    """
    Directory containing files PyInstaller bundled in (migrations/,
    alembic.ini) -- this is sys._MEIPASS when frozen, which for a
    --onedir build is the '_internal' folder next to the .exe, NOT
    the same directory as _resource_base_dir(). Read-only at runtime;
    never write here (e.g. dev.db goes in _resource_base_dir()
    instead).
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    bundled_dir = _bundled_resource_dir()
    alembic_ini = os.path.join(bundled_dir, "alembic.ini")
    cfg = Config(alembic_ini)
    # alembic.ini's own script_location is a relative path ("migrations"),
    # which Alembic would otherwise resolve relative to the current
    # working directory -- not reliable inside a frozen bundle. Overriding
    # it here with an absolute path resolved against the bundle's actual
    # resource directory (sys._MEIPASS when frozen) makes it work
    # regardless of the process's cwd.
    cfg.set_main_option("script_location", os.path.join(bundled_dir, "migrations"))
    command.upgrade(cfg, "head")


def _open_browser_when_ready(url: str, timeout_seconds: int = 20) -> None:
    import urllib.request

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url + "/health", timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)


def main() -> None:
    base_dir = _resource_base_dir()
    os.chdir(base_dir)

    # app.config.Settings already reads a .env file from the current
    # working directory (see model_config in app/config.py) -- since
    # we just chdir'd into the folder containing the .exe, dropping a
    # .env file next to it (e.g. to point DATABASE_URL at Postgres)
    # works automatically with no extra loading here. We only supply
    # a SQLite default via an environment variable, and only when the
    # operator hasn't set DATABASE_URL some other way, so a .env
    # file's own DATABASE_URL always takes precedence over this
    # fallback.
    env_path = os.path.join(base_dir, ".env")
    if "DATABASE_URL" not in os.environ and not os.path.exists(env_path):
        os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(base_dir, 'dev.db')}"

    print("Philippine Accounting System")
    print("Applying database migrations...")
    _run_migrations()

    port = int(os.environ.get("PORT", "8000"))
    url = f"http://localhost:{port}"

    print(f"Starting server at {url} ...")
    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
