"""BoardNet: salas distribuídas, dama, xadrez e trilha."""
import asyncio
import os
import secrets
import time
import string
from dataclasses import dataclass, field
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from checkers import Checkers
from chess_game import ChessGame
from morris import Morris
from storage import Store

app = FastAPI(title='BoardNet - Worker')
app.mount('/static', StaticFiles(directory=Path(__file__).resolve().parent / 'static'), name='static')
SERVER_ID = os.getenv('SERVER_ID', 'Servidor local')
STARTED_AT = time.monotonic()
BASE = Path(__file__).resolve().parent

class PlayerRequest(BaseModel):
    nickname: str = Field(min_length=1,max_length=24)
    game: str = 'checkers'

@dataclass
class Room:
    game: str = 'checkers'
    players: dict = field(default_factory=dict)
    connections: dict = field(default_factory=dict)
    game_state: object = field(default_factory=Checkers)

DATA_FILE = os.getenv('WORKER_DB', str(BASE / '.boardnet_data' / 'worker.sqlite3'))
store = Store(DATA_FILE)

def restore_rooms():
    recovered = {}
    for code, data in store.all().items():
        state=data['game_state']
        room=Room(game=data['game'],players=data['players'],game_state=(
            ChessGame(state['moves']) if data['game']=='chess' else
            Morris(board=state['board'],placed=state['placed'],turn=state['turn'],
                   winner=state['winner'],draw=state.get('draw',False),
                   move_no=state['move_no'],quiet_moves=state.get('quiet_moves',0)) if data['game']=='morris' else
            Checkers(board=state['board'],turn=state['turn'],winner=state['winner'],move_no=state['move_no'])))
        recovered[code]=room
    return recovered

rooms: dict[str,Room] = restore_rooms()

def persist_room(code, room):
    state=room.game_state
    store.put(code,{'game':room.game,'players':room.players,'game_state':(
        {'moves':state.moves} if room.game=='chess' else
        {'board':state.board,'placed':state.placed,'turn':state.turn,'winner':state.winner,
         'draw':state.draw,'move_no':state.move_no,'quiet_moves':state.quiet_moves} if room.game=='morris' else
        {'board':state.board,'turn':state.turn,'winner':state.winner,'move_no':state.move_no})})

lock=asyncio.Lock()

def public_room(code,room):
    return {'code':code,'game':room.game,'server':SERVER_ID,'players':[
        {'nickname':name,'side':'w' if i==0 else 'b','online':token in room.connections}
        for i,(token,name) in enumerate(room.players.items())],
        'ready':len(room.players)==2,'game_state':room.game_state.public()}

def make_code():
    while True:
        code=''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(6))
        if code not in rooms: return code

@app.get('/api/health')
async def health():
    # Não expõe tokens de jogadores nem conteúdo de partidas.
    async with lock:
        games = {kind: sum(r.game == kind for r in rooms.values()) for kind in ('checkers', 'chess', 'morris')}
        active_sockets = sum(len(r.connections) for r in rooms.values())
        active_rooms = sum(bool(r.connections) for r in rooms.values())
        return {'ok':True, 'server':SERVER_ID, 'rooms':len(rooms),
                'rooms_by_game':games, 'active_rooms':active_rooms,
                'connections':active_sockets, 'uptime_seconds':int(time.monotonic()-STARTED_AT)}

@app.get('/')
async def homepage(): return FileResponse(BASE/'static'/'index.html')

@app.post('/api/rooms')
async def create_room(data:PlayerRequest):
    if data.game not in ('checkers','chess','morris'): raise HTTPException(400,'Jogo indisponível.')
    if not data.nickname.strip(): raise HTTPException(400,'Informe um apelido.')
    async with lock:
        code,token=make_code(),secrets.token_urlsafe(24)
        room=Room(game=data.game,game_state=ChessGame() if data.game=='chess' else Morris() if data.game=='morris' else Checkers());room.players[token]=data.nickname.strip();rooms[code]=room
        persist_room(code,room)
        return {'code':code,'token':token,'side':'w','room':public_room(code,room)}

@app.post('/api/rooms/{code}/join')
async def join_room(code:str,data:PlayerRequest):
    code=code.strip().upper()
    if not data.nickname.strip(): raise HTTPException(400,'Informe um apelido.')
    async with lock:
        room=rooms.get(code)
        if not room: raise HTTPException(404,'Sala não encontrada.')
        if len(room.players)>=2: raise HTTPException(409,'Sala cheia.')
        if data.game!=room.game: raise HTTPException(400,'Jogo incorreto.')
        token=secrets.token_urlsafe(24);room.players[token]=data.nickname.strip()
        persist_room(code,room)
        response={'code':code,'token':token,'side':'b','room':public_room(code,room)}
    await broadcast(code)
    return response

@app.get('/api/rooms/{code}')
async def get_room(code:str):
    async with lock:
        room=rooms.get(code.upper())
        if not room: raise HTTPException(404,'Sala não encontrada.')
        return public_room(code.upper(),room)

async def broadcast(code):
    async with lock:
        room=rooms.get(code)
        if room is None:return
        payload={'type':'room_state','room':public_room(code,room)}
        connections=list(room.connections.items())
    for token,ws in connections:
        try: await ws.send_json(payload)
        except (RuntimeError,WebSocketDisconnect,OSError): pass

@app.websocket('/ws/{code}/{token}')
async def room_ws(ws:WebSocket,code:str,token:str):
    code=code.upper()
    async with lock:
        room=rooms.get(code)
        if not room or token not in room.players:
            await ws.close(code=1008);return
        # Replace a stale connection from this player, e.g. after browser refresh.
        previous=room.connections.get(token)
        await ws.accept()
        room.connections[token]=ws
    if previous:
        try:await previous.close(code=1000)
        except RuntimeError:pass
    await broadcast(code)
    try:
        while True:
            data=await ws.receive_json()
            if not isinstance(data,dict):continue
            typ=data.get('type')
            if typ=='ping':
                await ws.send_json({'type':'pong'})
            elif typ=='move':
                error=None
                async with lock:
                    room=rooms.get(code)
                    if room is None or room.connections.get(token) is not ws:
                        error='Sessão não está ativa.'
                    elif len(room.players)!=2:
                        error='Aguarde o segundo jogador.'
                    else:
                        player_index=list(room.players).index(token)
                        expected='w' if player_index==0 else 'b'
                        if room.game_state.public()['turn'] != expected:
                            error='Não é sua vez.'
                        else:
                            if room.game=='chess':
                                try:
                                    room.game_state.play(data.get('uci'))
                                    persist_room(code,room)
                                except ValueError as exc: error=str(exc)
                            elif room.game=='morris':
                                try:
                                    room.game_state.play(data.get('from'),data.get('to'),data.get('capture'))
                                    persist_room(code,room)
                                except ValueError as exc: error=str(exc)
                            else:
                                path=data.get('path')
                                if not isinstance(path,list) or len(path)<2 or len(path)>32 or any(
                                    not isinstance(p,list) or len(p)!=2 or any(type(x)!=int or not 0<=x<=7 for x in p) for p in path
                                ):
                                    error='Formato da jogada inválido.'
                                else:
                                    try:
                                        room.game_state.play(path)
                                        persist_room(code,room)
                                    except ValueError as exc:error=str(exc)
                if error:await ws.send_json({'type':'error','message':error})
                else:await broadcast(code)
            else:
                await ws.send_json({'type':'error','message':'Tipo de mensagem desconhecido.'})
    except (WebSocketDisconnect,RuntimeError,OSError): pass
    finally:
        async with lock:
            room=rooms.get(code)
            if room and room.connections.get(token) is ws:
                room.connections.pop(token,None)
        await broadcast(code)
