#!/usr/bin/env python3

from __future__ import annotations

import unittest

from CodolMapEntities import parse_entities, spawn_candidates


class CodolMapEntitiesTests(unittest.TestCase):
    def test_parses_spawn_entities_and_vectors(self) -> None:
        text = r'''
        { "classname" "worldspawn" "message" "Crash" }
        {
          "classname" "mp_sd_spawn_attacker"
          "origin" "12.5 -30 64"
          "angles" "0 90 0"
          "team" "allies"
        }
        '''
        entities = parse_entities(text)
        self.assertEqual(len(entities), 2)
        self.assertEqual(
            spawn_candidates(entities),
            [
                {
                    "index": 1,
                    "classname": "mp_sd_spawn_attacker",
                    "origin": [12.5, -30.0, 64.0],
                    "angles": [0.0, 90.0, 0.0],
                    "angle": None,
                    "team": "allies",
                    "targetname": None,
                }
            ],
        )

    def test_rejects_unterminated_entity(self) -> None:
        with self.assertRaisesRegex(ValueError, "unterminated"):
            parse_entities('{ "classname" "worldspawn"')


if __name__ == "__main__":
    unittest.main()
