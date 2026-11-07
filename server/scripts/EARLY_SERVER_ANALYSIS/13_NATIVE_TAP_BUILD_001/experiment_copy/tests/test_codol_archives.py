"""Differential native archive tests. No game process is started.

Build make codol-archive first. --wsl Ubuntu-24.04 runs the Linux inspector
from Windows. The supplied reference and cached zones are read only.
"""
import argparse
import hashlib
import importlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ARGS = ZA = FF = None


def host_path(path):
    path = str(Path(path).resolve())
    if ARGS.wsl:
        return '/mnt/' + path[0].lower() + path[2:].replace('\\', '/')
    return path


def native(path, exe=None):
    cmd = ['wsl', '-d', ARGS.wsl, '--'] if ARGS.wsl else []
    cmd += [host_path(ARGS.tool), host_path(path)]
    if exe:
        cmd.append(host_path(exe))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def manifest(data):
    zone = ZA.Zone(data)
    lines = [f'zone {len(data)} {len(zone.assets)} {zone.string_count}']
    position = 56 + 4*zone.string_count
    for index in range(zone.string_count):
        reference = struct.unpack_from('<I', data, 56+4*index)[0]
        digest = 'unresolved'
        if reference == 0xffffffff:
            end = data.index(0, position)
            digest = hashlib.sha256(data[position:end]).hexdigest()
            position = end + 1
        lines.append(f'string {index} {reference} {digest}')
    for asset in zone.assets:
        payload = ZA.decode_rawfile(asset.blob)[1] if asset.type == 36 else asset.blob
        lines.append(f'asset {asset.index} {asset.type} {asset.size} {len(payload)} '
                     + hashlib.sha256(payload).hexdigest())
    return '\n'.join(lines)


class Archives(unittest.TestCase):
    def assert_manifest(self, path, data, exe=None):
        result = native(path, exe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), manifest(data))

    def test_cached_zones(self):
        paths = sorted(Path(ARGS.cache).glob('*.zone'))
        self.assertTrue(paths, 'No cached zones found')
        for path in paths:
            with self.subTest(zone=path.name):
                self.assert_manifest(path, path.read_bytes())

    def test_shipped_fastfiles(self):
        for name in ('code_pre_gfx_mp', 'code_post_gfx_mp', 'common_gametype_mp',
                     'mp_killhouse_sh'):
            with self.subTest(zone=name):
                self.assert_manifest(Path(ARGS.root) / 'client_shipRetail/chinese' / (name + '.ff'),
                                     (Path(ARGS.cache) / (name + '.zone')).read_bytes(),
                                     Path(ARGS.root) / 'C1.exe')

    def test_generated_stream_and_rawfiles(self):
        builder = FF.ZoneBuilder('native-test').add_zone_marker()
        builder.strings = [b'tag_origin', b'', b'j_head', b'tag_origin']
        for size in (0, 1, 65535, 65536, 65537, 131073, 1048577):
            payload = (bytes(range(256)) * (size // 256 + 1))[:size]
            for compressed in (False, True):
                builder.add_rawfile(f'test/{size}-{compressed}.gsc', payload, compressed)
        builder.add_stringtable('test/table.csv', [['a', 'b'], ['c', 'd']])
        data = builder.build()
        with tempfile.TemporaryDirectory(prefix='codol-archive-') as folder:
            path = Path(folder) / 'test.zone'
            path.write_bytes(data)
            self.assert_manifest(path, data)
            wrapped = FF.wrap_ffotd(data, key=bytes(range(24)), iv=bytes(range(16)))
            path = Path(folder) / 'test.ff'
            path.write_bytes(wrapped)
            self.assert_manifest(path, data, Path(ARGS.root) / 'C1.exe')
            for offset in (0, 8, 0x15, 0x114, 0x115, len(wrapped) - 1):
                with self.subTest(corruption=offset):
                    corrupt = bytearray(wrapped)
                    corrupt[offset] ^= 0x80
                    path.write_bytes(corrupt)
                    self.assertNotEqual(native(path, Path(ARGS.root) / 'C1.exe').returncode, 0)

    def test_zone_bounds(self):
        data = FF.ZoneBuilder('bounds').add_rawfile('a.gsc', b'main() {}', True).build()
        zone = ZA.Zone(data)
        variants = [data[:n] for n in (0, 1, 39, 55, len(data)-1)]
        for offset in (0, 0x28, 0x30, zone.asset_table_offset + 4,
                       zone.asset_table_offset + 12, zone.assets[0].offset + 0x28 + 4,
                       zone.assets[0].offset + 0x28 + 8):
            corrupt = bytearray(data)
            struct.pack_into('<I', corrupt, offset, 0xffffffff)
            variants.append(corrupt)
        with tempfile.TemporaryDirectory(prefix='codol-bounds-') as folder:
            path = Path(folder) / 'bad.zone'
            for index, data in enumerate(variants):
                with self.subTest(case=index):
                    path.write_bytes(data)
                    self.assertNotEqual(native(path).returncode, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--tool', default=str(Path(__file__).resolve().parents[1] / 'bin/codol_archive'))
    parser.add_argument('--wsl')
    ARGS, rest = parser.parse_known_args()
    sys.path.insert(0, str(Path(ARGS.reference)))
    sys.path.insert(0, str(Path(ARGS.reference) / 'ffwriter'))
    ZA = importlib.import_module('zone_assets')
    FF = importlib.import_module('codol_ff')
    unittest.main(argv=[sys.argv[0]] + rest)
