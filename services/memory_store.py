import os, json
from typing import Dict, Any, List

ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def artifact_path(session_id: str) -> str:
    return os.path.join(ARTIFACT_DIR, f"{session_id}.json")

def load_artifact(session_id: str) -> Dict[str, Any]:
    path = artifact_path(session_id)
    if not os.path.exists(path):
        raise FileNotFoundError("artifact missing")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_artifact(session: Dict[str, Any]):
    path = artifact_path(session["session_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)

def append_message(session_id: str, role: str, content: str):
    session = load_artifact(session_id)
    session.setdefault("chat", []).append({"role": role, "content": content})
    save_artifact(session)

def add_event(session_id: str, event: Dict[str, Any]):
    session = load_artifact(session_id)
    session.setdefault("learning_events", []).append(event)
    save_artifact(session)