"""Session persistence — JSON file per session."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

_SAFE_SID = re.compile(r"^[a-f0-9]{12}$")


class SessionManager:
    def __init__(self, sessions_dir: str | Path):
        self.dir = Path(sessions_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "archive").mkdir(exist_ok=True)

    def create_session(self, title: str = "New Chat") -> str:
        sid = uuid.uuid4().hex[:12]
        data = {
            "title": title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "compressed_context": "",
            "messages": [],
        }
        self._write(sid, data)
        return sid

    def load_session(self, sid: str) -> list[dict]:
        data = self._read(sid)
        return data.get("messages", [])

    def load_session_for_agent(self, sid: str) -> list[dict]:
        """Return messages optimized for LLM: merge consecutive assistant msgs, inject compressed context."""
        data = self._read(sid)
        messages = data.get("messages", [])
        compressed = data.get("compressed_context", "")

        merged = self._merge_consecutive_assistant(messages)

        if compressed:
            merged.insert(0, {
                "role": "assistant",
                "content": f"[以下是之前对话的摘要]\n{compressed}",
            })
        return merged

    def save_message(self, sid: str, role: str, content: str, tool_calls: list | None = None):
        data = self._read(sid)
        msg: dict = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        data["messages"].append(msg)
        data["updated_at"] = time.time()
        self._write(sid, data)

    def list_sessions(self) -> list[dict]:
        sessions = []
        for f in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": f.stem,
                "title": data.get("title", "Untitled"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "message_count": len(data.get("messages", [])),
            })
        return sessions

    def rename_session(self, sid: str, title: str):
        data = self._read(sid)
        data["title"] = title
        self._write(sid, data)

    def delete_session(self, sid: str):
        path = self.dir / f"{sid}.json"
        if path.exists():
            path.unlink()

    def compress_history(self, sid: str, summary: str, n: int) -> int:
        data = self._read(sid)
        messages = data["messages"]
        if len(messages) < n:
            return 0

        archived = messages[:n]
        archive_path = self.dir / "archive" / f"{sid}_{int(time.time())}.json"
        archive_path.write_text(json.dumps(archived, ensure_ascii=False, indent=2), encoding="utf-8")

        data["messages"] = messages[n:]
        existing = data.get("compressed_context", "")
        data["compressed_context"] = f"{existing}\n---\n{summary}".strip() if existing else summary
        self._write(sid, data)
        return n

    def get_compressed_context(self, sid: str) -> str:
        data = self._read(sid)
        return data.get("compressed_context", "")

    def _merge_consecutive_assistant(self, messages: list[dict]) -> list[dict]:
        if not messages:
            return []
        merged = [messages[0].copy()]
        for msg in messages[1:]:
            if msg["role"] == "assistant" and merged[-1]["role"] == "assistant":
                merged[-1]["content"] += "\n" + msg["content"]
            else:
                merged.append(msg.copy())
        return merged

    def _read(self, sid: str) -> dict:
        if not _SAFE_SID.match(sid):
            return {"messages": [], "compressed_context": ""}
        path = self.dir / f"{sid}.json"
        if not path.exists():
            return {"messages": [], "compressed_context": ""}
        data = json.loads(path.read_text(encoding="utf-8"))
        # v1 migration: bare list -> v2 dict
        if isinstance(data, list):
            data = {"messages": data, "compressed_context": ""}
        return data

    def _write(self, sid: str, data: dict):
        if not _SAFE_SID.match(sid):
            return
        path = self.dir / f"{sid}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
