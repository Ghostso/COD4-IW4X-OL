#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from CodolTwoClientMatch import process_state, transport_progress_counters


class CodolTwoClientMatchTests(unittest.TestCase):
    def write_state(self, game: Path, processes: list[dict]) -> None:
        logs = game / "Ayria" / "Logs"
        logs.mkdir(parents=True)
        (logs / "ol-mod-processes.json").write_text(
            json.dumps({"processes": processes}), encoding="utf-8"
        )

    def test_clients_are_ordered_by_instance_not_pid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary)
            self.write_state(game, [
                {"role": "dedicated", "pid": 50000},
                {"role": "client", "pid": 53352, "instance": 1},
                {"role": "client", "pid": 24136, "instance": 2},
            ])
            self.assertEqual(process_state(game), [53352, 24136])

    def test_duplicate_instance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary)
            self.write_state(game, [
                {"role": "client", "pid": 100, "instance": 1},
                {"role": "client", "pid": 200, "instance": 1},
            ])
            with self.assertRaises(SystemExit):
                process_state(game)

    def test_transport_progress_does_not_treat_message_ack_as_a_heartbeat(self) -> None:
        counters = transport_progress_counters({
            "incoming_sequence": 123,
            "message_acknowledge": 45,
            "udp_send_succeeded": 678,
        })
        self.assertEqual(counters, {
            "incoming_sequence": 123,
            "udp_send_succeeded": 678,
        })


if __name__ == "__main__":
    unittest.main()
