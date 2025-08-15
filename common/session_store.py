import json, sqlite3, time
from pathlib import Path
from typing import Optional
from datetime import datetime
from .models import SessionData

DB_PATH = Path('./session_store.sqlite3')

class SessionStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init()

    def _init(self):
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                '''
                CREATE TABLE IF NOT EXISTS sessions (
                  session_id TEXT PRIMARY KEY,
                  json TEXT NOT NULL,
                  updated_at INTEGER NOT NULL
                )
                '''
            )
            con.commit()
        finally:
            con.close()

    def upsert(self, data: SessionData) -> None:
    # DUMP THEO CHUẨN JSON (convert datetime → ISO string)
        js = data.model_dump(mode="json")
        js["updated_at"] = datetime.utcnow().isoformat()

        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                "REPLACE INTO sessions(session_id, json, updated_at) VALUES (?, ?, ?)",
                (data.session_id, json.dumps(js, ensure_ascii=False), int(time.time()))
            )
            con.commit()
        finally:
            con.close()


    def get(self, session_id: str) -> Optional[SessionData]:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute('SELECT json FROM sessions WHERE session_id=?', (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            js = json.loads(row[0])
            return SessionData(**js)
        finally:
            con.close()

    def update_fields(self, session_id: str, **fields):
        data = self.get(session_id)
        if not data:
            return None
        for k, v in fields.items():
            setattr(data, k, v)
        self.upsert(data)
        return data

    def delete(self, session_id: str) -> None:
        con = sqlite3.connect(self.db_path)
        try:
            con.execute('DELETE FROM sessions WHERE session_id=?', (session_id,))
            con.commit()
        finally:
            con.close()

    def cleanup(self, ttl_hours: int = 24):
        now = int(time.time())
        cutoff = now - ttl_hours * 3600
        con = sqlite3.connect(self.db_path)
        try:
            con.execute('DELETE FROM sessions WHERE updated_at < ?', (cutoff,))
            con.commit()
        finally:
            con.close()