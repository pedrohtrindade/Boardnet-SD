"""Gateway da BoardNet: roteamento por sala, registro SQLite e monitoramento.

Não implementa failover nem replicação de estados dos jogos.
"""
import asyncio
import os
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
from storage import Store

app = FastAPI(title="BoardNet - Gateway distribuído")
app.mount('/static', StaticFiles(directory=Path(__file__).resolve().parent / 'static'), name='static')
BASE = Path(__file__).resolve().parent
STARTED_AT = time.monotonic()
WORKERS = [url.strip().rstrip("/") for url in os.getenv(
    "WORKER_URLS", "http://127.0.0.1:8001,http://127.0.0.1:8002"
).split(",") if url.strip()]
REGISTRY_DB=os.getenv('GATEWAY_DB',str(BASE / '.boardnet_data' / 'gateway.sqlite3'))
store=Store(REGISTRY_DB)
room_owner: dict[str,str] = store.all()
registry_lock = asyncio.Lock()
next_worker = len(room_owner) % max(len(WORKERS),1)

@app.get("/")
async def index():
    return FileResponse(BASE / "static" / "index.html")

async def request_worker(method, worker, endpoint, json=None):
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.request(method, worker + endpoint, json=json)
    except (httpx.RequestError, httpx.TimeoutException):
        raise HTTPException(503, "Servidor da partida indisponível.")
    if not response.is_success:
        try:
            detail = response.json().get("detail", "Erro no servidor de partidas.")
        except ValueError:
            detail = "Erro no servidor de partidas."
        raise HTTPException(response.status_code, detail)
    return response.json()

async def check_worker(worker):
    try:
        return await request_worker("GET", worker, "/api/health")
    except HTTPException:
        return None

@app.get('/api/health')
async def health():
    return {'ok': True, 'service': 'gateway', 'uptime_seconds': int(time.monotonic()-STARTED_AT)}

@app.get("/api/cluster")
async def cluster():
    healths = await asyncio.gather(*(check_worker(w) for w in WORKERS))
    workers = [{
        'server': (h or {}).get('server',f'Servidor {i+1}'),
        'online': bool(h), 'rooms': (h or {}).get('rooms'),
        'rooms_by_game': (h or {}).get('rooms_by_game'),
        'active_rooms': (h or {}).get('active_rooms'),
        'connections': (h or {}).get('connections'),
        'uptime_seconds': (h or {}).get('uptime_seconds'),
    } for i,h in enumerate(healths)]
    online = sum(w['online'] for w in workers)
    return {
        'gateway': {'online': True, 'uptime_seconds': int(time.monotonic()-STARTED_AT)},
        'workers': workers, 'online_workers': online,
        'status': 'online' if online == len(WORKERS) and online > 0 else 'degraded' if online else 'offline',
        'registered_rooms': len(room_owner), 'persistence': 'sqlite',
        'failover': False,
        'note': 'Salas não migram de worker automaticamente. Partidas persistem no SQLite do worker de origem.'
    }

@app.post("/api/rooms")
async def create_room(data:dict):
    global next_worker
    async with registry_lock:
        if not WORKERS:
            raise HTTPException(503, "Nenhum servidor configurado.")
        # Round Robin: seleciona o próximo worker disponível.
        for attempt in range(len(WORKERS)):
            idx = (next_worker+attempt)%len(WORKERS)
            worker=WORKERS[idx]
            if await check_worker(worker) is None:
                continue
            response=await request_worker("POST",worker,"/api/rooms",json=data)
            code=response["code"]
            if code in room_owner:
                # Colisão extremamente rara; não registrar a sala duplicada.
                continue
            room_owner[code]=worker
            store.put(code,worker)
            next_worker=(idx+1)%len(WORKERS)
            return response
        raise HTTPException(503,"Nenhum servidor de partidas disponível.")

def owner(code):
    worker=room_owner.get(code.upper())
    if not worker:
        raise HTTPException(404, "Sala não encontrada neste gateway.")
    return worker

@app.post("/api/rooms/{code}/join")
async def join_room(code:str,data:dict):
    code=code.strip().upper()
    return await request_worker("POST",owner(code),f"/api/rooms/{code}/join",json=data)

@app.get("/api/rooms/{code}")
async def get_room(code:str):
    code=code.strip().upper()
    return await request_worker("GET",owner(code),f"/api/rooms/{code}")

@app.websocket("/ws/{code}/{token}")
async def relay_socket(ws:WebSocket,code:str,token:str):
    code=code.upper()
    worker=room_owner.get(code)
    if not worker:
        await ws.close(code=1008)
        return
    ws_url=worker.replace("http://","ws://",1).replace("https://","wss://",1)
    # Token é gerado pelo worker. WebSocket continua validado no worker.
    accepted = False
    try:
        async with connect(f"{ws_url}/ws/{code}/{token}",open_timeout=5,ping_interval=20) as backend:
            await ws.accept()
            accepted = True
            async def browser_to_worker():
                while True:
                    msg=await ws.receive_text()
                    await backend.send(msg)
            async def worker_to_browser():
                async for msg in backend:
                    await ws.send_text(msg)
            tasks=[asyncio.create_task(browser_to_worker()),asyncio.create_task(worker_to_browser())]
            done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
            for task in pending:task.cancel()
            await asyncio.gather(*pending,return_exceptions=True)
            for task in done:
                try: task.result()
                except (WebSocketDisconnect,ConnectionClosed,RuntimeError):pass
    except (OSError,TimeoutError,ConnectionClosed,WebSocketDisconnect,RuntimeError):
        pass
    finally:
        try:
            await ws.close(code=1013 if accepted else 1011,
                           reason='Conexão com servidor da partida encerrada.')
        except (RuntimeError,OSError):
            pass
