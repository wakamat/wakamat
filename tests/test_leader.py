"""Tests for team leader orchestration."""

import tempfile
from pathlib import Path

import pytest

from wakamat.leader import TeamLeader
from wakamat.models import MemberRole, TaskStatus


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def leader(tmp_dir: Path) -> TeamLeader:
    return TeamLeader(
        team_name="test-team",
        leader_name="leader",
        base_dir=tmp_dir,
    )


class TestTeamLeader:
    def test_create_team(self, leader: TeamLeader) -> None:
        assert leader.team.name == "test-team"
        assert leader.team.leader.name == "leader"
        assert leader.team.leader.role == MemberRole.LEADER

    def test_spawn_member(self, leader: TeamLeader) -> None:
        member = leader.spawn_member(name="alice", prompt="Review code")
        assert member.name == "alice"
        assert len(leader.team.members) == 1
        assert leader.team.members[0].id == member.id

    def test_spawn_multiple_members(self, leader: TeamLeader) -> None:
        leader.spawn_member(name="alice", prompt="Review code")
        leader.spawn_member(name="bob", prompt="Write tests")
        leader.spawn_member(name="charlie", prompt="Check security")
        assert len(leader.team.members) == 3

    def test_add_task(self, leader: TeamLeader) -> None:
        task = leader.add_task(title="Review PR", description="Check for bugs")
        assert task.title == "Review PR"
        tasks = leader.task_manager.get_tasks()
        assert len(tasks) == 1

    def test_add_task_with_assignment(self, leader: TeamLeader) -> None:
        leader.spawn_member(name="alice", prompt="Review")
        task = leader.add_task(title="Review PR", assign_to="alice")
        assert task.assigned_to is not None

    def test_add_tasks_batch(self, leader: TeamLeader) -> None:
        leader.spawn_member(name="alice", prompt="Work")
        tasks = leader.add_tasks([
            {"title": "Task 1", "description": "First task", "assign_to": "alice"},
            {"title": "Task 2", "description": "Second task"},
            {"title": "Task 3", "depends_on": []},
        ])
        assert len(tasks) == 3

    def test_get_status(self, leader: TeamLeader) -> None:
        leader.spawn_member(name="alice", prompt="Work")
        leader.add_task(title="Task 1")
        status = leader.get_status()
        assert status["team_name"] == "test-team"
        assert len(status["members"]) == 2  # leader + alice
        assert len(status["tasks"]) == 1

    def test_shutdown_member(self, leader: TeamLeader) -> None:
        member = leader.spawn_member(name="alice", prompt="Work")
        result = leader.shutdown_member("alice")
        assert result is True
        # Check message was sent
        msgs = leader.mailbox.receive(member.id)
        assert len(msgs) == 1
        assert "shut down" in msgs[0].content.lower()

    def test_shutdown_nonexistent_member(self, leader: TeamLeader) -> None:
        result = leader.shutdown_member("unknown")
        assert result is False

    def test_check_leader_messages(self, leader: TeamLeader) -> None:
        from wakamat.models import Message

        member = leader.spawn_member(name="alice", prompt="Work")
        # Simulate alice sending a message to leader
        leader.mailbox.send(
            Message(
                sender=member.id,
                recipient=leader.team.leader.id,
                content="Task completed!",
            )
        )
        msgs = leader.check_leader_messages()
        assert len(msgs) == 1
        assert msgs[0]["from"] == "alice"
        assert msgs[0]["content"] == "Task completed!"

    def test_cleanup_with_active_members_raises(self, leader: TeamLeader) -> None:
        leader.spawn_member(name="alice", prompt="Work")
        with pytest.raises(RuntimeError, match="active members"):
            leader.cleanup()

    def test_cleanup_success(self, leader: TeamLeader) -> None:
        member = leader.spawn_member(name="alice", prompt="Work")
        member.active = False
        leader.cleanup()
        # Config should be removed
        config_path = leader._config_dir / "config.json"
        assert not config_path.exists()

    def test_config_persisted(self, leader: TeamLeader) -> None:
        leader.spawn_member(name="alice", prompt="Work")
        config_path = leader._config_dir / "config.json"
        assert config_path.exists()

        import json
        config = json.loads(config_path.read_text())
        assert config["name"] == "test-team"
        assert len(config["members"]) == 1
