"""Exercise the packaged server's lobby handoff parser with real awk."""

from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PARSER = REPO / 'tools/package/gameserver/map_handoff.awk'
NOW = 1_800_000_000


class PackageHandoffTests(unittest.TestCase):
    def parse(self, record):
        with tempfile.TemporaryDirectory(prefix='codol-handoff-') as directory:
            handoff = Path(directory) / 'startgame.txt'
            handoff.write_bytes(record.encode('ascii'))
            return subprocess.run(
                ['awk', '-v', f'now={NOW}', '-f', str(PARSER), str(handoff)],
                capture_output=True, text=True, check=False)

    def record(self, stamp=NOW, map_name='mp_rust', gametype='dm', zone='mp',
               session='mp_rust'):
        return (f'{stamp} ready 1 map={map_name} gametype={gametype} '
                f'type={zone} session_map={session}\n')

    def test_valid_modes_and_legacy_session_fallback(self):
        for zone, map_name, session in (
            ('mp', 'mp_rust', 'mp_rust'),
            ('coop', 'mp_killhouse_sh', 'coop_training_mp_killhouse_sh'),
            ('zm', 'zm_nuked', 'zm_nuked'),
        ):
            with self.subTest(zone=zone):
                result = self.parse(self.record(map_name=map_name, zone=zone,
                                                session=session))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(),
                                 f'{map_name} dm {zone} {session}')
        legacy = self.record().replace(' session_map=mp_rust', '')
        result = self.parse(legacy)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'mp_rust dm mp mp_rust')

    def test_name_limits_match_windows_reader(self):
        self.assertEqual(self.parse(self.record(map_name='m' + 'a' * 63)).returncode, 0)
        self.assertEqual(self.parse(self.record(gametype='d' + 'm' * 31)).returncode, 0)
        for record in (
            self.record(map_name='m' + 'a' * 64),
            self.record(session='s' + 'a' * 64),
            self.record(gametype='d' + 'm' * 32),
            self.record(map_name='mp_rust;echo'),
            self.record(zone='other'),
        ):
            with self.subTest(record=record):
                self.assertNotEqual(self.parse(record).returncode, 0)

    def test_freshness_and_record_integrity(self):
        self.assertEqual(self.parse(self.record(stamp=NOW - 600)).returncode, 0)
        self.assertEqual(self.parse(self.record(stamp=NOW + 60)).returncode, 0)
        self.assertEqual(self.parse(self.record().replace('\n', '\r\n')).returncode, 0)
        for record in (
            self.record(stamp=NOW - 601),
            self.record(stamp=NOW + 61),
            self.record(stamp='not-a-time'),
            self.record() + self.record(map_name='mp_crash'),
            ' ',
        ):
            with self.subTest(record=record):
                self.assertNotEqual(self.parse(record).returncode, 0)


if __name__ == '__main__':
    unittest.main()
