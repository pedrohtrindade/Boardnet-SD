"""Trilha (Nine Men's Morris), motor autoritativo e serializável.

Índices por anel (externo, intermediário, interno), em sentido horário:
0 topo-esquerda, 1 topo-meio, 2 topo-direita, 3 direita-meio,
4 baixo-direita, 5 baixo-meio, 6 baixo-esquerda, 7 esquerda-meio.
"""
from dataclasses import dataclass, field

MILLS = tuple(
    tuple(r * 8 + i for i in indices)
    for r in range(3)
    for indices in ((0, 1, 2), (2, 3, 4), (4, 5, 6), (6, 7, 0))
) + tuple((i, 8 + i, 16 + i) for i in (1, 3, 5, 7))

ADJACENT = tuple(
    tuple(sorted({ring * 8 + (pos - 1) % 8, ring * 8 + (pos + 1) % 8} |
                 ({(ring - 1) * 8 + pos} if pos % 2 and ring > 0 else set()) |
                 ({(ring + 1) * 8 + pos} if pos % 2 and ring < 2 else set())))
    for ring in range(3) for pos in range(8)
)


@dataclass
class Morris:
    board: list = field(default_factory=lambda: ['.'] * 24)
    placed: dict = field(default_factory=lambda: {'w': 0, 'b': 0})
    turn: str = 'w'
    winner: str | None = None
    draw: bool = False
    move_no: int = 0
    quiet_moves: int = 0

    def __post_init__(self):
        if len(self.board) != 24 or any(p not in ('.', 'w', 'b') for p in self.board):
            raise ValueError('Tabuleiro de trilha inválido.')
        if set(self.placed) != {'w', 'b'} or any(type(n) is not int or n < 0 or n > 9 for n in self.placed.values()):
            raise ValueError('Contadores de peças inválidos.')
        if self.turn not in ('w', 'b') or self.winner not in (None, 'w', 'b') or type(self.draw) is not bool:
            raise ValueError('Estado da trilha inválido.')
        if type(self.move_no) is not int or self.move_no < 0 or type(self.quiet_moves) is not int or self.quiet_moves < 0:
            raise ValueError('Contadores da trilha inválidos.')
        for side in ('w', 'b'):
            if self.board.count(side) > self.placed[side]:
                raise ValueError('Mais peças no tabuleiro que peças colocadas.')

    def mill(self, i, side=None, board=None):
        board = self.board if board is None else board
        side = board[i] if side is None else side
        return side != '.' and any(i in triple and all(board[p] == side for p in triple) for triple in MILLS)

    def captures(self, board, enemy):
        occupied = [i for i, p in enumerate(board) if p == enemy]
        outside = [i for i in occupied if not self.mill(i, enemy, board)]
        return outside or occupied

    def phase(self, side):
        if self.placed[side] < 9:
            return 'placing'
        if self.board.count(side) == 3:
            return 'flying'
        return 'moving'

    def legal_moves(self):
        if self.winner or self.draw:
            return []
        side = self.turn
        enemy = 'b' if side == 'w' else 'w'
        empty = [i for i, p in enumerate(self.board) if p == '.']
        phase = self.phase(side)
        if phase == 'placing':
            options = [(None, dst) for dst in empty]
        else:
            options = [(src, dst) for src, p in enumerate(self.board) if p == side
                       for dst in (empty if phase == 'flying' else ADJACENT[src]) if self.board[dst] == '.']
        legal = []
        for src, dst in options:
            simulated = self.board.copy()
            if src is not None:
                simulated[src] = '.'
            simulated[dst] = side
            formed = self.mill(dst, side, simulated) and not (src is not None and self.mill(dst, side))
            # Capturing is only required on *forming* a mill with a new move.
            if formed and enemy in simulated:
                for captured in self.captures(simulated, enemy):
                    legal.append({'from': src, 'to': dst, 'capture': captured})
            else:
                legal.append({'from': src, 'to': dst, 'capture': None})
        return legal

    def play(self, source, target, capture=None):
        if type(target) is not int or not 0 <= target < 24:
            raise ValueError('Destino inválido.')
        if source is not None and (type(source) is not int or not 0 <= source < 24):
            raise ValueError('Origem inválida.')
        if capture is not None and (type(capture) is not int or not 0 <= capture < 24):
            raise ValueError('Captura inválida.')
        move = {'from': source, 'to': target, 'capture': capture}
        if move not in self.legal_moves():
            raise ValueError('Jogada não permitida pelas regras da trilha.')
        side, enemy = self.turn, 'b' if self.turn == 'w' else 'w'
        if source is None:
            self.placed[side] += 1
        else:
            self.board[source] = '.'
        self.board[target] = side
        if capture is not None:
            self.board[capture] = '.'
        self.move_no += 1
        self.quiet_moves = 0 if capture is not None or source is None else self.quiet_moves + 1
        self.turn = enemy
        if all(n == 9 for n in self.placed.values()):
            if self.board.count(enemy) < 3 or not self.legal_moves():
                self.winner = side
            elif self.quiet_moves >= 100:
                self.draw = True

    def public(self):
        return {
            'board': self.board.copy(), 'turn': self.turn, 'winner': self.winner,
            'draw': self.draw, 'game_over': bool(self.winner or self.draw),
            'move_no': self.move_no, 'placed': self.placed.copy(),
            'remaining': {s: 9 - self.placed[s] for s in ('w', 'b')},
            'on_board': {s: self.board.count(s) for s in ('w', 'b')},
            'phase': self.phase(self.turn), 'legal_moves': self.legal_moves(),
        }
