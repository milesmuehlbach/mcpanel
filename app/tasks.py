from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import queue
import threading
from typing import Any, Callable, Literal
from uuid import uuid4

TaskState = Literal["queued", "running", "succeeded", "failed"]

_TERMINATOR = object()


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class TaskRecord:
    id: str
    name: str
    state: TaskState
    message: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: Any = None


@dataclass(slots=True)
class _TaskEntry:
    record: TaskRecord
    func: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    done_event: threading.Event


class TaskManager:
    def __init__(self, max_completed_tasks: int = 100):
        if max_completed_tasks < 1:
            raise ValueError("max_completed_tasks must be at least 1")

        self._max_completed_tasks = max_completed_tasks
        self._lock = threading.Lock()
        self._entries: dict[str, _TaskEntry] = {}
        self._queue: queue.Queue[str | object] = queue.Queue()
        self._accepting_tasks = True
        self._worker = threading.Thread(
            target=self._run,
            name="worker_1",
            daemon=True,
        )
        self._worker.start()

    def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        name: str | None = None,
        **kwargs: Any,
    ) -> str:
        task_id = uuid4().hex
        task_name = name or getattr(func, "__name__", "") or "task"
        record = TaskRecord(
            id=task_id,
            name=task_name,
            state="queued",
            message="task queued",
            created_at=_utcnow(),
        )
        entry = _TaskEntry(
            record=record,
            func=func,
            args=args,
            kwargs=kwargs,
            done_event=threading.Event(),
        )

        with self._lock:
            if not self._accepting_tasks:
                raise RuntimeError("task manager is shut down")

            self._entries[task_id] = entry

        self._queue.put(task_id)
        return task_id

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            entry = self._entries.get(task_id)
            if entry is None:
                return None

            return replace(entry.record)

    def list_tasks(self) -> list[TaskRecord]:
        with self._lock:
            entries = [replace(entry.record) for entry in self._entries.values()]

        return sorted(entries, key=lambda record: record.created_at)

    def wait_for_task(
        self, task_id: str, timeout: float | None = None
    ) -> TaskRecord | None:
        with self._lock:
            entry = self._entries.get(task_id)
            if entry is None:
                return None

            done_event = entry.done_event

        finished = done_event.wait(timeout)
        if not finished:
            return None

        return replace(entry.record)

    def set_message(self, task_id: str, message: str) -> bool:
        with self._lock:
            entry = self._entries.get(task_id)
            if entry is None:
                return False

            if entry.record.state not in {"queued", "running"}:
                return False

            entry.record.message = message
            return True

    def shutdown(self, timeout: float | None = None) -> None:
        with self._lock:
            if not self._accepting_tasks:
                worker = self._worker
            else:
                self._accepting_tasks = False
                worker = self._worker
                self._queue.put(_TERMINATOR)

        worker.join(timeout)

    def _run(self) -> None:
        while True:
            task_token = self._queue.get()
            try:
                if task_token is _TERMINATOR:
                    return

                task_id = task_token

                with self._lock:
                    entry = self._entries.get(task_id)
                    if entry is None:
                        continue

                    entry.record.state = "running"
                    entry.record.message = "task running"
                    entry.record.started_at = _utcnow()

                try:
                    result = entry.func(*entry.args, **entry.kwargs)
                except Exception as exception:
                    with self._lock:
                        entry.record.state = "failed"
                        entry.record.message = "task failed"
                        entry.record.error = (
                            str(exception) or exception.__class__.__name__
                        )
                        entry.record.finished_at = _utcnow()
                        self._prune_completed_tasks()
                    entry.done_event.set()
                    continue

                with self._lock:
                    entry.record.state = "succeeded"
                    entry.record.message = "task completed"
                    entry.record.result = result
                    entry.record.finished_at = _utcnow()
                    self._prune_completed_tasks()
                entry.done_event.set()
            finally:
                self._queue.task_done()

    def _prune_completed_tasks(self) -> None:
        completed_entries = [
            entry
            for entry in self._entries.values()
            if entry.record.state in {"succeeded", "failed"}
            and entry.record.finished_at is not None
        ]
        overflow = len(completed_entries) - self._max_completed_tasks
        if overflow <= 0:
            return

        completed_entries.sort(
            key=lambda entry: entry.record.finished_at or entry.record.created_at
        )
        for entry in completed_entries[:overflow]:
            self._entries.pop(entry.record.id, None)
