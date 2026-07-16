"""INTENTIDE validators."""
from __future__ import annotations


def require_capacity(capacity: int) -> int:
    if not isinstance(capacity, int) or capacity < 0:
        raise ValueError("capacity must be a non-negative int")
    return capacity


def require_agent_id(agent_id: str) -> str:
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("agent_id must be a non-empty string")
    return agent_id.strip()
