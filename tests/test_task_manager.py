"""Tests for task management system."""

import tempfile
from pathlib import Path

import pytest

from wakamat.models import Task, TaskStatus
from wakamat.task_manager import TaskManager


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def task_manager(tmp_dir: Path) -> TaskManager:
    return TaskManager("test-team", base_dir=tmp_dir)


class TestTaskManager:
    def test_add_and_get_tasks(self, task_manager: TaskManager) -> None:
        t1 = Task(title="Task 1")
        t2 = Task(title="Task 2")
        task_manager.add_task(t1)
        task_manager.add_task(t2)
        tasks = task_manager.get_tasks()
        assert len(tasks) == 2
        assert tasks[0].title == "Task 1"

    def test_add_tasks_batch(self, task_manager: TaskManager) -> None:
        tasks = [Task(title=f"Task {i}") for i in range(5)]
        task_manager.add_tasks(tasks)
        assert len(task_manager.get_tasks()) == 5

    def test_claim_task(self, task_manager: TaskManager) -> None:
        task = Task(title="Claimable")
        task_manager.add_task(task)
        claimed = task_manager.claim_task(task.id, "member-1")
        assert claimed is not None
        assert claimed.status == TaskStatus.IN_PROGRESS
        assert claimed.assigned_to == "member-1"

    def test_claim_already_claimed(self, task_manager: TaskManager) -> None:
        task = Task(title="Claimable")
        task_manager.add_task(task)
        task_manager.claim_task(task.id, "member-1")
        # Second claim should fail
        result = task_manager.claim_task(task.id, "member-2")
        assert result is None

    def test_claim_next(self, task_manager: TaskManager) -> None:
        t1 = Task(title="First")
        t2 = Task(title="Second")
        task_manager.add_tasks([t1, t2])
        claimed = task_manager.claim_next("member-1")
        assert claimed is not None
        assert claimed.title == "First"

    def test_claim_next_skips_blocked(self, task_manager: TaskManager) -> None:
        t1 = Task(id="t1", title="First")
        t2 = Task(id="t2", title="Blocked", depends_on=["t1"])
        t3 = Task(id="t3", title="Available")
        task_manager.add_tasks([t1, t2, t3])
        # Claim t1
        task_manager.claim_task("t1", "member-1")
        # Next available should be t3 (t2 is blocked)
        claimed = task_manager.claim_next("member-2")
        assert claimed is not None
        assert claimed.id == "t3"

    def test_complete_task(self, task_manager: TaskManager) -> None:
        task = Task(title="To complete")
        task_manager.add_task(task)
        task_manager.claim_task(task.id, "member-1")
        completed = task_manager.complete_task(task.id, "Done!")
        assert completed is not None
        assert completed.status == TaskStatus.COMPLETED
        assert completed.result == "Done!"
        assert completed.completed_at is not None

    def test_fail_task(self, task_manager: TaskManager) -> None:
        task = Task(title="Will fail")
        task_manager.add_task(task)
        failed = task_manager.fail_task(task.id, "Something went wrong")
        assert failed is not None
        assert failed.status == TaskStatus.FAILED

    def test_dependency_unblocking(self, task_manager: TaskManager) -> None:
        t1 = Task(id="t1", title="Dependency")
        t2 = Task(id="t2", title="Dependent", depends_on=["t1"])
        task_manager.add_tasks([t1, t2])
        assert task_manager.is_task_blocked("t2")

        # Complete the dependency
        task_manager.claim_task("t1", "member-1")
        task_manager.complete_task("t1", "done")
        assert not task_manager.is_task_blocked("t2")

    def test_get_available_tasks(self, task_manager: TaskManager) -> None:
        t1 = Task(id="t1", title="Available 1")
        t2 = Task(id="t2", title="Blocked", depends_on=["t1"])
        t3 = Task(id="t3", title="Available 2")
        task_manager.add_tasks([t1, t2, t3])
        available = task_manager.get_available_tasks()
        assert len(available) == 2
        titles = {t.title for t in available}
        assert titles == {"Available 1", "Available 2"}

    def test_is_all_done(self, task_manager: TaskManager) -> None:
        t1 = Task(title="Task 1")
        t2 = Task(title="Task 2")
        task_manager.add_tasks([t1, t2])
        assert not task_manager.is_all_done()

        task_manager.claim_task(t1.id, "m1")
        task_manager.complete_task(t1.id, "done")
        assert not task_manager.is_all_done()

        task_manager.claim_task(t2.id, "m2")
        task_manager.complete_task(t2.id, "done")
        assert task_manager.is_all_done()

    def test_assign_task(self, task_manager: TaskManager) -> None:
        task = Task(title="To assign")
        task_manager.add_task(task)
        assigned = task_manager.assign_task(task.id, "member-1")
        assert assigned is not None
        assert assigned.assigned_to == "member-1"
        # Still pending - assignment doesn't change status
        assert assigned.status == TaskStatus.PENDING

    def test_cleanup(self, task_manager: TaskManager) -> None:
        task_manager.add_task(Task(title="Will be removed"))
        task_manager.cleanup()
        # After cleanup, creating a new manager should start fresh
        tm2 = TaskManager("test-team", base_dir=task_manager._base_dir)
        assert len(tm2.get_tasks()) == 0
