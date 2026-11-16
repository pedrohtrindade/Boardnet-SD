
let chessSelected=null, morrisSelected=null, morrisPending=null, gameChoice='checkers';
let reconnectTimer=null, heartbeatTimer=null, reconnectAttempts=0;
let socket=null, roomCode='', token='', mySide='', room=null, selected=null, prefix=[], generation=0;
const $=id=>document.getElementById(id);
function available(){if(!socket||socket.readyState!==WebSocket.OPEN||!room||!room.ready||room.game_state.winner||room.game_state.game_over)return[];const me=room.players.find(p=>p.side===mySide);return me&&me.side===room.game_state.turn?room.game_state.legal_moves:[];}
function eq(a,b){return a[0]===b[0]&&a[1]===b[1]}
function starts(path,prefix){return prefix.every((p,i)=>eq(p,path[i]))}
function allowed(){return available().filter(m=>starts(m.path,prefix))}
// A ordem de exibição muda, mas as coordenadas do servidor continuam intactas.
function orientationFor(side){return side==='b'?'black':'white';}
function visualToLogical(vr,vc,side){return side==='b'?[7-vr,7-vc]:[vr,vc];}
function boardCoordinates(r,c,side){
 const showFile=(side==='b'?c===7:c===0);
 const showRank=(side==='b'?r===0:r===7);
 return {file:showRank?'abcdefgh'[c]:'',rank:showFile?String(8-r):''};
}
function addCoordinates(square,r,c){
 const marks=boardCoordinates(r,c,mySide);
 if(marks.rank){const n=document.createElement('span');n.className='coordinate rank';n.textContent=marks.rank;square.append(n);}
 if(marks.file){const n=document.createElement('span');n.className='coordinate file';n.textContent=marks.file;square.append(n);}
}
function boardPosition(vr,vc){return visualToLogical(vr,vc,mySide);}
function displayName(side){return side==='w'?'Brancas':'Pretas';}
function playerRow(player,side){
 const item=document.createElement('div');item.className='player';
 const avatar=document.createElement('span');avatar.className='player-token '+(side==='w'?'token-white':'token-black');avatar.setAttribute('aria-hidden','true');
 const details=document.createElement('div');details.className='player-details';
 const label=document.createElement('strong');label.textContent=player?.nickname||'Aguardando jogador';
 const meta=document.createElement('span');meta.className='muted small';meta.textContent=displayName(side)+(side===mySide?' · você':'');
 details.append(label,meta);
 const presence=document.createElement('span');presence.className='presence '+(player?.online?'is-online':'');presence.textContent=player?(player.online?'Online':'Offline'):'Pendente';
 item.append(avatar,details,presence);return item;
}
function updatePlayers(){
 if(!room)return;
 const local=room.players.find(p=>p.side===mySide),remote=room.players.find(p=>p.side!==(mySide==='b'?'b':'w'));
 const localSide=mySide==='b'?'b':'w';
 $('player-top').replaceChildren(playerRow(remote,localSide==='w'?'b':'w'));
 $('player-bottom').replaceChildren(playerRow(local,localSide));
}
function drawBoard(){if(room?.game==='chess'){$('board').className='board';drawChess();return;}if(room?.game==='morris'){drawMorris();return;}const board=$('board');board.className='board';board.replaceChildren();if(!room)return;const state=room.game_state;let moves=allowed();const targets=prefix.length?moves.filter(m=>m.path.length>prefix.length).map(m=>m.path[prefix.length]):selected?available().filter(m=>eq(m.path[0],selected)).map(m=>m.path[1]):[];const highlight=prefix.length?prefix[prefix.length-1]:selected;
for(let vr=0;vr<8;vr++)for(let vc=0;vc<8;vc++){const [r,c]=boardPosition(vr,vc);const el=document.createElement('button');el.className='sq '+((r+c)%2?'dark':'light');el.type='button';el.setAttribute('aria-label',`Casa ${squareName(r,c)}`);addCoordinates(el,r,c);if(highlight&&eq(highlight,[r,c]))el.classList.add('selected');if(targets.some(p=>eq(p,[r,c])))el.classList.add('target');const p=state.board[r][c];if(p!=='.'){const piece=document.createElement('div');piece.className='piece '+(p.toLowerCase()==='w'?'whitepiece':'blackpiece');if(p===p.toUpperCase()){piece.classList.add('king');piece.textContent='♛'}el.appendChild(piece);}el.addEventListener('click',()=>clickSquare(r,c));board.appendChild(el);}}
function clickSquare(r,c){if(room?.game==='chess'){clickChess(r,c);return;}if(!room)return;const moves=available();if(!moves.length){showMsg('Aguarde sua vez ou o outro jogador.');return;}const at=[r,c];if(prefix.length){const next=allowed().filter(m=>m.path.length>prefix.length&&eq(m.path[prefix.length],at));if(next.length){prefix=[...prefix,at];selected=prefix[0];const completed=next.filter(m=>m.path.length===prefix.length);const continuing=next.filter(m=>m.path.length>prefix.length);if(completed.length&&!continuing.length){const path=prefix;prefix=[];selected=null;sendMove({type:'move',path});showMsg('Jogada enviada. Aguardando confirmação...');}else showMsg('Continue a sequência obrigatória de captura.');drawBoard();return;}prefix=[];selected=null;showMsg('Sequência cancelada. Selecione novamente.');}
const chosen=moves.filter(m=>eq(m.path[0],at));if(chosen.length){selected=at;prefix=[at];showMsg('Selecione a casa destacada para mover.');drawBoard();return;}showMsg('Escolha uma peça sua que tenha jogadas legais.');drawBoard();}
function renderRoom(data){
 const previousMove=room?.game_state.move_no;
 room=data;updatePlayers();
 $('workername').textContent='Servidor: '+(room.server||'Não identificado');
 const g=room.game_state,me=room.players.find(p=>p.side===mySide),myTurn=me?.side===g.turn;
 $('status').textContent=g.draw?'Empate':g.winner?`Vitória das ${g.winner==='w'?'brancas':'pretas'}`:room.ready?(myTurn?'Sua vez de jogar':`Vez das ${g.turn==='w'?'brancas':'pretas'}`):'Aguardando adversário';
 $('turn-indicator').classList.toggle('my-turn',Boolean(room.ready&&myTurn&&!g.winner&&!g.draw));
 $('moveinfo').textContent=`${g.move_no} jogadas · ${me?'Você: '+displayName(me.side):'Participante'}${room.game==='morris'?` · ${ {placing:'Colocação',moving:'Movimentação',flying:'Voo'}[g.phase]}`:''}`;
 $('details').textContent=room.game==='morris'?`Por colocar: ${g.remaining.w} brancas / ${g.remaining.b} pretas · Em jogo: ${g.on_board.w} brancas / ${g.on_board.b} pretas`:'';
 if(previousMove!==undefined&&previousMove!==g.move_no){prefix=[];selected=null;chessSelected=null;morrisSelected=null;morrisPending=null;showMsg(g.winner?'Partida encerrada.':'Tabuleiro atualizado.');}
 if(!room.ready){prefix=[];selected=null;}
 $('gametitle').textContent=room.game==='chess'?'Xadrez':room.game==='morris'?'Trilha':'Dama brasileira';
 $('rules').textContent=room.game==='chess'?'Xeque, xeque-mate, roque, en passant e promoção. Selecione a peça e a casa de destino.':room.game==='morris'?'Coloque nove peças, forme trilhas de três e capture peças adversárias. Depois, movimente pelas linhas. Com três peças, você pode voar.':'Capturas são obrigatórias e seguem a lei da maioria. Damas percorrem várias casas diagonais.';
 $('orientation').textContent=room.game==='morris'?'Tabuleiro fixo':`Perspectiva: ${displayName(mySide)}`;
 drawBoard();
}
const chessGlyph={K:'♔',Q:'♕',R:'♖',B:'♗',N:'♘',P:'♙',k:'♚',q:'♛',r:'♜',b:'♝',n:'♞',p:'♟'};
function chessSquares(fen){const rows=fen.split(' ')[0].split('/');return rows.map(row=>{const out=[];for(const k of row){if(/[1-8]/.test(k))for(let j=0;j<Number(k);j++)out.push('.');else out.push(k);}return out;});}
function squareName(r,c){return 'abcdefgh'[c]+(8-r);}
function drawChess(){const el=$('board');el.replaceChildren();if(!room)return;const g=room.game_state,b=chessSquares(g.fen),moves=available();const candidates=chessSelected?moves.filter(m=>m.slice(0,2)===chessSelected):[];
for(let vr=0;vr<8;vr++)for(let vc=0;vc<8;vc++){const [r,c]=boardPosition(vr,vc);const sq=document.createElement('button');sq.type='button';sq.className='sq '+((r+c)%2?'dark':'light');const id=squareName(r,c);sq.setAttribute('aria-label',`Casa ${id}`);addCoordinates(sq,r,c);if(id===chessSelected)sq.classList.add('selected');if(candidates.some(m=>m.slice(2,4)===id))sq.classList.add('target');const pc=b[r][c];if(pc!=='.'){const piece=document.createElement('span');piece.textContent=chessGlyph[pc];piece.className='chess-piece '+(pc===pc.toUpperCase()?'white':'black');sq.append(piece);}sq.addEventListener('click',()=>clickChess(r,c));el.append(sq);}}
function clickChess(r,c){if(!room)return;const possible=available(),id=squareName(r,c);if(!possible.length){showMsg('Aguarde sua vez ou a partida terminar.');return;}if(chessSelected){const candidates=possible.filter(m=>m.slice(0,2)===chessSelected&&m.slice(2,4)===id);if(candidates.length){let chosen=candidates[0];if(candidates.length>1){const selection=prompt('Promover para: q = dama, r = torre, b = bispo, n = cavalo','q');if(selection===null)return;chosen=candidates.find(m=>m.endsWith(selection.trim().toLowerCase()));if(!chosen){showMsg('Peça de promoção inválida.');return;}}chessSelected=null;sendMove({type:'move',uci:chosen});showMsg('Movimento enviado para validação.');drawChess();return;}}
if(possible.some(m=>m.slice(0,2)===id)){chessSelected=id;showMsg('Escolha uma casa destacada.');}else{chessSelected=null;showMsg('Selecione uma peça sua com jogadas legais.');}drawChess();}
// Coordenadas de 24 interseções, percorrendo cada anel em sentido horário.
const morrisCoords=[[8,8],[50,8],[92,8],[92,50],[92,92],[50,92],[8,92],[8,50],
[22,22],[50,22],[78,22],[78,50],[78,78],[50,78],[22,78],[22,50],
[36,36],[50,36],[64,36],[64,50],[64,64],[50,64],[36,64],[36,50]];
function morrisAllowed(){return room?.game==='morris'?available():[];}
function drawMorris(){
 const container=$('board');container.className='morris-board';container.replaceChildren();if(!room)return;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 100 100');svg.setAttribute('class','morris-lines');
 const lines=[];
 for(const ring of [0,1,2]){
  const indices=[0,1,2,3,4,5,6,7,0];for(let k=0;k<8;k++)lines.push([ring*8+indices[k],ring*8+indices[k+1]]);
 }
 for(const i of [1,3,5,7]){lines.push([i,8+i],[8+i,16+i]);}
 for(const [a,b] of lines){const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',morrisCoords[a][0]);line.setAttribute('y1',morrisCoords[a][1]);line.setAttribute('x2',morrisCoords[b][0]);line.setAttribute('y2',morrisCoords[b][1]);line.setAttribute('stroke','#745033');line.setAttribute('stroke-width','1.3');svg.append(line);}container.append(svg);
 const moves=morrisAllowed();const pending=morrisPending;
 const targets=pending?pending.choices:room.game_state.phase==='placing'?moves.map(m=>m.to):morrisSelected!==null?moves.filter(m=>m.from===morrisSelected).map(m=>m.to):[];
 morrisCoords.forEach(([x,y],i)=>{const point=document.createElement('button');point.type='button';point.className='morris-point';point.style.left=x+'%';point.style.top=y+'%';point.title='Ponto '+i;
 const pc=room.game_state.board[i];point.setAttribute('aria-label',`Ponto ${i+1}: ${pc==='.'?'vazio':pc==='w'?'branca':'preta'}`);
 if(morrisSelected===i)point.classList.add('selected');if(targets.includes(i))point.classList.add(pending?'capture':'target');
 if(pc!=='.'){const piece=document.createElement('span');piece.className='morris-piece '+pc;point.append(piece);}
 point.addEventListener('click',()=>clickMorris(i));container.append(point);
 });
}
function clickMorris(i){
 const moves=morrisAllowed();if(!moves.length){showMsg('Aguarde sua vez ou a partida terminar.');return;}
 if(morrisPending){const match=morrisPending.moves.find(m=>m.capture===i);if(match){sendMove({type:'move',from:match.from,to:match.to,capture:match.capture});morrisPending=null;morrisSelected=null;showMsg('Trilha formada! Captura enviada.');drawMorris();}else showMsg('Escolha uma peça adversária marcada em vermelho para capturar.');return;}
 const state=room.game_state;
 if(state.phase!=='placing'&&state.board[i]===mySide){morrisSelected=i;showMsg('Selecione uma posição livre destacada.');drawMorris();return;}
 const candidates=moves.filter(m=>m.from===(state.phase==='placing'?null:morrisSelected)&&m.to===i);
 if(candidates.length){
  if(candidates.some(m=>m.capture!==null)){
   morrisPending={moves:candidates,choices:candidates.filter(m=>m.capture!==null).map(m=>m.capture)};
   showMsg('Você formou uma trilha! Clique na peça adversária marcada em vermelho para capturar.');drawMorris();return;
  }
  sendMove({type:'move',from:candidates[0].from,to:i,capture:null});morrisSelected=null;showMsg('Jogada enviada. Aguardando confirmação...');drawMorris();return;
 }
 showMsg(state.phase==='placing'?'Clique num ponto livre para colocar sua peça.':'Selecione uma peça sua e um destino permitido.');
}
function showMsg(text){$('message').textContent=text;}
async function api(url,body){const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const json=await res.json();if(!res.ok)throw Error(json.detail||'Erro na requisição.');return json;}
function enter(data){roomCode=data.code;token=data.token;mySide=data.side;gameChoice=data.room.game;chessSelected=null;morrisSelected=null;morrisPending=null;sessionStorage.setItem('boardnet-room',JSON.stringify({code:roomCode,token,side:mySide}));$('roomcode').textContent=roomCode;$('home').classList.add('hidden');$('game').classList.remove('hidden');renderRoom(data.room);connect();}
async function createRoom(){try{$('homeError').textContent='';enter(await api('/api/rooms',{nickname:$('nickname').value,game:$('gamechoice').value}));}catch(e){$('homeError').textContent=e.message;}}
async function joinRoom(){try{$('homeError').textContent='';const code=$('roominput').value.trim().toUpperCase();if(!code)throw Error('Informe o código da sala.');enter(await api(`/api/rooms/${encodeURIComponent(code)}/join`,{nickname:$('nickname').value,game:$('gamechoice').value}));}catch(e){$('homeError').textContent=e.message;}}
function sendMove(payload){
 if(!socket||socket.readyState!==WebSocket.OPEN){showMsg('Conexão indisponível. Aguarde a reconexão.');return false;}
 socket.send(JSON.stringify(payload));return true;
}
function stopConnectionTimers(){
 if(reconnectTimer!==null){clearTimeout(reconnectTimer);reconnectTimer=null;}
 if(heartbeatTimer!==null){clearInterval(heartbeatTimer);heartbeatTimer=null;}
}
function retryConnection(){if(!roomCode||!token)return;stopConnectionTimers();connect();}
function connect(){
 if(!roomCode||!token)return;
 stopConnectionTimers();const current=++generation;
 if(socket){socket.onclose=null;socket.close();}
 const protocol=location.protocol==='https:'?'wss':'ws';
 $('connection').textContent='🟡 Conectando ao servidor da partida...';
 $('reconnect').classList.add('hidden');
 const ws=new WebSocket(`${protocol}://${location.host}/ws/${roomCode}/${encodeURIComponent(token)}`);
 socket=ws;
 ws.onopen=()=>{
  if(current!==generation)return;
  reconnectAttempts=0;
  $('connection').textContent='🟢 WebSocket conectado';
  $('reconnect').classList.add('hidden');
  heartbeatTimer=setInterval(()=>{
   if(socket===ws&&ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify({type:'ping'}));
  },15000);
 };
 ws.onmessage=e=>{
  if(current!==generation)return;
  let data;try{data=JSON.parse(e.data);}catch{return;}
  if(data.type==='room_state')renderRoom(data.room);
  if(data.type==='error')showMsg('⚠ '+data.message);
 };
 ws.onclose=()=>{
  if(current!==generation)return;
  stopConnectionTimers();socket=null;
  selected=null;prefix=[];chessSelected=null;morrisSelected=null;morrisPending=null;
  drawBoard();
  const delay=Math.min(15000,1000*2**Math.min(reconnectAttempts,4));
  reconnectAttempts++;
  $('connection').textContent=`🔴 Conexão perdida. Reconectando em ${Math.ceil(delay/1000)}s...`;
  $('reconnect').classList.remove('hidden');
  reconnectTimer=setTimeout(()=>{reconnectTimer=null;if(current===generation&&roomCode)connect();},delay);
 };
 ws.onerror=()=>{if(current===generation)$('connection').textContent='⚠ Erro de conexão com o servidor.';};
}

function copyCode(){if(navigator.clipboard?.writeText)navigator.clipboard.writeText(roomCode).then(()=>showMsg('Código copiado!')).catch(()=>showMsg('Copie o código exibido acima.'));else showMsg('Copie o código exibido acima.');}
function goHome(){generation++;stopConnectionTimers();reconnectAttempts=0;if(socket){socket.onclose=null;socket.close();socket=null;}room=null;prefix=[];selected=null;chessSelected=null;morrisSelected=null;morrisPending=null;sessionStorage.removeItem('boardnet-room');$('home').classList.remove('hidden');$('game').classList.add('hidden');}
async function loadCluster(){try{const r=await fetch('/api/cluster');if(!r.ok)return;const data=await r.json();$('clusterstatus').textContent='Cluster '+(data.status==='online'?'operacional':data.status==='degraded'?'degradado':'indisponível')+' | '+data.workers.map(w=>w.server+': '+(w.online?'online ('+w.rooms+' salas, '+w.connections+' conexões)':'offline')).join(' | ');}catch(e){$('clusterstatus').textContent='Status indisponível';}}loadCluster();setInterval(loadCluster,5000);
(async()=>{const saved=sessionStorage.getItem('boardnet-room');if(!saved)return;try{const s=JSON.parse(saved);const response=await fetch(`/api/rooms/${encodeURIComponent(s.code)}`);if(!response.ok)throw Error();enter({code:s.code,token:s.token,side:s.side,room:await response.json()});}catch(e){sessionStorage.removeItem('boardnet-room');}})();

for(const tile of document.querySelectorAll('[data-game]')){
 tile.addEventListener('click',()=>{
  $('gamechoice').value=tile.dataset.game;
  for(const t of document.querySelectorAll('[data-game]')){const active=t===tile;t.classList.toggle('is-selected',active);t.setAttribute('aria-pressed',String(active));}
 });
}
$('gamechoice').addEventListener('change',()=>{
 for(const tile of document.querySelectorAll('[data-game]')){const active=tile.dataset.game===$('gamechoice').value;tile.classList.toggle('is-selected',active);tile.setAttribute('aria-pressed',String(active));}
});
