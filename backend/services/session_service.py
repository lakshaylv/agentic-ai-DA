import threading
import uuid
from datetime import datetime, timezone

import pandas as pd


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, df: pd.DataFrame, filename: str = "") -> str:
        session_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._sessions[session_id] = {
                "df": df,
                "filename": filename,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "row_count": df.shape[0],
                "column_count": df.shape[1],
            }
        return session_id

    def get(self, session_id: str) -> pd.DataFrame | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session["df"]

    def get_metadata(self, session_id: str) -> dict | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return {
                "session_id": session_id,
                "filename": session["filename"],
                "created_at": session["created_at"],
                "row_count": session["row_count"],
                "column_count": session["column_count"],
            }

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False
            del self._sessions[session_id]
            return True

    def list_sessions(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "session_id": sid,
                    "filename": s["filename"],
                    "created_at": s["created_at"],
                    "row_count": s["row_count"],
                    "column_count": s["column_count"],
                }
                for sid, s in self._sessions.items()
            ]


session_store = SessionStore()
