"""Agentverse Chat Protocol helpers.

Thin wrappers around the standard chat protocol message types so the agent
modules stay readable. Imports `uagents_core` — only loaded inside agent
processes / the Bureau, never by the cascade, CLI, or API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
)


def chat_text(text: str, end_session: bool = False) -> ChatMessage:
    """Build a ChatMessage carrying a single text block (often a JSON envelope)."""
    content: list = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content)


def acknowledge(msg: ChatMessage) -> ChatAcknowledgement:
    return ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id
    )


def extract_text(msg: ChatMessage) -> str:
    """Concatenate all TextContent blocks of an incoming ChatMessage."""
    parts: list[str] = []
    for item in msg.content:
        if isinstance(item, TextContent):
            parts.append(item.text)
    return "\n".join(parts).strip()
