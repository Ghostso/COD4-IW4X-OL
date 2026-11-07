"""Check that the packaged server image contains its startup helpers."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class PackageContextTests(unittest.TestCase):
    def test_rcon_helper_is_in_image_context(self):
        with tempfile.TemporaryDirectory(prefix='codol-package-context-') as path:
            root = Path(path).resolve()
            temp_parent = Path(tempfile.gettempdir()).resolve()
            self.assertEqual(root.parent, temp_parent)
            fake_server = root / 'server.elf'
            fake_server.write_bytes(b'\x7fELF')
            output = root / 'package'
            result = subprocess.run(
                [sys.executable, str(REPO / 'tools/codol_package.py'),
                 '--skip-game', '--linux-bin', str(fake_server),
                 '--out', str(output)], cwd=REPO, capture_output=True,
                text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            helper = output / 'gameserver/rcon_password.sh'
            self.assertTrue(helper.is_file())
            self.assertTrue((output / 'gameserver/map_handoff.awk').is_file())
            dockerfile = (output / 'gameserver/Dockerfile').read_text()
            entrypoint = (output / 'gameserver/entrypoint.sh').read_text()
            self.assertIn('COPY rcon_password.sh /usr/local/bin/rcon_password.sh', dockerfile)
            self.assertIn('/usr/local/bin/rcon_password.sh "$RCON_FILE"', entrypoint)
            self.assertIn('COPY map_handoff.awk /usr/local/bin/map_handoff.awk', dockerfile)
            self.assertIn('awk -v now="$(date +%s)" -f /usr/local/bin/map_handoff.awk "$HANDOFF"', entrypoint)


if __name__ == '__main__':
    unittest.main()
