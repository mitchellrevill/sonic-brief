from typing import Dict, Any, List, Optional
from threading import Lock


class SessionTracker:
    """In-memory, thread-safe session tracker intended for short-lived tracking in dev/test.

    Stores session entries keyed by session id and exposes simple helpers.
    """
    def __init__(self):
        self._lock = Lock()
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def upsert(self, session_id: str, data: Dict[str, Any]):
        """Insert or update a session entry."""
        with self._lock:
            self._sessions[session_id] = {**self._sessions.get(session_id, {}), **data}

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._sessions.get(session_id)

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [v.copy() for v in self._sessions.values()]

    def remove(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]


# Module-level singleton
_SESSION_TRACKER: Optional[SessionTracker] = None


def get_session_tracker() -> SessionTracker:
    global _SESSION_TRACKER
    if _SESSION_TRACKER is None:
        _SESSION_TRACKER = SessionTracker()
    return _SESSION_TRACKER
