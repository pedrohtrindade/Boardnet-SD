"""Persistência SQLite local por processo; nenhum failover implícito."""
import json
import sqlite3
from pathlib import Path

class Store:
    def __init__(self, filepath):
        path=Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db=sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.commit()

    def put(self, key, data):
        with self.db:
            self.db.execute("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,json.dumps(data)))

    def all(self):
        return {key: json.loads(value) for key,value in self.db.execute("SELECT key,value FROM kv")}
