"""Run from the project root; uses no answer constants for the question proof.

The fixture stores both the literal source wording and its geometric translation.
Any wording edit fails the binding check so a reviewer must reconsider coordinates.
"""
import json
from pathlib import Path
import unittest

from cube_net_helpers import fold_cube_net, free_polyominoes

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / 'fixtures/cube_net.json').read_text())
QUESTIONS = json.loads((HERE.parent / 'data/questions.json').read_text())


class CubeNetFixtureTests(unittest.TestCase):
    def test_reject_invalid_size_disconnection_and_overlaps(self):
        for cells in ([(0, 0)], [(x, 0) for x in range(6)],
                      [(x, 0) for x in range(5)] + [(10, 10)]):
            self.assertFalse(fold_cube_net(cells)['folds'])

    def test_source_binding_and_computed_answer(self):
        q = next(q for q in QUESTIONS if q['id'] == FIXTURE['id'])
        self.assertEqual(q['prompt'], FIXTURE['source_prompt'])
        self.assertEqual(q['type'], 'choice')
        self.assertEqual({c['key']: c['text'] for c in q['choices']},
                         {key: item['source_text'] for key, item in FIXTURE['choices'].items()})
        self.assertEqual(FIXTURE['predicate'], 'cannot_fold_to_cube')
        invalid = []
        for key, item in FIXTURE['choices'].items():
            states = {fold_cube_net(case['cells'])['folds'] for case in item['cases']}
            self.assertEqual(len(states), 1, 'The wording permits inconsistent foldability: ' + key)
            if states == {False}:
                invalid.append(key)
        self.assertEqual(invalid, [q['answer']])

    def test_d_attachment_covers_exact_cartesian_product(self):
        cases = FIXTURE['choices']['D']['cases']
        self.assertEqual(len(cases), 16)
        self.assertEqual({(case['upper_column'], case['lower_column']) for case in cases},
                         {(u, l) for u in range(4) for l in range(4)})
        for case in cases:
            self.assertEqual(set(map(tuple, case['cells'])),
                             {(x, 0) for x in range(4)} |
                             {(case['upper_column'], -1), (case['lower_column'], 1)})

    def test_free_hexominoes_and_geometric_invariance(self):
        shapes = free_polyominoes(6)
        self.assertEqual(len(shapes), 35)
        self.assertEqual(sum(fold_cube_net(s)['folds'] for s in shapes), 11)
        for cells in shapes:
            expected = fold_cube_net(cells)['folds']
            for swap in (False, True):
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        transformed = [(sx*(y if swap else x)+13,
                                        sy*(x if swap else y)-9) for x, y in cells]
                        self.assertEqual(fold_cube_net(transformed)['folds'], expected)


if __name__ == '__main__':
    unittest.main()
