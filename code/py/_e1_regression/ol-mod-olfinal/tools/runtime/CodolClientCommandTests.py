#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from CodolClientCommand import build_script, build_state_observer_script


class CodolClientCommandTests(unittest.TestCase):
    def test_command_is_dispatched_only_from_ready_game_frame(self) -> None:
        source = build_script("mr 0 1 custom1", 0, 0.0)

        self.assertIn("connectionState.readU32() !== 10", source)
        self.assertNotIn("setInterval(drive", source)
        self.assertNotIn("Interceptor.attach(comFrame", source)
        self.assertIn("invoke(commandText, 0)", source)
        self.assertIn("0xC3", source)
        self.assertNotIn("0xC2, 0x08, 0x00", source)
        self.assertNotIn("['pointer', 'int'], 'stdcall'", source)
        self.assertIn("event: 'armed'", source)
        self.assertIn("event: 'invoked'", source)
        self.assertIn("source: 'frida-script-load'", source)

    def test_state_observer_does_not_invoke_native_code(self) -> None:
        source = build_state_observer_script()
        self.assertIn("event: 'connection-state'", source)
        self.assertIn("setInterval(reportState, 50)", source)
        self.assertNotIn("NativeFunction", source)

    @unittest.skipUnless(shutil.which("node"), "node is required for generated JS check")
    def test_generated_javascript_parses(self) -> None:
        source = build_script('mr 0 2 quote"candidate', 1, 0.25)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client-command.js"
            path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
