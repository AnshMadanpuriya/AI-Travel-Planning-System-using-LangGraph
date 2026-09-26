"""Keep Streamlit responsive even if an MCP task ignores async cancellation."""

from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from .config import PROJECT_ROOT, Settings
from .models import PlannerResult
from .payloads import clip_text, partial_answer

ProgressCallback = Callable[[dict[str, Any]], None]


def _posix_descendants(parent_pid: int) -> list[int]:
    """Find descendants even when the MCP SDK starts a separate process group."""
    try:
        snapshot = subprocess.run(
            ["ps", "-eo", "pid=,ppid="],
            capture_output=True,
            text=True,
            timeout=1,
            check=True,
        )
        pairs = [tuple(map(int, row.split())) for row in snapshot.stdout.splitlines()]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    descendants: list[int] = []
    pending = [parent_pid]
    while pending:
        parent = pending.pop()
        children = [pid for pid, ppid in pairs if ppid == parent]
        descendants.extend(children)
        pending.extend(children)
    return descendants


def _stop_worker(process: subprocess.Popen[str]) -> None:
    """Stop only this request's private process tree, including its MCP server."""
    if os.name == "nt" and process.poll() is not None:
        return
    if os.name == "nt":
        try:
            outcome = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
            if outcome.returncode and process.poll() is None:
                process.kill()
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
    else:
        # MCP creates its own session, so killing only the worker's group is insufficient.
        for pid in reversed(_posix_descendants(process.pid)):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()


def _run_worker(
    command: list[str],
    payload: dict[str, Any],
    timeout: float,
    on_progress: ProgressCallback | None = None,
) -> PlannerResult:
    started = time.monotonic()
    deadline = started + timeout
    trace: list[dict[str, Any]] = []
    available_tools: list[str] = []
    stage = "Starting the local planner"
    events: queue.Queue[dict[str, Any] | None] = queue.Queue()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = (
        str(PROJECT_ROOT / "src") + os.pathsep + environment.get("PYTHONPATH", "")
    )
    environment["PYTHONIOENCODING"] = "utf-8"
    if on_progress:
        on_progress({"stage": stage, "elapsed_seconds": 0.0})
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        encoding="utf-8",
        bufsize=1,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    def read_events() -> None:
        try:
            assert process.stdout is not None
            for line in process.stdout:
                try:
                    event = json.loads(line)
                    if isinstance(event, dict):
                        events.put(event)
                except (ValueError, TypeError):
                    # Third-party stdout is not trusted as a result or displayed to the user.
                    continue
        finally:
            events.put(None)

    def send_request() -> None:
        # Writing in a daemon thread also bounds a worker that never reads stdin.
        try:
            assert process.stdin is not None
            process.stdin.write(json.dumps(payload, ensure_ascii=False))
            process.stdin.close()
        except (OSError, ValueError):
            pass

    reader = threading.Thread(target=read_events, daemon=True)
    writer = threading.Thread(target=send_request, daemon=True)
    reader.start()
    writer.start()
    last_update = 0.0
    reason = "The planner stopped before it could finish. Restart the app and try again."
    try:
        while time.monotonic() < deadline:
            elapsed = time.monotonic() - started
            if on_progress and elapsed - last_update >= 0.5:
                on_progress({"stage": stage, "elapsed_seconds": elapsed})
                last_update = elapsed
            try:
                event = events.get(timeout=min(0.1, max(0.001, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if event is None:
                break
            if "stage" in event:
                stage = str(event["stage"])
                if on_progress:
                    on_progress({"stage": stage, "elapsed_seconds": time.monotonic() - started})
            if "available_tools" in event:
                available_tools = event["available_tools"]
            if "tool_result" in event:
                trace.append(event["tool_result"])
            if "result" in event:
                data = event["result"]
                return PlannerResult(
                    answer=data["answer"],
                    tool_trace=data.get("tool_trace", trace),
                    available_tools=data.get("available_tools", available_tools),
                    partial=data.get("partial", False),
                    elapsed_seconds=round(time.monotonic() - started, 1),
                )
            if "error" in event:
                reason = str(event["error"])
                break
        else:
            reason = f"Planning stopped after {timeout:g} seconds while {stage.lower()}. Completed checks are shown below."
        return PlannerResult(
            answer=partial_answer(reason, trace),
            tool_trace=trace,
            available_tools=available_tools,
            partial=True,
            elapsed_seconds=round(time.monotonic() - started, 1),
        )
    finally:
        _stop_worker(process)
        reader.join(timeout=0.2)
        writer.join(timeout=0.2)
        if not reader.is_alive() and process.stdout:
            process.stdout.close()


def plan_trip_sync(
    query: str,
    history: Sequence[dict[str, str]] | None = None,
    on_progress: ProgressCallback | None = None,
) -> PlannerResult:
    """The UI's timeout is enforced outside the planner and its asyncio event loop."""
    if not query.strip():
        raise ValueError("Please describe the trip you want to plan.")
    if len(query.encode("utf-8")) > 3000:
        raise ValueError("Please shorten the trip brief, keeping the cities, dates and constraints.")
    settings = Settings.from_env()
    settings.require_agent_key()
    items = list(history or [])
    selected = items if len(items) <= 3 else [items[0], *items[-2:]]
    compact_history = [
        {"role": item.get("role", "user"), "content": clip_text(item.get("content", ""), 600)}
        for item in selected
    ]
    return _run_worker(
        [sys.executable, "-u", "-m", "travel_planner.worker"],
        {"query": query, "history": compact_history},
        settings.planner_timeout_seconds,
        on_progress,
    )
