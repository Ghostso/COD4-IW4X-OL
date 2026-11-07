#!/usr/bin/env python3

from __future__ import annotations

import unittest

from CodolMatchFlow import select_game_window


class MatchWindowSelectionTests(unittest.TestCase):
    def test_selects_game_window_when_console_is_enumerated_first(self) -> None:
        self.assertEqual(
            select_game_window(
                [
                    (100, 10, "ConsoleWindowClass"),
                    (200, 20, "CODO"),
                ]
            ),
            (200, 20),
        )

    def test_does_not_fall_back_to_console_window(self) -> None:
        self.assertIsNone(
            select_game_window([(100, 10, "ConsoleWindowClass")])
        )

    def test_window_class_match_is_case_insensitive(self) -> None:
        self.assertEqual(select_game_window([(200, 20, "codo")]), (200, 20))


if __name__ == "__main__":
    unittest.main()
