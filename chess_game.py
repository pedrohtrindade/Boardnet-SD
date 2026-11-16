"""Xadrez autoritativo com python-chess. Persistência por FEN e histórico UCI."""
import chess

class ChessGame:
    def __init__(self, moves=None):
        self.board = chess.Board()
        self.moves = list(moves or [])
        for uci in self.moves:
            move = chess.Move.from_uci(uci)
            if move not in self.board.legal_moves:
                raise ValueError("Histórico de xadrez inválido.")
            self.board.push(move)

    def play(self, uci):
        if not isinstance(uci,str) or len(uci) not in (4,5):
            raise ValueError("Formato de movimento inválido.")
        if self.board.is_game_over(claim_draw=True):
            raise ValueError("A partida terminou.")
        try: move = chess.Move.from_uci(uci)
        except ValueError: raise ValueError("Movimento inválido.")
        if move not in self.board.legal_moves:
            raise ValueError("Movimento não permitido pelas regras do xadrez.")
        self.board.push(move)
        self.moves.append(uci)

    def public(self):
        result = self.board.outcome(claim_draw=True)
        winner = ('w' if result.winner else 'b') if result and result.winner is not None else None
        return {'fen':self.board.fen(), 'turn':'w' if self.board.turn else 'b',
                'winner':winner, 'draw':bool(result and result.winner is None),
                'game_over':result is not None,
                'termination':result.termination.name if result else None,
                'check':self.board.is_check(),
                'move_no':len(self.moves),
                'last_move':self.moves[-1] if self.moves else None,
                'legal_moves':[m.uci() for m in self.board.legal_moves] if not result else []}
