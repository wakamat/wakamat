"""Tests for core data models."""

from wakamat.models import (
    MemberRole,
    Message,
    Task,
    TaskStatus,
    Team,
    TeamMember,
)


class TestTask:
    def test_create_task(self) -> None:
        task = Task(title="Test task", description="Do something")
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.assigned_to is None
        assert len(task.id) == 8

    def test_task_no_deps_not_blocked(self) -> None:
        task = Task(title="No deps")
        assert not task.is_blocked

    def test_task_with_deps_is_blocked(self) -> None:
        task = Task(title="Has deps", depends_on=["abc"])
        assert task.is_blocked


class TestTeamMember:
    def test_create_member(self) -> None:
        member = TeamMember(name="alice", prompt="Review code")
        assert member.name == "alice"
        assert member.role == MemberRole.MEMBER
        assert member.active is True

    def test_leader_role(self) -> None:
        leader = TeamMember(name="leader", role=MemberRole.LEADER)
        assert leader.role == MemberRole.LEADER


class TestTeam:
    def _make_team(self) -> Team:
        leader = TeamMember(name="leader", role=MemberRole.LEADER)
        m1 = TeamMember(name="alice")
        m2 = TeamMember(name="bob")
        return Team(name="test-team", leader=leader, members=[m1, m2])

    def test_get_member_by_name(self) -> None:
        team = self._make_team()
        assert team.get_member_by_name("alice") is not None
        assert team.get_member_by_name("alice").name == "alice"
        assert team.get_member_by_name("unknown") is None

    def test_get_leader_by_name(self) -> None:
        team = self._make_team()
        assert team.get_member_by_name("leader") is not None
        assert team.get_member_by_name("leader").role == MemberRole.LEADER

    def test_active_members(self) -> None:
        team = self._make_team()
        assert len(team.active_members) == 2
        team.members[0].active = False
        assert len(team.active_members) == 1

    def test_all_agents(self) -> None:
        team = self._make_team()
        assert len(team.all_agents) == 3  # leader + 2 members


class TestMessage:
    def test_create_message(self) -> None:
        msg = Message(sender="a", recipient="b", content="hello")
        assert msg.sender == "a"
        assert msg.recipient == "b"
        assert msg.read is False
