"""CLI interface for wakamat Agent Teams."""

from __future__ import annotations

import asyncio
import json
import sys

import click
from rich.console import Console
from rich.table import Table

from wakamat.leader import TeamLeader
from wakamat.models import Task

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """wakamat - Agent Teams orchestration framework."""
    pass


@main.command()
@click.argument("team_name")
@click.option("--leader-name", default="leader", help="Name for the team leader.")
@click.option("--model", default="claude-sonnet-4-5-20250929", help="Default model for agents.")
def create(team_name: str, leader_name: str, model: str) -> None:
    """Create a new agent team."""
    leader = TeamLeader(team_name=team_name, leader_name=leader_name, model=model)
    console.print(f"[green]Team '{team_name}' created.[/green]")
    console.print(f"  Leader: {leader_name} (ID: {leader.team.leader.id})")


@main.command()
@click.argument("team_name")
@click.argument("member_name")
@click.option("--prompt", "-p", required=True, help="Instructions for this team member.")
@click.option("--model", default=None, help="Model to use (defaults to team model).")
def spawn(team_name: str, member_name: str, prompt: str, model: str | None) -> None:
    """Spawn a new team member."""
    leader = TeamLeader(team_name=team_name)
    member = leader.spawn_member(name=member_name, prompt=prompt, model=model)
    console.print(f"[green]Spawned member '{member_name}' (ID: {member.id})[/green]")


@main.command(name="add-task")
@click.argument("team_name")
@click.argument("title")
@click.option("--description", "-d", default="", help="Task description.")
@click.option("--depends-on", multiple=True, help="Task IDs this task depends on.")
@click.option("--assign-to", default=None, help="Member name to assign to.")
def add_task(
    team_name: str, title: str, description: str, depends_on: tuple[str, ...], assign_to: str | None
) -> None:
    """Add a task to the shared task list."""
    leader = TeamLeader(team_name=team_name)
    task = leader.add_task(
        title=title,
        description=description,
        depends_on=list(depends_on) if depends_on else None,
        assign_to=assign_to,
    )
    console.print(f"[green]Task added: '{title}' (ID: {task.id})[/green]")


@main.command()
@click.argument("team_name")
def status(team_name: str) -> None:
    """Show team status."""
    leader = TeamLeader(team_name=team_name)
    st = leader.get_status()

    # Members table
    member_table = Table(title=f"Team: {st['team_name']}")
    member_table.add_column("Name")
    member_table.add_column("Role")
    member_table.add_column("Active")

    for m in st["members"]:
        active_str = "[green]yes[/green]" if m["active"] else "[red]no[/red]"
        member_table.add_row(m["name"], m["role"], active_str)
    console.print(member_table)

    # Tasks table
    if st["tasks"]:
        task_table = Table(title="Tasks")
        task_table.add_column("ID")
        task_table.add_column("Title")
        task_table.add_column("Status")
        task_table.add_column("Assigned To")

        status_colors = {
            "pending": "yellow",
            "in_progress": "blue",
            "completed": "green",
            "failed": "red",
        }
        for t in st["tasks"]:
            color = status_colors.get(t["status"], "white")
            task_table.add_row(
                t["id"],
                t["title"],
                f"[{color}]{t['status']}[/{color}]",
                t["assigned_to"] or "-",
            )
        console.print(task_table)

    if st["all_done"]:
        console.print("[green]All tasks completed![/green]")


@main.command()
@click.argument("team_name")
def run(team_name: str) -> None:
    """Start all team members and run until completion."""
    leader = TeamLeader(team_name=team_name)

    if not leader.team.members:
        console.print("[yellow]No team members to run. Spawn members first.[/yellow]")
        return

    console.print(f"[blue]Starting team '{team_name}' with {len(leader.team.members)} members...[/blue]")

    results = asyncio.run(leader.run())

    console.print("\n[green]Team run completed.[/green]")
    for name, result in results.items():
        console.print(f"\n[bold]{name}:[/bold]")
        console.print(result[:500] if len(result) > 500 else result)


@main.command()
@click.argument("team_name")
def messages(team_name: str) -> None:
    """Check messages sent to the leader."""
    leader = TeamLeader(team_name=team_name)
    msgs = leader.check_leader_messages()

    if not msgs:
        console.print("[dim]No new messages.[/dim]")
        return

    for m in msgs:
        console.print(f"[bold]{m['from']}[/bold] ({m['timestamp']}):")
        console.print(f"  {m['content']}")


@main.command()
@click.argument("team_name")
def cleanup(team_name: str) -> None:
    """Clean up team resources."""
    leader = TeamLeader(team_name=team_name)
    try:
        leader.cleanup()
        console.print(f"[green]Team '{team_name}' cleaned up.[/green]")
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")


@main.command()
@click.argument("team_name")
@click.argument("description")
@click.option("--members", "-m", default=3, help="Number of team members to spawn.")
@click.option("--model", default="claude-sonnet-4-5-20250929", help="Model to use.")
def quick(team_name: str, description: str, members: int, model: str) -> None:
    """Quick-start: create a team, auto-generate members and tasks, and run.

    Example:
        wakamat quick my-review "Review PR #142 for security, performance, and tests"
    """
    leader = TeamLeader(team_name=team_name, model=model)
    console.print(f"[green]Team '{team_name}' created.[/green]")

    # Use Claude to plan the team structure
    import anthropic

    client = anthropic.Anthropic()
    planning_response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": (
                    f"I need to create an agent team for this task: {description}\n\n"
                    f"Create exactly {members} team members with distinct roles. "
                    "Also create tasks for each member.\n\n"
                    "Respond with JSON only (no markdown):\n"
                    '{"members": [{"name": "...", "prompt": "..."}], '
                    '"tasks": [{"title": "...", "description": "...", "assign_to": "member_name"}]}'
                ),
            }
        ],
    )

    plan_text = planning_response.content[0].text
    # Extract JSON from response
    try:
        plan = json.loads(plan_text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = plan_text.find("{")
        end = plan_text.rfind("}") + 1
        if start >= 0 and end > start:
            plan = json.loads(plan_text[start:end])
        else:
            console.print("[red]Failed to parse team plan from Claude.[/red]")
            return

    # Spawn members
    for m in plan["members"]:
        member = leader.spawn_member(name=m["name"], prompt=m["prompt"])
        console.print(f"  Spawned: {m['name']} (ID: {member.id})")

    # Add tasks
    for t in plan["tasks"]:
        task = leader.add_task(
            title=t["title"],
            description=t.get("description", ""),
            assign_to=t.get("assign_to"),
        )
        console.print(f"  Task: {t['title']} (ID: {task.id})")

    console.print(f"\n[blue]Starting team with {len(plan['members'])} members...[/blue]")
    results = asyncio.run(leader.run())

    console.print("\n[green]Team run completed![/green]")
    for name, result in results.items():
        console.print(f"\n[bold]{name}:[/bold]")
        console.print(result[:500] if len(result) > 500 else result)


if __name__ == "__main__":
    main()
