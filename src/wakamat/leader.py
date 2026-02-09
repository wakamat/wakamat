"""Team leader orchestration."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from wakamat.agent import AgentRunner
from wakamat.messaging import Mailbox
from wakamat.models import MemberRole, Task, Team, TeamMember
from wakamat.task_manager import TaskManager


class TeamLeader:
    """Orchestrates an agent team.

    The leader creates the team, spawns members, assigns tasks,
    monitors progress, and cleans up when done.
    """

    def __init__(
        self,
        team_name: str,
        leader_name: str = "leader",
        model: str = "claude-sonnet-4-5-20250929",
        base_dir: Path | None = None,
        api_key: str | None = None,
    ) -> None:
        self.api_key = api_key
        self._base_dir = base_dir or Path.home() / ".wakamat"

        # Create leader member
        leader = TeamMember(name=leader_name, role=MemberRole.LEADER, model=model)
        self.team = Team(name=team_name, leader=leader)

        # Initialize subsystems
        self.task_manager = TaskManager(team_name, self._base_dir / "tasks")
        self.mailbox = Mailbox(team_name, self._base_dir / "mailboxes")

        # Save team config
        self._config_dir = self._base_dir / "teams" / team_name
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._save_config()

        self._runners: dict[str, AgentRunner] = {}
        self._agent_tasks: dict[str, asyncio.Task[str]] = {}

    def _save_config(self) -> None:
        """Persist team config to disk."""
        config = self.team.model_dump(mode="json")
        config_path = self._config_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2, default=str))

    def _member_names(self) -> dict[str, str]:
        """Build name -> id mapping for all team agents."""
        mapping: dict[str, str] = {}
        mapping[self.team.leader.name] = self.team.leader.id
        for m in self.team.members:
            mapping[m.name] = m.id
        return mapping

    def spawn_member(
        self,
        name: str,
        prompt: str,
        model: str | None = None,
        max_turns: int = 50,
    ) -> TeamMember:
        """Create and register a new team member.

        The member is not started until run() or run_member() is called.
        """
        member = TeamMember(
            name=name,
            prompt=prompt,
            model=model or self.team.leader.model,
        )
        self.team.members.append(member)
        self._save_config()

        runner = AgentRunner(
            member=member,
            team_name=self.team.name,
            task_manager=self.task_manager,
            mailbox=self.mailbox,
            leader_id=self.team.leader.id,
            member_names=self._member_names(),
            api_key=self.api_key,
            max_turns=max_turns,
        )
        self._runners[member.id] = runner
        return member

    def add_task(
        self,
        title: str,
        description: str = "",
        depends_on: list[str] | None = None,
        assign_to: str | None = None,
    ) -> Task:
        """Add a task to the shared task list."""
        task = Task(
            title=title,
            description=description,
            depends_on=depends_on or [],
        )
        if assign_to:
            member = self.team.get_member_by_name(assign_to)
            if member:
                task.assigned_to = member.id
        self.task_manager.add_task(task)
        self.team.tasks.append(task)
        return task

    def add_tasks(self, tasks: list[dict[str, Any]]) -> list[Task]:
        """Add multiple tasks at once.

        Each dict should have 'title' and optionally 'description',
        'depends_on', and 'assign_to' keys.
        """
        result = []
        for t in tasks:
            task = self.add_task(
                title=t["title"],
                description=t.get("description", ""),
                depends_on=t.get("depends_on"),
                assign_to=t.get("assign_to"),
            )
            result.append(task)
        return result

    async def run_member(self, member_id: str) -> str:
        """Start a single team member running."""
        runner = self._runners.get(member_id)
        if runner is None:
            raise ValueError(f"No runner found for member {member_id}")
        return await runner.run()

    async def run(self) -> dict[str, str]:
        """Start all team members and wait for them to complete.

        Returns a dict mapping member names to their final output.
        """
        # Update member_names for all runners (in case members were added after runner creation)
        names = self._member_names()
        for runner in self._runners.values():
            runner.member_names = names

        # Launch all members concurrently
        tasks: dict[str, asyncio.Task[str]] = {}
        for member in self.team.members:
            if member.id in self._runners:
                coro = self.run_member(member.id)
                tasks[member.name] = asyncio.create_task(coro)

        # Wait for all to complete
        results: dict[str, str] = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = f"Error: {e}"

        return results

    def check_leader_messages(self) -> list[dict[str, str]]:
        """Check messages sent to the leader."""
        messages = self.mailbox.receive(self.team.leader.id)
        id_to_name = {v: k for k, v in self._member_names().items()}
        return [
            {
                "from": id_to_name.get(m.sender, m.sender),
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in messages
        ]

    def get_status(self) -> dict[str, Any]:
        """Get team status overview."""
        tasks = self.task_manager.get_tasks()
        id_to_name = {v: k for k, v in self._member_names().items()}
        return {
            "team_name": self.team.name,
            "members": [
                {"name": m.name, "active": m.active, "role": m.role.value}
                for m in self.team.all_agents
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "assigned_to": id_to_name.get(t.assigned_to, t.assigned_to)
                    if t.assigned_to
                    else None,
                    "result": t.result,
                }
                for t in tasks
            ],
            "all_done": self.task_manager.is_all_done(),
        }

    def shutdown_member(self, name: str) -> bool:
        """Request a member to shut down by sending a shutdown message."""
        member = self.team.get_member_by_name(name)
        if member is None:
            return False
        msg_content = "The leader has requested you to shut down. Please finish your current work and use the shutdown tool."
        from wakamat.models import Message

        msg = Message(
            sender=self.team.leader.id,
            recipient=member.id,
            content=msg_content,
        )
        self.mailbox.send(msg)
        return True

    def cleanup(self) -> None:
        """Clean up all team resources."""
        active = [m for m in self.team.members if m.active]
        if active:
            names = ", ".join(m.name for m in active)
            raise RuntimeError(
                f"Cannot clean up: active members still running: {names}. "
                "Shut them down first."
            )
        self.task_manager.cleanup()
        self.mailbox.cleanup()
        # Remove config
        config_path = self._config_dir / "config.json"
        if config_path.exists():
            config_path.unlink()
        if self._config_dir.exists():
            self._config_dir.rmdir()
