"""Inicia e supervisiona dois workers e um gateway localmente, sem Docker.

Se um processo encerrar inesperadamente, tenta reiniciá-lo mantendo o mesmo
SQLite. Isso NÃO é failover: o worker original volta no mesmo endereço/porta.
"""
import os
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

DATA = Path(__file__).resolve().parent / '.boardnet_data'
DATA.mkdir(exist_ok=True)

COMMANDS = [
    ('Servidor 1', 'worker:app', 8001, {'SERVER_ID':'Servidor 1','WORKER_DB':str(DATA/'worker1.sqlite3')}),
    ('Servidor 2', 'worker:app', 8002, {'SERVER_ID':'Servidor 2','WORKER_DB':str(DATA/'worker2.sqlite3')}),
    ('Gateway', 'gateway:app', 8000, {'WORKER_URLS':'http://127.0.0.1:8001,http://127.0.0.1:8002',
                                     'GATEWAY_DB':str(DATA/'gateway.sqlite3')}),
]
RESTART_DELAY = 2
MAX_RESTARTS = 5
RESTART_WINDOW = 60


def launch(config):
    name, module, port, extra = config
    env = os.environ.copy()
    env.update(extra)
    p = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', module, '--host',
         '0.0.0.0' if name == 'Gateway' else '127.0.0.1', '--port', str(port)],
        env=env, cwd=str(Path(__file__).resolve().parent),
    )
    print(f'{name}: PID {p.pid}, porta {port}', flush=True)
    return p


def main():
    processes = {}
    restart_history = {config[0]: deque() for config in COMMANDS}
    try:
        for config in COMMANDS:
            processes[config[0]] = launch(config)
        print('BoardNet: http://127.0.0.1:8000 | Ctrl+C para encerrar todos.', flush=True)
        print('Supervisão: até 5 reinicializações por processo em 60 segundos.', flush=True)
        while True:
            time.sleep(.5)
            for config in COMMANDS:
                name = config[0]
                p = processes[name]
                if p.poll() is None:
                    continue
                now = time.monotonic()
                history = restart_history[name]
                while history and now-history[0] > RESTART_WINDOW:
                    history.popleft()
                if len(history) >= MAX_RESTARTS:
                    raise RuntimeError(f'{name} encerrou repetidamente (PID {p.pid}, código {p.returncode}); '
                                       f'limite de {MAX_RESTARTS} tentativas em {RESTART_WINDOW}s atingido.')
                history.append(now)
                print(f'AVISO: {name} encerrou (código {p.returncode}). Reiniciando em {RESTART_DELAY}s...', flush=True)
                time.sleep(RESTART_DELAY)
                processes[name] = launch(config)
    except KeyboardInterrupt:
        print('\nEncerrando BoardNet...', flush=True)
    finally:
        for p in reversed(list(processes.values())):
            if p.poll() is None:
                p.terminate()
        for p in reversed(list(processes.values())):
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()


if __name__ == '__main__':
    main()
