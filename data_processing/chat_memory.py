# chat_memory.py
import json, os
from collections import defaultdict

class PersistentMemory:
    def __init__(self, path="user_history.json"):
        self.path = path
        self.store = defaultdict(list)
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                try:
                    self.store = defaultdict(list, json.load(f))
                except:
                    self.store = defaultdict(list)

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.store, f, indent=2, ensure_ascii=False)

    def add_record(self, user_id, record):
        self.store[user_id].append(record)
        self._save()

    def get_history(self, user_id):
        return self.store[user_id]

    def reset(self, user_id):
        self.store[user_id] = []
        self._save()

memory = PersistentMemory()
