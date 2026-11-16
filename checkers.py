"""Motor autoritativo de damas brasileiras 8x8. Coordenadas: [linha, coluna]."""
from dataclasses import dataclass

DIAGONALS = ((-1,-1),(-1,1),(1,-1),(1,1))


def inside(r,c): return 0 <= r < 8 and 0 <= c < 8


def initial_board():
    return [[('b' if r < 3 else 'w') if (r+c)%2 and (r < 3 or r > 4) else '.' for c in range(8)] for r in range(8)]


def color(piece): return piece.lower() if piece != '.' else None


def captures_from(board, start):
    """Retorna sequências completas. As peças capturadas BLOQUEIAM até o fim do lance."""
    r,c = start
    piece = board[r][c]
    if piece == '.': return []
    enemy = 'w' if color(piece) == 'b' else 'b'
    result = []

    def walk(pos, path, removed):
        row,col = pos
        possibilities = []
        for dr,dc in DIAGONALS:
            if piece.isupper():
                rr,cc = row+dr,col+dc
                while inside(rr,cc) and board[rr][cc] == '.':
                    rr += dr; cc += dc
                if not inside(rr,cc) or color(board[rr][cc]) != enemy or (rr,cc) in removed:
                    continue
                victim=(rr,cc)
                rr += dr; cc += dc
                while inside(rr,cc) and board[rr][cc] == '.':
                    possibilities.append(((rr,cc),victim))
                    rr += dr;cc += dc
            else:
                rr,cc = row+dr,col+dc
                land=(row+2*dr,col+2*dc)
                if inside(*land) and color(board[rr][cc]) == enemy and (rr,cc) not in removed and board[land[0]][land[1]] == '.':
                    possibilities.append((land,(rr,cc)))
        if not possibilities:
            if removed: result.append({'path':[list(x) for x in path], 'captures':[list(x) for x in removed]})
            return
        for dest,victim in possibilities:
            # The moving piece leaves its current square; captured pieces remain physically present.
            prev = board[row][col]
            board[row][col]='.'
            board[dest[0]][dest[1]]=prev
            walk(dest,path+[dest],removed+[victim])
            board[dest[0]][dest[1]]='.'
            board[row][col]=prev
    walk(start,[start],[])
    return result


def legal_moves(board, turn):
    captures=[]
    moves=[]
    for r in range(8):
        for c in range(8):
            piece=board[r][c]
            if color(piece)!=turn: continue
            captures.extend(captures_from(board,(r,c)))
            if piece.isupper():
                for dr,dc in DIAGONALS:
                    rr,cc=r+dr,c+dc
                    while inside(rr,cc) and board[rr][cc]=='.':
                        moves.append({'path':[[r,c],[rr,cc]],'captures':[]})
                        rr+=dr;cc+=dc
            else:
                dr=-1 if turn=='w' else 1
                for dc in (-1,1):
                    rr,cc=r+dr,c+dc
                    if inside(rr,cc) and board[rr][cc]=='.':
                        moves.append({'path':[[r,c],[rr,cc]],'captures':[]})
    if captures:
        maximum=max(len(m['captures']) for m in captures)
        return [m for m in captures if len(m['captures'])==maximum]
    return moves


@dataclass
class Checkers:
    board: list = None
    turn: str = 'w'
    winner: str | None = None
    move_no: int = 0

    def __post_init__(self):
        if self.board is None: self.board=initial_board()

    def public(self):
        moves=[] if self.winner else legal_moves(self.board,self.turn)
        return {'board':self.board,'turn':self.turn,'winner':self.winner,'move_no':self.move_no,'legal_moves':moves,'status':'finished' if self.winner else 'playing'}

    def play(self,path):
        if self.winner: raise ValueError('A partida já terminou.')
        moves=legal_moves(self.board,self.turn)
        move=next((m for m in moves if m['path']==path),None)
        if move is None: raise ValueError('Jogada inválida: respeite a captura obrigatória e a lei da maioria.')
        start,end=path[0],path[-1]
        piece=self.board[start[0]][start[1]]
        self.board[start[0]][start[1]]='.'
        for r,c in move['captures']: self.board[r][c]='.'
        if piece=='w' and end[0]==0: piece='W'
        if piece=='b' and end[0]==7: piece='B'
        self.board[end[0]][end[1]]=piece
        self.turn='b' if self.turn=='w' else 'w'
        self.move_no+=1
        if not legal_moves(self.board,self.turn):
            self.winner='w' if self.turn=='b' else 'b'
        return move
