#!/usr/bin/env python3

import struct
import unittest

from CodolDedicatedStatus import NONE_CLIENT, STATUS_MAGIC, decode


class DedicatedStatusTests(unittest.TestCase):
    def test_schema_four_decodes_client_think_failure_and_command(self) -> None:
        payload = bytearray(struct.pack("<IHHI", STATUS_MAGIC, 4, 1, 4000))
        payload.extend(struct.pack("<18I", *([0] * 18)))
        payload.extend(struct.pack("<5I", 0, 2, 1, 9, 8))
        payload.extend(struct.pack(
            "<IHH4I4QIIi", 0x7F000001, 30001, 0,
            3900, 20, 30, 29, 40, 40, 0, 4096, 3990, 128, 0,
        ))
        payload.extend(struct.pack(
            "<10I", 2, 3920, 3936, 3936, 3920, 3904,
            NONE_CLIENT, 0, 3, 3,
        ))
        payload.extend(struct.pack(
            "<12I2i", 3888, 2, 3920, 3904, 17, 3, 0x401,
            1024, 2048, 0, 73, 4, 127, -127,
        ))
        payload.extend(struct.pack("<6I", 1, 218, 1, 219, 0, 0))
        payload.extend(struct.pack("<I", 0))

        client = decode(bytes(payload))["clients"][0]
        self.assertEqual(client["usercmd"]["last_discarded_rejected_time"], 3888)
        self.assertEqual(client["usercmd"]["discarded_rejected_count"], 2)
        self.assertEqual(client["client_think"]["failure_stage_code"], 17)
        self.assertEqual(
            client["client_think"]["failure_stage"], "client_events_unsupported"
        )
        self.assertEqual(client["client_think"]["last_attempted_command_time"], 3920)
        self.assertEqual(client["client_think"]["command"]["buttons"], 0x401)
        self.assertEqual(client["client_think"]["command"]["weapon"], 73)
        self.assertEqual(client["client_think"]["command"]["forward_move"], 127)
        self.assertEqual(client["client_think"]["command"]["right_move"], -127)

    def test_schema_five_resolves_the_hit_height_above_the_target(self) -> None:
        # Two clients: 0 shoots, 1 is hit. The shooter stands at z=100 and the
        # target's feet are at z=64, and the committed trace stops 40% of the
        # way along a ray that descends 30 units from an eye at z=150 - so the
        # hit lands at z=138, which is 74 above the target's feet at z=64. That
        # single number is the whole point
        # of schema 5; a collapsed hit skeleton reports the same small height no
        # matter where the shooter aims.
        def client(num, origin, bullet):
            body = bytearray(struct.pack("<5I", num, 2, 1, 9, 8))
            body.extend(struct.pack(
                "<IHH4I4QIIi", 0x7F000001, 30001, 0,
                3900, 20, 30, 29, 40, 40, 0, 4096, 3990, 128, 0,
            ))
            body.extend(struct.pack(
                "<10I", 2, 3920, 3936, 3936, 3920, 3904, NONE_CLIENT, 0, 3, 3,
            ))
            body.extend(struct.pack(
                "<12I2i", 3888, 2, 3920, 3904, 0, 0, 0,
                0, 0, 0, 73, 4, 0, 0,
            ))
            body.extend(struct.pack("<3f", *origin))
            body.extend(struct.pack("<3f", 0.0, 137.0, 0.0))
            body.extend(struct.pack("<I", 100))
            body.extend(bullet)
            body.extend(struct.pack("<6I", 0, 0, 0, 0, 0, 0))
            body.extend(struct.pack("<I", 0))
            return body

        fired = bytearray(struct.pack("<I", 3920))
        fired.extend(struct.pack("<3f", 0.0, 0.0, 150.0))
        fired.extend(struct.pack("<3f", 0.0, 300.0, 120.0))
        fired.extend(struct.pack("<f", 0.4))
        fired.extend(struct.pack("<6I", 1, 1, 2, 1626, 5, 0))
        idle = bytearray(struct.pack("<I", 0xFFFFFFFF))
        idle.extend(struct.pack("<3f", 0.0, 0.0, 0.0))
        idle.extend(struct.pack("<3f", 0.0, 0.0, 0.0))
        idle.extend(struct.pack("<f", 0.0))
        idle.extend(struct.pack("<6I", 0, 2047, 0, 0, 0, 0))

        payload = bytearray(struct.pack("<IHHI", STATUS_MAGIC, 5, 2, 4000))
        payload.extend(struct.pack("<18I", *([0] * 18)))
        payload.extend(client(0, (0.0, 0.0, 90.0), fired))
        payload.extend(client(1, (0.0, 300.0, 64.0), idle))

        status = decode(bytes(payload))
        shooter, target = status["clients"]
        self.assertEqual(shooter["origin"], [0.0, 0.0, 90.0])
        self.assertEqual(shooter["view_angles"], [0.0, 137.0, 0.0])
        self.assertEqual(shooter["health"], 100)
        self.assertEqual(shooter["bullet"]["hit_entity_num"], 1)
        self.assertEqual(shooter["bullet"]["part_name"], 1626)
        self.assertEqual(shooter["bullet"]["part_group"], 5)
        self.assertAlmostEqual(shooter["bullet"]["hit_point"][2], 138.0, places=4)
        self.assertAlmostEqual(
            shooter["bullet"]["hit_height_above_target_feet"], 74.0, places=4
        )
        self.assertIsNone(target["bullet"])

    def test_schema_five_rejects_truncated_locational_diagnostics(self) -> None:
        payload = bytearray(struct.pack("<IHHI", STATUS_MAGIC, 5, 1, 4000))
        payload.extend(struct.pack("<18I", *([0] * 18)))
        payload.extend(struct.pack("<5I", 0, 2, 1, 9, 8))
        payload.extend(struct.pack(
            "<IHH4I4QIIi", 0x7F000001, 30001, 0,
            3900, 20, 30, 29, 40, 40, 0, 4096, 3990, 128, 0,
        ))
        payload.extend(struct.pack(
            "<10I", 2, 3920, 3936, 3936, 3920, 3904, NONE_CLIENT, 0, 3, 3,
        ))
        payload.extend(struct.pack(
            "<12I2i", 3888, 2, 3920, 3904, 0, 0, 0, 0, 0, 0, 73, 4, 0, 0,
        ))
        payload.extend(b"\x00" * 40)
        with self.assertRaises(RuntimeError):
            decode(bytes(payload))

    def test_schema_three_decodes_usercmd_and_projection_diagnostics(self) -> None:
        payload = bytearray(struct.pack("<IHHI", STATUS_MAGIC, 3, 1, 4000))
        payload.extend(struct.pack("<18I", *([0] * 18)))
        payload.extend(struct.pack("<5I", 0, 2, 1, 9, 8))
        payload.extend(struct.pack(
            "<IHH4I4QIIi", 0x7F000001, 30001, 0,
            3900, 20, 30, 29, 40, 40, 0, 4096, 3990, 128, 0,
        ))
        payload.extend(struct.pack(
            "<10I", 2, 3920, 3936, 3936, 3920, 3904,
            NONE_CLIENT, 0, 3, 3,
        ))
        payload.extend(struct.pack("<6I", 1, 218, 1, 219, 0, 0))
        payload.extend(struct.pack("<I", 0))

        status = decode(bytes(payload))
        client = status["clients"][0]
        self.assertEqual(client["usercmd"]["pending_count"], 2)
        self.assertEqual(client["usercmd"]["last_executed_time"], 3904)
        self.assertIsNone(client["usercmd"]["last_discarded_time"])
        self.assertEqual(client["snapshot_projection"]["player_entity_mask"], 3)
        self.assertEqual(client["snapshot_projection"]["client_info_mask"], 3)

    def test_schema_three_rejects_truncated_diagnostics(self) -> None:
        payload = bytearray(struct.pack("<IHHI", STATUS_MAGIC, 3, 1, 0))
        payload.extend(struct.pack("<18I", *([0] * 18)))
        payload.extend(struct.pack("<5I", 0, 2, 1, 0, 0))
        payload.extend(bytes(68 + 39))
        with self.assertRaisesRegex(RuntimeError, "diagnostics status is truncated"):
            decode(bytes(payload))


if __name__ == "__main__":
    unittest.main()
