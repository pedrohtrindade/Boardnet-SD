import unittest
from morris import Morris, ADJACENT, MILLS

class MorrisTest(unittest.TestCase):
    def test_initial_and_placement(self):
        g=Morris()
        self.assertEqual(g.public()['phase'],'placing')
        self.assertEqual(len(g.legal_moves()),24)
        g.play(None,0)
        self.assertEqual(g.placed['w'],1)
        self.assertEqual(g.turn,'b')
        with self.assertRaises(ValueError):g.play(None,0)

    def test_mill_capture_and_restrictions(self):
        g=Morris()
        for source,idx in [('w',0),('b',8),('w',1),('b',9)]:
            self.assertEqual(g.turn,source);g.play(None,idx)
        captures=[m for m in g.legal_moves() if m['to']==2]
        self.assertEqual({m['capture'] for m in captures},{8,9})
        with self.assertRaises(ValueError):g.play(None,2)
        g.play(None,2,8)
        self.assertEqual(g.board[8],'.')
        self.assertEqual(g.board[2],'w')

    def test_all_enemy_in_mills_can_capture(self):
        board=['.']*24
        for i in (0,1,2):board[i]='w'
        for i in (8,9,10):board[i]='b'
        g=Morris(board=board,placed={'w':3,'b':3})
        self.assertEqual(g.captures(g.board,'b'),[8,9,10])

    def test_adjacent_and_flying(self):
        self.assertIn(9,ADJACENT[1]);self.assertNotIn(8,ADJACENT[0])
        g=Morris(board=list('w...b.w....b....w...b...'),placed={'w':9,'b':9})
        self.assertEqual(g.phase('w'),'flying')
        self.assertTrue(any(m['from']==0 and m['to']==23 for m in g.legal_moves()))
        g.board[1]='w'
        self.assertEqual(g.phase('w'),'moving')
        self.assertFalse(any(m['from']==0 and m['to']==23 for m in g.legal_moves()))

    def test_win_by_less_than_three(self):
        board=['.']*24
        for i in (0,1,9):board[i]='w'
        for i in (3,4,10):board[i]='b'
        g=Morris(board=board,placed={'w':9,'b':9})
        self.assertEqual(g.phase('w'),'flying')
        self.assertIn({'from':9,'to':2,'capture':3},g.legal_moves())
        g.play(9,2,3)
        self.assertEqual(g.winner,'w')
        self.assertTrue(g.public()['game_over'])
        with self.assertRaises(ValueError):g.play(None,5)

    def test_win_by_blocking(self):
        board=['.']*24
        for i in (1,3,5,7,9):board[i]='w'
        for i in (0,2,4,6):board[i]='b'
        g=Morris(board=board,placed={'w':9,'b':9})
        self.assertIn({'from':9,'to':17,'capture':None},g.legal_moves())
        g.play(9,17)
        self.assertEqual(g.winner,'w')

    def test_mill_capture_prefer_unprotected(self):
        board=['.']*24
        for i in (0,1):board[i]='w'
        for i in (8,9,10,12):board[i]='b'
        g=Morris(board=board,placed={'w':8,'b':8})
        self.assertEqual({m['capture'] for m in g.legal_moves() if m['to']==2},{12})
        with self.assertRaises(ValueError):g.play(None,2,8)
        g.play(None,2,12)
        self.assertEqual(g.board[12],'.')

    def test_validation_and_no_mutation_on_invalid(self):
        g=Morris()
        before=g.public()
        for args in ((None,24,None),(None,0,3),(1,0,None),(None,True,None)):
            with self.assertRaises(ValueError):g.play(*args)
        self.assertEqual(g.public(),before)

    def test_persistence_data(self):
        g=Morris();g.play(None,0);g.play(None,8)
        obj=Morris(board=g.board.copy(),placed=g.placed.copy(),turn=g.turn,move_no=g.move_no,quiet_moves=g.quiet_moves)
        self.assertEqual(obj.public(),g.public())

if __name__=='__main__':unittest.main()
