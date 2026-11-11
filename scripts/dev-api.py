"""Start the local API with application configuration from the root .env only."""

import os
import subprocess
import sys
from pathlib import Path

# Already installed by uvicorn[standard].
from dotenv import dotenv_values, load_dotenv


def load_local_environment(root: Path) -> None:
    env_file = root / ".env"
    if not env_file.is_file():
        raise SystemExit("Create the repository root .env from .env.example first.")

    # Preserve OS essentials (PATH, TEMP, etc.), but do not inherit app settings.
    names = set(dotenv_values(root / ".env.example", interpolate=False))
    names.update(dotenv_values(env_file, interpolate=False))
    names.update(name for name in os.environ if name.startswith((
        "OPENAI_", "SOURCEPILOT_", "LANGFUSE_",
    )))
    for name in names:
        os.environ.pop(name, None)
    load_dotenv(env_file, override=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_local_environment(root)
    print("Starting local API using the repository root .env", flush=True)
    try:
        return subprocess.call([
            sys.executable, "-m", "uvicorn", "sourcepilot.main:app",
            "--loop", "sourcepilot.comparison.lifecycle:comparison_loop",
            "--reload", "--port", "8000",
        ], cwd=root / "apps" / "api")
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
