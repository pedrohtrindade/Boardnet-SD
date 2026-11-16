import unittest
from checkers import Checkers, initial_board, legal_moves

def empty():return [['.']*8 for _ in range(8)]

class TestCheckers(unittest.TestCase):
    def test_start(self):
        g=Checkers();self.assertEqual(sum(p=='w' for row in g.board for p in row),12)
        self.assertEqual(sum(p=='b' for row in g.board for p in row),12)
        self.assertEqual(len(legal_moves(g.board,'w')),7)
    def test_turn_and_move(self):
        g=Checkers();g.play([[5,0],[4,1]])
        self.assertEqual(g.turn,'b')
        self.assertEqual(g.board[4][1],'w')
        with self.assertRaises(ValueError):g.play([[5,2],[4,3]])
    def test_forced_capture_backward(self):
        b=empty();b[3][2]='w';b[4][3]='b';b[5][4]='.';b[5][0]='w'
        moves=legal_moves(b,'w')
        self.assertEqual([m['path'] for m in moves],[[[3,2],[5,4]]])
        g=Checkers(board=b);g.play([[3,2],[5,4]]);self.assertEqual(b[4][3],'.')
    def test_majority_and_chain(self):
        b=empty();b[5][0]='w';b[4][1]='b';b[2][3]='b';b[4][5]='b';b[5][6]='w'
        moves=legal_moves(b,'w')
        self.assertEqual(max(len(m['captures']) for m in moves),2)
        self.assertTrue(all(len(m['captures'])==2 for m in moves))
        self.assertEqual(moves[0]['path'],[[5,0],[3,2],[1,4]])
    def test_king_flying(self):
        b=empty();b[6][1]='W';b[3][4]='b'
        moves=legal_moves(b,'w');self.assertEqual({tuple(m['path'][-1]) for m in moves},{(2,5),(1,6),(0,7)})
    def test_promote(self):
        b=empty();b[1][2]='w';b[7][6]='b'
        g=Checkers(board=b);g.play([[1,2],[0,1]]);self.assertEqual(g.board[0][1],'W')
    def test_captured_piece_blocks_king_recapture(self):
        b=empty();b[5][0]='W';b[4][1]='b';b[2][3]='b'
        moves=legal_moves(b,'w')
        self.assertTrue(all(len(set(map(tuple,m['captures'])))==len(m['captures']) for m in moves))

if __name__=='__main__':unittest.main()
