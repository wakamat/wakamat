"""Core data models for Agent Teams."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task in the shared task list."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MemberRole(str, Enum):
    """Role of a team member."""

    LEADER = "leader"
    MEMBER = "member"


class Task(BaseModel):
    """A work item in the shared task list."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    result: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_blocked(self) -> bool:
        """Check if this task has unresolved dependencies.

        Note: This only checks if depends_on is non-empty.
        Use TaskManager.is_task_blocked() to check actual dependency statuses.
        """
        return len(self.depends_on) > 0


class Message(BaseModel):
    """A message between team members."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    sender: str
    recipient: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False


class TeamMember(BaseModel):
    """A member of an agent team."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    role: MemberRole = MemberRole.MEMBER
    prompt: str = ""
    model: str = "claude-sonnet-4-5-20250929"
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: list[dict[str, Any]] = Field(default_factory=list)


class Team(BaseModel):
    """An agent team with a leader and members."""

    name: str
    leader: TeamMember
    members: list[TeamMember] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_member(self, member_id: str) -> TeamMember | None:
        """Get a team member by ID."""
        if self.leader.id == member_id:
            return self.leader
        return next((m for m in self.members if m.id == member_id), None)

    def get_member_by_name(self, name: str) -> TeamMember | None:
        """Get a team member by name."""
        if self.leader.name == name:
            return self.leader
        return next((m for m in self.members if m.name == name), None)

    @property
    def active_members(self) -> list[TeamMember]:
        """Get all active team members (excluding leader)."""
        return [m for m in self.members if m.active]

    @property
    def all_agents(self) -> list[TeamMember]:
        """Get all agents including leader."""
        return [self.leader] + self.members
