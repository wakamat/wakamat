"""Tests for the messaging system."""

import tempfile
from pathlib import Path

import pytest

from wakamat.messaging import Mailbox
from wakamat.models import Message


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mailbox(tmp_dir: Path) -> Mailbox:
    return Mailbox("test-team", base_dir=tmp_dir)


class TestMailbox:
    def test_send_and_receive(self, mailbox: Mailbox) -> None:
        msg = Message(sender="alice", recipient="bob", content="Hello Bob!")
        mailbox.send(msg)

        received = mailbox.receive("bob")
        assert len(received) == 1
        assert received[0].content == "Hello Bob!"
        assert received[0].sender == "alice"

    def test_receive_marks_read(self, mailbox: Mailbox) -> None:
        msg = Message(sender="alice", recipient="bob", content="Hello")
        mailbox.send(msg)

        # First receive
        received = mailbox.receive("bob")
        assert len(received) == 1

        # Second receive should return empty (already read)
        received2 = mailbox.receive("bob")
        assert len(received2) == 0

    def test_receive_without_marking_read(self, mailbox: Mailbox) -> None:
        msg = Message(sender="alice", recipient="bob", content="Hello")
        mailbox.send(msg)

        received = mailbox.receive("bob", mark_read=False)
        assert len(received) == 1

        # Should still be unread
        received2 = mailbox.receive("bob")
        assert len(received2) == 1

    def test_multiple_messages(self, mailbox: Mailbox) -> None:
        mailbox.send(Message(sender="alice", recipient="bob", content="Message 1"))
        mailbox.send(Message(sender="charlie", recipient="bob", content="Message 2"))

        received = mailbox.receive("bob")
        assert len(received) == 2

    def test_broadcast(self, mailbox: Mailbox) -> None:
        members = ["alice", "bob", "charlie"]
        messages = mailbox.broadcast("alice", "Hello everyone!", members)

        # Should send to bob and charlie (not alice)
        assert len(messages) == 2

        bob_msgs = mailbox.receive("bob")
        assert len(bob_msgs) == 1
        assert bob_msgs[0].content == "Hello everyone!"

        charlie_msgs = mailbox.receive("charlie")
        assert len(charlie_msgs) == 1

        # Alice should not get her own broadcast
        alice_msgs = mailbox.receive("alice")
        assert len(alice_msgs) == 0

    def test_get_all_messages(self, mailbox: Mailbox) -> None:
        mailbox.send(Message(sender="a", recipient="b", content="msg1"))
        mailbox.send(Message(sender="a", recipient="b", content="msg2"))
        mailbox.receive("b")  # marks as read

        mailbox.send(Message(sender="a", recipient="b", content="msg3"))

        all_msgs = mailbox.get_all_messages("b")
        assert len(all_msgs) == 3

    def test_empty_mailbox(self, mailbox: Mailbox) -> None:
        received = mailbox.receive("nonexistent")
        assert len(received) == 0

    def test_cleanup(self, mailbox: Mailbox) -> None:
        mailbox.send(Message(sender="a", recipient="b", content="test"))
        mailbox.cleanup()
        # After cleanup, should be empty
        mb2 = Mailbox("test-team", base_dir=mailbox._base_dir)
        assert len(mb2.receive("b")) == 0
