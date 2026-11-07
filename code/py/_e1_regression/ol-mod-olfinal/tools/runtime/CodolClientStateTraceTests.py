#!/usr/bin/env python3
"""Regression checks for the read-only CODOL packet-client trace."""

from __future__ import annotations

import unittest

from CodolClientStateTrace import (
    CLIENT_STATE_NETFIELDS_RVA,
    CL_PARSE_PACKET_CLIENTS_RVA,
    build_script,
)


class CodolClientStateTraceTests(unittest.TestCase):
    def test_trace_uses_native_packet_client_layout(self) -> None:
        script = build_script()
        self.assertIn(f"module.base.add({CL_PARSE_PACKET_CLIENTS_RVA})", script)
        self.assertIn("this.snapshot = this.context.ecx", script)
        self.assertIn("this.clientActive = args[0]", script)
        self.assertIn("snapshot.add(0x3548)", script)
        self.assertIn("snapshot.add(0x3558)", script)
        self.assertIn(
            f"module.base.add({CLIENT_STATE_NETFIELDS_RVA})", script)
        self.assertIn("clientStateFields.add(21 * 12)", script)
        self.assertIn("team: readU32(row.add(8))", script)


if __name__ == "__main__":
    unittest.main()
