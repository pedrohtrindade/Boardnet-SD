"""Testes isolados do status do gateway (sem dependência de rede)."""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

# Garante que importar gateway não escreva no banco das partidas do usuário.
_tmp = tempfile.TemporaryDirectory()
os.environ.setdefault('GATEWAY_DB', os.path.join(_tmp.name, 'gateway.sqlite3'))
import gateway


class MonitoringTest(unittest.IsolatedAsyncioTestCase):
    async def test_workers_online_and_degraded(self):
        async def stub(url):
            if url.endswith('1'):
                return {'server': 'Servidor 1', 'rooms': 3, 'connections': 2,
                        'active_rooms': 1, 'uptime_seconds': 15,
                        'rooms_by_game': {'chess': 1, 'checkers': 1, 'morris': 1}}
            return None
        with patch.object(gateway, 'WORKERS', ['http://server1','http://server2']), \
             patch.object(gateway, 'check_worker', side_effect=stub):
            result = await gateway.cluster()
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['online_workers'], 1)
        self.assertEqual(result['workers'][0]['connections'], 2)
        self.assertIsNone(result['workers'][1]['rooms'])
        self.assertFalse(result['failover'])

    async def test_cluster_healthy(self):
        with patch.object(gateway, 'WORKERS', ['w1','w2']), \
             patch.object(gateway, 'check_worker', return_value={'ok':True, 'rooms':0, 'connections':0}):
            result = await gateway.cluster()
        self.assertEqual(result['status'], 'online')
        self.assertEqual(result['online_workers'], 2)

    async def test_cluster_all_offline(self):
        with patch.object(gateway, 'WORKERS', ['w1','w2']), \
             patch.object(gateway, 'check_worker', return_value=None):
            result = await gateway.cluster()
        self.assertEqual(result['status'], 'offline')

    async def test_gateway_health(self):
        result = await gateway.health()
        self.assertTrue(result['ok'])
        self.assertGreaterEqual(result['uptime_seconds'], 0)


if __name__ == '__main__':
    unittest.main()
