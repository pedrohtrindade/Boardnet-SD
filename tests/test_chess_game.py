import unittest
from chess_game import ChessGame

class ChessGameTests(unittest.TestCase):
    def test_initial_position_and_moves(self):
        g=ChessGame();s=g.public()
        self.assertEqual(s['turn'],'w')
        self.assertEqual(len(s['legal_moves']),20)
    def test_illegal_move(self):
        with self.assertRaises(ValueError): ChessGame().play('e2e5')
    def test_scholars_mate(self):
        g=ChessGame()
        for uci in ('e2e4','e7e5','d1h5','b8c6','f1c4','g8f6','h5f7'):g.play(uci)
        self.assertTrue(g.public()['game_over'])
        self.assertEqual(g.public()['winner'],'w')
    def test_persistence_from_uci(self):
        g=ChessGame()
        for m in ('e2e4','e7e5','g1f3'):g.play(m)
        restored=ChessGame(g.moves)
        self.assertEqual(restored.public()['fen'],g.public()['fen'])
    def test_castling(self):
        g=ChessGame()
        for m in ('e2e4','e7e5','g1f3','b8c6','f1e2','g8f6','e1g1'):g.play(m)
        self.assertEqual(g.board.piece_at(__import__('chess').G1).symbol(),'K')
