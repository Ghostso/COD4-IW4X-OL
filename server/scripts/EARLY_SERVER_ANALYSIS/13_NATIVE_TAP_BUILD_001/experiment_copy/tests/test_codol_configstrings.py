"""Byte parity with the reference configstring writer, extracted without startup."""
import argparse
import ast
import ctypes as C
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

ROOT = Path(__file__).resolve().parents[1]
LIB = REF = None
CHECKSUMS = None


class Msg(C.Structure):
    _fields_ = [('data', C.c_void_p), ('size', C.c_size_t), ('capacity', C.c_size_t),
                ('cursor', C.c_size_t), ('bit', C.c_size_t), ('failed', C.c_int)]


class Bank(C.Structure):
    _fields_ = [('values', C.c_void_p * 6519), ('bytes', C.c_size_t), ('count', C.c_uint)]


class Configstrings(unittest.TestCase):
    def test_measured_constant_checksums(self):
        checksum = C.c_uint32(123)
        for category, expected in CHECKSUMS.items():
            self.assertTrue(LIB.CODOL_ConstConfigChecksum(category.encode(), C.byref(checksum)))
            self.assertEqual(checksum.value, expected)
        self.assertFalse(LIB.CODOL_ConstConfigChecksum(b'tdm', C.byref(checksum)))

    def setUp(self):
        self.bank = Bank()

    def tearDown(self):
        LIB.CODOL_ClearConfigstrings(C.byref(self.bank))

    def set(self, index, value):
        self.assertTrue(LIB.CODOL_SetConfigstring(C.byref(self.bank), index, value))

    def encode(self, capacity=262144, gamestate=False):
        buffer = C.create_string_buffer(capacity)
        msg = Msg()
        LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, capacity)
        if gamestate:
            ok = LIB.CODOL_WriteGamestate(C.byref(msg), C.byref(self.bank), b'mp_killhouse_sh',
                                         b'mp', 0x89abcdef, 127, 3, 0x12345678)
        else:
            ok = LIB.CODOL_WriteConfigstrings(C.byref(msg), C.byref(self.bank))
        return ok, buffer.raw[:msg.size], msg

    def test_reference_parity(self):
        for entries in ([], [(0, '')], [(0, 'abc'), (1, ''), (2, 'cod'), (5364, 'weapon'),
                         (6517, '55'), (6518, '\xff%')],
                        [(i, '' if i % 3 else str(i)) for i in range(6519)]):
            LIB.CODOL_ClearConfigstrings(C.byref(self.bank))
            for i, text in entries:
                self.set(i, text.encode('latin1'))
            ok, data, msg = self.encode()
            self.assertTrue(ok)
            self.assertFalse(msg.failed)
            self.assertEqual(data, REF.build_configstring_block(entries))

    def test_empty_is_distinct_from_unset(self):
        self.set(5363, b'')
        self.assertEqual(self.bank.count, 1)
        self.assertEqual(self.bank.bytes, 1)
        self.assertEqual(LIB.CODOL_GetConfigstring(C.byref(self.bank), 5363), b'')
        self.assertIsNone(LIB.CODOL_GetConfigstring(C.byref(self.bank), 5364))
        self.set(5363, None)
        self.assertEqual(self.bank.count, 0)
        self.assertFalse(LIB.CODOL_SetConfigstring(C.byref(self.bank), 6519, b'invalid'))

    def test_effective_inherited_model_reassertion_value(self):
        inherited = Bank()
        try:
            # MP inherits this model slot, while a prior category can send a
            # runtime update at the same index. The reassertion must use MP's
            # effective value after gamestate even without an override.
            self.assertTrue(LIB.CODOL_SetConfigstring(C.byref(inherited), 1685,
                                                       b'bar_spcsshotgun_tf_f_10'))
            self.assertEqual(LIB.CODOL_GetEffectiveConfigstring(
                C.byref(self.bank), C.byref(inherited), 1685),
                b'bar_spcsshotgun_tf_f_10')
            self.set(1685, b'')
            self.assertEqual(LIB.CODOL_GetEffectiveConfigstring(
                C.byref(self.bank), C.byref(inherited), 1685), b'')
        finally:
            LIB.CODOL_ClearConfigstrings(C.byref(inherited))

    def test_gamestate_order(self):
        self.set(0, b'\\g_gametype\\tdm')
        want = (b'\x02' + struct.pack('<I', 127) + b'mp_killhouse_sh\0mp\0'
                + struct.pack('<I', 0x89abcdef)
                + REF.build_configstring_block([(0, '\\g_gametype\\tdm')])
                + struct.pack('<II', 3, 0x12345678) + b'\x05')
        ok, data, _ = self.encode(gamestate=True)
        self.assertTrue(ok)
        self.assertEqual(data, want)
        for capacity in range(len(want)):
            self.assertFalse(self.encode(capacity, True)[0])

    def test_replicated_block_replacement(self):
        names = (C.c_char_p * 2)(b'first', b'second')
        values = (C.c_char_p * 2)(b'1', b'2')
        self.assertTrue(LIB.CODOL_SetReplicatedDvars(C.byref(self.bank), 2, names, values))
        self.assertEqual(LIB.CODOL_GetConfigstring(C.byref(self.bank), 24), b'first')
        self.assertEqual(LIB.CODOL_GetConfigstring(C.byref(self.bank), 225), b'2')
        self.assertEqual(LIB.CODOL_GetConfigstring(C.byref(self.bank), 26), b'')
        before = self.encode()[1]
        names[1] = b''
        self.assertFalse(LIB.CODOL_SetReplicatedDvars(C.byref(self.bank), 2, names, values))
        self.assertEqual(before, self.encode()[1])
        self.assertTrue(LIB.CODOL_SetReplicatedDvars(C.byref(self.bank), 1, names, values))
        self.assertEqual(LIB.CODOL_GetConfigstring(C.byref(self.bank), 25), b'')
        self.assertEqual(LIB.CODOL_GetConfigstring(C.byref(self.bank), 225), b'')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    args, rest = parser.parse_known_args()
    # Execute only the two pure writer definitions; no imports/game server startup.
    source = ast.parse((args.reference / 'game-server.py').read_text(encoding='utf-8-sig'))
    parts = {node.name: node for node in ast.walk(source)
             if isinstance(node, (ast.ClassDef, ast.FunctionDef))
             and node.name in ('_CfgWriter', 'build_configstring_block')}
    namespace = {'os': type('Environment', (), {'environ': {'CODOL_NO_SECTIONS': '1'}})()}
    module = ast.Module(body=[parts['_CfgWriter'], parts['build_configstring_block']], type_ignores=[])
    exec(compile(module, '<reference writer>', 'exec'), namespace)
    REF = type('Reference', (), {key: namespace[key] for key in parts})()
    crc_source = ast.parse((args.reference / 'zone_crc.py').read_text(encoding='utf-8-sig'))
    CHECKSUMS = next(ast.literal_eval(node.value) for node in crc_source.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'FS_CRC_BY_ZONE_TYPE' for t in node.targets))
    with tempfile.TemporaryDirectory(prefix='codol-config-') as folder:
        target = Path(folder) / ('cfg.dll' if os.name == 'nt' else 'cfg.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-shared', '-fPIC', '-O2', str(ROOT/'src/codol/net/codol_msg.c'),
                        str(ROOT/'src/codol/snapshot/codol_configstrings.c'), '-o', str(target)], check=True)
        LIB = C.CDLL(str(target))
        bank, msg = C.POINTER(Bank), C.POINTER(Msg)
        LIB.CODOL_ClearConfigstrings.argtypes = [bank]
        LIB.CODOL_SetConfigstring.argtypes = [bank, C.c_uint, C.c_char_p]
        LIB.CODOL_GetConfigstring.argtypes = [bank, C.c_uint]
        LIB.CODOL_GetConfigstring.restype = C.c_char_p
        LIB.CODOL_GetEffectiveConfigstring.argtypes = [bank, bank, C.c_uint]
        LIB.CODOL_GetEffectiveConfigstring.restype = C.c_char_p
        LIB.CODOL_ConstConfigChecksum.argtypes = [C.c_char_p, C.POINTER(C.c_uint32)]
        LIB.CODOL_SetReplicatedDvars.argtypes = [bank, C.c_uint, C.POINTER(C.c_char_p), C.POINTER(C.c_char_p)]
        LIB.CODOL_MsgWriteInit.argtypes = [msg, C.c_void_p, C.c_size_t]
        LIB.CODOL_WriteConfigstrings.argtypes = [msg, bank]
        LIB.CODOL_WriteGamestate.argtypes = [msg, bank, C.c_char_p, C.c_char_p] + [C.c_uint32]*4
        run = unittest.main(argv=[__file__] + rest, exit=False)
        if os.name == 'nt':
            import _ctypes
            _ctypes.FreeLibrary(LIB._handle)
    sys.exit(0 if run.result.wasSuccessful() else 1)
