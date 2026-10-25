"""Ask a local LM Studio model for a reviewable coding change proposal.

This script sends only the task and files named on the command line. It never
writes to the project; Codex reviews and applies any proposed changes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "prism-ml/bonsai-27b"
MAX_FILE_BYTES = 100_000


def read_project_file(relative_path: str) -> tuple[str, str]:
    candidate = (PROJECT_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"File must be inside the project: {relative_path}") from exc
    if not candidate.is_file():
        raise ValueError(f"Not a project file: {relative_path}")
    data = candidate.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(
            f"File is {len(data):,} bytes; limit is {MAX_FILE_BYTES:,}: {relative_path}"
        )
    return candidate.relative_to(PROJECT_ROOT).as_posix(), data.decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="One focused coding task")
    parser.add_argument(
        "--files", nargs="+", required=True,
        help="Project-relative files to give the local model as context",
    )
    parser.add_argument("--model", default=os.getenv("LMSTUDIO_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.getenv("LMSTUDIO_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    try:
        file_sections = [read_project_file(path) for path in args.files]
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))

    context = "\n\n".join(
        f"--- FILE: {name} ---\n{contents}\n--- END FILE ---"
        for name, contents in file_sections
    )
    system_message = (
        "You are a coding helper working on a Python/Pygame project. "
        "Make only the focused change requested. The provided files are context, "
        "not permission to invent unseen project APIs. Return a unified diff with "
        "project-relative paths only, inside one diff code block. If the task is "
        "unclear or the provided context is insufficient, explain what is missing "
        "instead of guessing. Do not claim to have edited files or run tests."
    )
    user_message = f"TASK\n{args.task}\n\nPROJECT FILES\n{context}"
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "temperature": args.temperature,
        "stream": False,
    }
    request = Request(
        f"{args.base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=300) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"LM Studio returned HTTP {exc.code}: {detail}")
        return 1
    except (URLError, TimeoutError) as exc:
        print(
            "Could not reach LM Studio. Start it with "
            "`C:\\Users\\lucam\\.lmstudio\\bin\\lms.exe server start --port 1234 --bind 127.0.0.1`."
        )
        print(f"Details: {exc}")
        return 1

    try:
        choice = result["choices"][0]
        message = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"Unexpected LM Studio response: {json.dumps(result, ensure_ascii=False)}")
        return 1

    print(f"Model: {result.get('model', args.model)}")
    print(f"Context files: {', '.join(name for name, _ in file_sections)}")
    print("\n" + str(message).strip())
    usage = result.get("usage")
    if usage:
        print(f"\nToken usage: {usage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
