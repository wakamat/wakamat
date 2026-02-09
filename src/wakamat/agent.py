"""Agent execution engine using Claude API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import anthropic

from wakamat.messaging import Mailbox
from wakamat.models import Message, Task, TeamMember
from wakamat.task_manager import TaskManager


# Tool definitions that agents can use
AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "send_message",
        "description": "Send a message to another team member.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient_name": {
                    "type": "string",
                    "description": "Name of the team member to send the message to.",
                },
                "content": {
                    "type": "string",
                    "description": "The message content.",
                },
            },
            "required": ["recipient_name", "content"],
        },
    },
    {
        "name": "check_messages",
        "description": "Check for new messages from other team members.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "claim_task",
        "description": "Claim the next available task from the shared task list.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "complete_task",
        "description": "Mark the current task as completed with a result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task to complete.",
                },
                "result": {
                    "type": "string",
                    "description": "The result or output of the completed task.",
                },
            },
            "required": ["task_id", "result"],
        },
    },
    {
        "name": "view_tasks",
        "description": "View all tasks in the shared task list with their statuses.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "report_to_leader",
        "description": "Send a status update or report to the team leader.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The report content.",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "shutdown",
        "description": "Gracefully shut down this agent. Use when all assigned tasks are done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for shutting down.",
                },
            },
            "required": ["reason"],
        },
    },
]


class AgentRunner:
    """Runs a single agent (team member) in its own async loop.

    Each agent has its own Claude API conversation, can send/receive messages,
    claim tasks, and report results.
    """

    def __init__(
        self,
        member: TeamMember,
        team_name: str,
        task_manager: TaskManager,
        mailbox: Mailbox,
        leader_id: str,
        member_names: dict[str, str],  # name -> id mapping
        api_key: str | None = None,
        max_turns: int = 50,
    ) -> None:
        self.member = member
        self.team_name = team_name
        self.task_manager = task_manager
        self.mailbox = mailbox
        self.leader_id = leader_id
        self.member_names = member_names
        self.max_turns = max_turns
        self._client = anthropic.Anthropic(api_key=api_key)
        self._conversation: list[dict[str, Any]] = []
        self._running = True
        self._current_task_id: str | None = None

    def _build_system_prompt(self) -> str:
        teammates = ", ".join(
            n for n in self.member_names if n != self.member.name
        )
        return (
            f"You are '{self.member.name}', a team member in an agent team called '{self.team_name}'.\n"
            f"Your teammates are: {teammates}\n\n"
            f"Your role and instructions:\n{self.member.prompt}\n\n"
            "You have tools to communicate with teammates, claim and complete tasks, "
            "and report to the leader. Work autonomously on your assigned tasks. "
            "When you finish all your work, use the shutdown tool.\n\n"
            "Guidelines:\n"
            "- Check messages regularly to stay coordinated\n"
            "- Claim tasks before working on them\n"
            "- Report meaningful findings to the leader\n"
            "- Share relevant discoveries with teammates\n"
            "- Shut down when all your work is done"
        )

    def _handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Handle a tool call from the agent and return the result."""
        if tool_name == "send_message":
            recipient_name = tool_input["recipient_name"]
            recipient_id = self.member_names.get(recipient_name)
            if recipient_id is None:
                return f"Error: Unknown team member '{recipient_name}'"
            msg = Message(
                sender=self.member.id,
                recipient=recipient_id,
                content=tool_input["content"],
            )
            self.mailbox.send(msg)
            return f"Message sent to {recipient_name}"

        elif tool_name == "check_messages":
            messages = self.mailbox.receive(self.member.id)
            if not messages:
                return "No new messages."
            # Resolve sender names
            id_to_name = {v: k for k, v in self.member_names.items()}
            lines = []
            for m in messages:
                sender_name = id_to_name.get(m.sender, m.sender)
                lines.append(f"From {sender_name}: {m.content}")
            return "\n".join(lines)

        elif tool_name == "claim_task":
            task = self.task_manager.claim_next(self.member.id)
            if task is None:
                return "No available tasks to claim."
            self._current_task_id = task.id
            return f"Claimed task '{task.title}' (ID: {task.id}): {task.description}"

        elif tool_name == "complete_task":
            task_id = tool_input["task_id"]
            result = tool_input["result"]
            task = self.task_manager.complete_task(task_id, result)
            if task is None:
                return f"Error: Task '{task_id}' not found."
            self._current_task_id = None
            # Notify leader
            msg = Message(
                sender=self.member.id,
                recipient=self.leader_id,
                content=f"Completed task '{task.title}': {result}",
            )
            self.mailbox.send(msg)
            return f"Task '{task.title}' marked as completed."

        elif tool_name == "view_tasks":
            tasks = self.task_manager.get_tasks()
            if not tasks:
                return "No tasks in the task list."
            id_to_name = {v: k for k, v in self.member_names.items()}
            lines = []
            for t in tasks:
                assignee = id_to_name.get(t.assigned_to, t.assigned_to) if t.assigned_to else "unassigned"
                lines.append(
                    f"[{t.status.value}] {t.title} (ID: {t.id}) - assigned to: {assignee}"
                )
            return "\n".join(lines)

        elif tool_name == "report_to_leader":
            msg = Message(
                sender=self.member.id,
                recipient=self.leader_id,
                content=tool_input["content"],
            )
            self.mailbox.send(msg)
            return "Report sent to leader."

        elif tool_name == "shutdown":
            self._running = False
            reason = tool_input.get("reason", "No reason given")
            # Notify leader
            msg = Message(
                sender=self.member.id,
                recipient=self.leader_id,
                content=f"Shutting down: {reason}",
            )
            self.mailbox.send(msg)
            return f"Shutting down: {reason}"

        return f"Unknown tool: {tool_name}"

    async def run(self) -> str:
        """Run the agent loop until shutdown or max turns reached."""
        self._conversation = [
            {"role": "user", "content": f"Begin your work. {self.member.prompt}"}
        ]

        for turn in range(self.max_turns):
            if not self._running:
                break

            response = await asyncio.to_thread(
                self._client.messages.create,
                model=self.member.model,
                max_tokens=4096,
                system=self._build_system_prompt(),
                tools=AGENT_TOOLS,
                messages=self._conversation,
            )

            # Build assistant message
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            self._conversation.append({"role": "assistant", "content": assistant_content})

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._handle_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if tool_results:
                self._conversation.append({"role": "user", "content": tool_results})

            # If stop_reason is end_turn and no tool calls, the agent is done thinking
            if response.stop_reason == "end_turn" and not tool_results:
                break

        self.member.active = False
        final_text = ""
        for block in response.content:
            if block.type == "text":
                final_text += block.text
        return final_text
