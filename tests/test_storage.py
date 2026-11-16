import tempfile
import unittest
from pathlib import Path
from storage import Store

class TestStorage(unittest.TestCase):
    def test_roundtrip_across_connections(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rooms.sqlite3'
            store=Store(path)
            store.put('ABC123', {'board':[['.','w'],['b','.']], 'players':{'token':'Ana'}})
            store.db.close()
            recovered=Store(path)
            self.assertEqual(recovered.all()['ABC123']['players'],{'token':'Ana'})
            recovered.put('ABC123', {'board':[], 'players':{'token':'Bia'}})
            self.assertEqual(recovered.all()['ABC123']['players'],{'token':'Bia'})
            recovered.db.close()
