"""Native wire regression tests; optional differential checks against alpha0022.

python tests/test_codol_wire.py [--reference PATH]
Uses the available C compiler (CC environment override), no third-party modules.
"""
import argparse
import ctypes as C
import importlib.util
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = None
LIB = None


class State(C.Structure):
    _fields_ = [("sequence", C.c_uint32), ("received", C.c_uint32 * 4),
                ("length", C.c_uint32), ("stride", C.c_uint16),
                ("last", C.c_uint8), ("active", C.c_uint8)]


def packet(message, index=0, sequence=42, qport=-1, capacity=1500):
    output = C.create_string_buffer(capacity)
    n = LIB.CODOL_WritePacket(output, capacity, sequence, qport,
                              message, len(message), index)
    return output.raw[:n]


def receive(state, buffer, pkt):
    seq, = struct.unpack_from('<I', pkt)
    return LIB.CODOL_ReadFragment(C.byref(state), buffer, len(buffer), seq,
                                  pkt[4:], len(pkt) - 4)


class WireTests(unittest.TestCase):
    def test_golden_header_and_exact_multiple(self):
        self.assertEqual(packet(b'abc', sequence=7), b'\x07\0\0\0abc')
        self.assertEqual(packet(b'abc', sequence=7, qport=17733),
                         struct.pack('<IH', 7, 17733) + b'abc')
        body = b'x' * 2324
        self.assertEqual(packet(body)[:10], bytes.fromhex('2a00008000018a048a04'))
        self.assertEqual(packet(body, 1)[:10], bytes.fromhex('2a00008001018a048a04'))
        self.assertEqual(packet(body, 2), b'')  # no empty terminator
        self.assertEqual(len(packet(b'x' * 1161)), 1165)
        self.assertEqual(len(packet(b'x' * 1162)), 1172)

    def test_reordered_duplicate_and_bounds(self):
        rng = random.Random(187)
        for length in (1162, 1163, 2324, 6000, 131072, 148736):
            body = rng.randbytes(length)
            parts = [packet(body, i) for i in range((length + 1161) // 1162)]
            rng.shuffle(parts)
            state, output = State(), C.create_string_buffer(length)
            for i, part in enumerate(parts):
                result = receive(state, output, part)
                self.assertEqual(result, 1 if i == len(parts) - 1 else 0)
                self.assertEqual(receive(state, output, part), result)
            self.assertEqual(state.length, length)
            self.assertEqual(output.raw, body)
        self.assertEqual(packet(b'x' * 148737), b'')
        self.assertEqual(packet(b'abc', capacity=6), b'')
        self.assertEqual(packet(b'a', sequence=0x20000000), b'')

    def test_bad_fragments_do_not_change_state(self):
        good = packet(b'x' * 2400)
        mutations = [good[:i] for i in range(len(good))]
        for pos, value in ((4, 128), (5, 128), (6, 0), (7, 0), (8, 0), (9, 0)):
            bad = bytearray(good); bad[pos] = value
            mutations.append(bytes(bad))
        for bad in mutations:
            if len(bad) < 4:
                continue
            s, out = State(), C.create_string_buffer(2400)
            before = bytes(s), out.raw
            self.assertEqual(receive(s, out, bad), -1)
            self.assertEqual((bytes(s), out.raw), before)
        s, out = State(), C.create_string_buffer(1161)
        self.assertEqual(receive(s, out, good), -1)

    def test_conflict_and_stale_sequence(self):
        s, out = State(), C.create_string_buffer(2400)
        good = packet(b'x' * 2400, sequence=8)
        self.assertEqual(receive(s, out, good), 0)
        before = bytes(s), out.raw
        bad = bytearray(good); bad[-1] ^= 1
        self.assertEqual(receive(s, out, bytes(bad)), -1)
        self.assertEqual(receive(s, out, packet(b'x' * 2400, sequence=7)), 0)
        self.assertEqual((bytes(s), out.raw), before)
        bad = bytearray(good); bad[5] = 1
        self.assertEqual(receive(s, out, bytes(bad)), -1)
        self.assertEqual((bytes(s), out.raw), before)

    def test_xor_raw_command_bytes(self):
        body, command, initial = bytes(range(128)), b'%\xff\x80hello', 179
        key, expected = initial, bytearray(body)
        for i in range(len(body)):
            key ^= (command[i % len(command)] << (i & 1)) & 255
            expected[i] ^= key
        out = C.create_string_buffer(body, len(body))
        LIB.CODOL_Xor(out, len(body), initial, command, len(command))
        self.assertEqual(out.raw, bytes(expected))
        LIB.CODOL_Xor(out, len(body), initial, command, len(command))
        self.assertEqual(out.raw, body)
        LIB.CODOL_Xor(out, len(body), initial, b'', 0)
        self.assertEqual(out.raw, bytes(v ^ initial for v in body))

    def test_counter_epoch(self):
        for wire, last, expected in ((0, 65535, 65536), (65535, 65536, 65535),
                                     (2, 65537, 65538), (32768, 0, 32768),
                                     (0, 0xffffffff, 0), (65535, 1, 65535)):
            self.assertEqual(LIB.CODOL_ExtendCounter(wire, last), expected)

    def test_alpha0022_byte_parity(self):
        if not REFERENCE:
            self.skipTest('pass --reference for alpha0022 differential tests')
        spec = importlib.util.spec_from_file_location('reference_fragments',
                                                     REFERENCE / 'netchan_fragment.py')
        ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
        rng = random.Random(11113)
        for length in (0, 1, 1161, 1162, 1163, 2324, 6198, 131072, 148736):
            body = rng.randbytes(length)
            expected = ref.split_payload(struct.pack('<I', 42) + body)
            actual = [packet(body, i) for i in range(max(1, (length + 1161) // 1162))]
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path)
    args, rest = parser.parse_known_args()
    REFERENCE = args.reference
    with tempfile.TemporaryDirectory(prefix='codol-wire-') as tmp:
        target = Path(tmp) / ('wire.dll' if os.name == 'nt' else 'wire.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE, '-std=c11', '-Wall', '-Wextra',
                        '-Werror', '-shared', '-fPIC', '-O2', str(ROOT / 'src/codol/net/codol_wire.c'),
                        '-o', str(target)], check=True)
        LIB = C.CDLL(str(target))
        LIB.CODOL_WritePacket.argtypes = [C.c_void_p, C.c_size_t, C.c_uint32, C.c_int,
                                          C.c_void_p, C.c_size_t, C.c_uint]
        LIB.CODOL_WritePacket.restype = C.c_size_t
        LIB.CODOL_ReadFragment.argtypes = [C.POINTER(State), C.c_void_p, C.c_size_t,
                                           C.c_uint32, C.c_void_p, C.c_size_t]
        LIB.CODOL_Xor.argtypes = [C.c_void_p, C.c_size_t, C.c_uint8, C.c_void_p, C.c_size_t]
        LIB.CODOL_ExtendCounter.argtypes = [C.c_uint16, C.c_uint32]
        LIB.CODOL_ExtendCounter.restype = C.c_uint32
        run = unittest.main(argv=[__file__] + rest, exit=False)
        # ctypes keeps the DLL open on Windows; release it before cleanup.
        if os.name == 'nt':
            import _ctypes
            _ctypes.FreeLibrary(LIB._handle)
    sys.exit(0 if run.result.wasSuccessful() else 1)
