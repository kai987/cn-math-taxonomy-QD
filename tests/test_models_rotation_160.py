import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from models_rotation_160 import right_angle_construction


class RotationConstructionTests(unittest.TestCase):
    def setUp(self):
        self.spec = {'angle_degrees': 90, 'direction': 'counterclockwise', 'options': [
            {'key': 'X', 'text': 'perpendicular through source', 'perpendicular_through': 'source', 'radius': None, 'orientation': 'either'},
            {'key': 'Y', 'text': 'wrong length and unspecified direction', 'perpendicular_through': 'center', 'radius': 'AB', 'orientation': 'either'},
            {'key': 'Z', 'text': 'oriented equal radius', 'perpendicular_through': 'center', 'radius': 'CA', 'orientation': 'counterclockwise'}]}

    def test_constructed_image_and_renamed_reordered_keys(self):
        self.assertEqual(right_angle_construction(self.spec), 'oriented equal radius')
        self.spec['options'].reverse()
        self.assertEqual(right_angle_construction(self.spec), 'oriented equal radius')

    def test_equal_radius_without_orientation_does_not_determine_image(self):
        self.spec['options'][-1]['orientation'] = 'either'
        with self.assertRaises(ValueError): right_angle_construction(self.spec)

    def test_direction_alone_does_not_determine_length(self):
        self.spec['options'][-1]['radius'] = None
        with self.assertRaises(ValueError): right_angle_construction(self.spec)

    def test_direction_does_not_rescue_wrong_radius(self):
        self.spec['options'][1]['orientation'] = 'counterclockwise'
        self.assertEqual(right_angle_construction(self.spec), 'oriented equal radius')

    def test_unknown_direction_radius_or_pivot_is_unresolved(self):
        for field, value in [('orientation', 'clockwise'), ('radius', 'unproved'), ('perpendicular_through', 'anywhere')]:
            spec = copy.deepcopy(self.spec)
            spec['options'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): right_angle_construction(spec)

    def test_unsupported_rotation_is_not_silently_a_right_angle(self):
        self.spec['angle_degrees'] = 180
        with self.assertRaises(ValueError): right_angle_construction(self.spec)


if __name__ == '__main__': unittest.main()
