#!/usr/bin/env python3

import unittest

from CodolAimControl import angle_delta


class CodolAimControlTests(unittest.TestCase):
    def test_angle_delta_uses_shortest_wrapped_direction(self) -> None:
        self.assertAlmostEqual(angle_delta(5.0, 355.0), 10.0)
        self.assertAlmostEqual(angle_delta(355.0, 5.0), -10.0)
        self.assertAlmostEqual(angle_delta(-84.0, 276.0), 0.0)


if __name__ == "__main__":
    unittest.main()
