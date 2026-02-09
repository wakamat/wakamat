"""Task management with file-based locking for concurrent access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from wakamat.models import Task, TaskStatus


class TaskManager:
    """Manages a shared task list with file-based locking.

    Tasks are stored on disk so multiple agent processes can read/write
    them concurrently. File locks prevent race conditions when claiming tasks.
    """

    def __init__(self, team_name: str, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.home() / ".wakamat" / "tasks"
        self._team_dir = self._base_dir / team_name
        self._team_dir.mkdir(parents=True, exist_ok=True)
        self._tasks_file = self._team_dir / "tasks.json"
        self._lock_file = self._team_dir / "tasks.lock"
        self._lock = FileLock(self._lock_file)

        if not self._tasks_file.exists():
            self._write_tasks([])

    def _read_tasks(self) -> list[Task]:
        """Read tasks from disk."""
        if not self._tasks_file.exists():
            return []
        data = json.loads(self._tasks_file.read_text())
        return [Task.model_validate(t) for t in data]

    def _write_tasks(self, tasks: list[Task]) -> None:
        """Write tasks to disk."""
        data = [t.model_dump(mode="json") for t in tasks]
        self._tasks_file.write_text(json.dumps(data, indent=2, default=str))

    def add_task(self, task: Task) -> Task:
        """Add a task to the shared list."""
        with self._lock:
            tasks = self._read_tasks()
            tasks.append(task)
            self._write_tasks(tasks)
        return task

    def add_tasks(self, new_tasks: list[Task]) -> list[Task]:
        """Add multiple tasks atomically."""
        with self._lock:
            tasks = self._read_tasks()
            tasks.extend(new_tasks)
            self._write_tasks(tasks)
        return new_tasks

    def get_tasks(self) -> list[Task]:
        """Get all tasks."""
        with self._lock:
            return self._read_tasks()

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        with self._lock:
            tasks = self._read_tasks()
            return next((t for t in tasks if t.id == task_id), None)

    def claim_task(self, task_id: str, member_id: str) -> Task | None:
        """Atomically claim a pending, unblocked task.

        Returns the claimed task, or None if the task cannot be claimed
        (already claimed, blocked by dependencies, or not found).
        """
        with self._lock:
            tasks = self._read_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                return None
            if task.status != TaskStatus.PENDING:
                return None
            if task.assigned_to is not None:
                return None
            if self._is_blocked(task, tasks):
                return None

            task.status = TaskStatus.IN_PROGRESS
            task.assigned_to = member_id
            self._write_tasks(tasks)
            return task

    def claim_next(self, member_id: str) -> Task | None:
        """Claim the next available (pending, unblocked, unassigned) task."""
        with self._lock:
            tasks = self._read_tasks()
            for task in tasks:
                if (
                    task.status == TaskStatus.PENDING
                    and task.assigned_to is None
                    and not self._is_blocked(task, tasks)
                ):
                    task.status = TaskStatus.IN_PROGRESS
                    task.assigned_to = member_id
                    self._write_tasks(tasks)
                    return task
            return None

    def complete_task(self, task_id: str, result: str = "") -> Task | None:
        """Mark a task as completed with an optional result."""
        with self._lock:
            tasks = self._read_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                return None
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            self._write_tasks(tasks)
            return task

    def fail_task(self, task_id: str, reason: str = "") -> Task | None:
        """Mark a task as failed with a reason."""
        with self._lock:
            tasks = self._read_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                return None
            task.status = TaskStatus.FAILED
            task.result = reason
            task.completed_at = datetime.now(timezone.utc)
            self._write_tasks(tasks)
            return task

    def assign_task(self, task_id: str, member_id: str) -> Task | None:
        """Assign a pending task to a specific member (leader action)."""
        with self._lock:
            tasks = self._read_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                return None
            if task.status != TaskStatus.PENDING:
                return None
            task.assigned_to = member_id
            self._write_tasks(tasks)
            return task

    def get_available_tasks(self) -> list[Task]:
        """Get all pending, unblocked, unassigned tasks."""
        with self._lock:
            tasks = self._read_tasks()
            return [
                t
                for t in tasks
                if t.status == TaskStatus.PENDING
                and t.assigned_to is None
                and not self._is_blocked(t, tasks)
            ]

    def is_task_blocked(self, task_id: str) -> bool:
        """Check if a task is blocked by incomplete dependencies."""
        with self._lock:
            tasks = self._read_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task is None:
                return False
            return self._is_blocked(task, tasks)

    def is_all_done(self) -> bool:
        """Check if all tasks are completed or failed."""
        with self._lock:
            tasks = self._read_tasks()
            return all(
                t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) for t in tasks
            )

    def _is_blocked(self, task: Task, all_tasks: list[Task]) -> bool:
        """Check if a task has unresolved dependencies."""
        if not task.depends_on:
            return False
        for dep_id in task.depends_on:
            dep = next((t for t in all_tasks if t.id == dep_id), None)
            if dep is None or dep.status != TaskStatus.COMPLETED:
                return True
        return False

    def cleanup(self) -> None:
        """Remove all task files for this team."""
        if self._tasks_file.exists():
            self._tasks_file.unlink()
        if self._lock_file.exists():
            self._lock_file.unlink()
        if self._team_dir.exists():
            self._team_dir.rmdir()
