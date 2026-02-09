"""Inter-agent messaging system using file-based mailboxes."""

from __future__ import annotations

import json
from pathlib import Path

from filelock import FileLock

from wakamat.models import Message


class Mailbox:
    """File-based mailbox for inter-agent communication.

    Each agent has its own mailbox file. Messages are appended atomically
    using file locks to prevent corruption from concurrent writes.
    """

    def __init__(self, team_name: str, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.home() / ".wakamat" / "mailboxes"
        self._team_dir = self._base_dir / team_name
        self._team_dir.mkdir(parents=True, exist_ok=True)

    def _mailbox_path(self, member_id: str) -> Path:
        return self._team_dir / f"{member_id}.json"

    def _lock_path(self, member_id: str) -> Path:
        return self._team_dir / f"{member_id}.lock"

    def send(self, message: Message) -> Message:
        """Send a message to a recipient's mailbox."""
        path = self._mailbox_path(message.recipient)
        lock = FileLock(self._lock_path(message.recipient))

        with lock:
            messages = self._read_mailbox(path)
            messages.append(message)
            self._write_mailbox(path, messages)

        return message

    def broadcast(self, sender: str, content: str, member_ids: list[str]) -> list[Message]:
        """Send a message to all specified members."""
        messages = []
        for member_id in member_ids:
            if member_id == sender:
                continue
            msg = Message(sender=sender, recipient=member_id, content=content)
            self.send(msg)
            messages.append(msg)
        return messages

    def receive(self, member_id: str, mark_read: bool = True) -> list[Message]:
        """Get all unread messages for a member."""
        path = self._mailbox_path(member_id)
        lock = FileLock(self._lock_path(member_id))

        with lock:
            messages = self._read_mailbox(path)
            unread = [m for m in messages if not m.read]
            if mark_read and unread:
                for m in messages:
                    m.read = True
                self._write_mailbox(path, messages)

        return unread

    def get_all_messages(self, member_id: str) -> list[Message]:
        """Get all messages (read and unread) for a member."""
        path = self._mailbox_path(member_id)
        lock = FileLock(self._lock_path(member_id))

        with lock:
            return self._read_mailbox(path)

    def _read_mailbox(self, path: Path) -> list[Message]:
        if not path.exists():
            return []
        data = json.loads(path.read_text())
        return [Message.model_validate(m) for m in data]

    def _write_mailbox(self, path: Path, messages: list[Message]) -> None:
        data = [m.model_dump(mode="json") for m in messages]
        path.write_text(json.dumps(data, indent=2, default=str))

    def cleanup(self) -> None:
        """Remove all mailbox files for this team."""
        if self._team_dir.exists():
            for f in self._team_dir.iterdir():
                f.unlink()
            self._team_dir.rmdir()
