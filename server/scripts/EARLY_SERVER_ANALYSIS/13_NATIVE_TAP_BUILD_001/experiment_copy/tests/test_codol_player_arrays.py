"""Combined player-state sections compared with the reference writers."""
import argparse
import ast
import ctypes as C
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from test_codol_delta import Msg, Context
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

ROOT = Path(__file__).resolve().parents[1]
LIB = WS = EC = STATS = None

class Updates(C.Structure):
    _fields_ = [('stats_mask', C.c_uint8), ('stats', C.c_int32*4),
                ('clip_mask', C.c_uint16), ('weapons_mask', C.c_uint16),
                ('weapon_index_mask', C.c_uint16), ('reserve_mask', C.c_uint16),
                ('clip_index', C.c_int16*16), ('clip_presence', C.c_uint8*16),
                ('clip_ammo', (C.c_uint16*2)*16), ('weapon_index', C.c_uint16*15),
                ('weapon_flags', C.c_uint8*15), ('reserve_type', C.c_uint16*16),
                ('reserve_ammo', C.c_uint16*16)]

class Element(C.Structure):
    _fields_ = [('field', C.c_uint32*42)]

# Section 5 (objectives) shares this carrier with section 6 (HUD elements);
# see codol_player_arrays.h. The tests leave it zeroed, which keeps the
# section-5 gate off and the emitted bits identical to before it existed.
class Objective(C.Structure):
    _fields_ = [('state', C.c_uint), ('field', C.c_uint*6)]

class Hud(C.Structure):
    _fields_ = [('count', C.c_uint*2), ('elements', (Element*31)*2),
                ('objectives', Objective*32)]

def hud_reference(hud):
    arrays = []
    for a in range(2):
        elements = []
        for slot in range(hud.count[a]):
            item = {}
            for i, (_, bits) in enumerate(WS.HUDELEM_FIELDS):
                value = hud.elements[a][slot].field[i]
                if bits == -85:
                    value = tuple((value >> (8*k)) & 255 for k in range(4))
                elif EC.kind_of(bits) == 'f':
                    value = EC.i2f(value)
                item[i] = value
            elements.append(item)
        arrays.append(elements)
    return tuple(arrays)

def expected(u, old, new, pool):
    writer = EC.MsgWriter()
    writer.write_bits(5 & ((1 << pool)-1), pool)
    stats = [u.stats[i] if u.stats_mask & (1 << i) else None for i in range(4)]
    clips = [(i, u.clip_index[i], [u.clip_ammo[i][k] if u.clip_presence[i] & (1 << k) else None
                                 for k in range(2)]) for i in range(16) if u.clip_mask & (1 << i)]
    weapons = None if not u.weapons_mask else [
        ((u.weapon_index[i] if u.weapon_index_mask & (1 << i) else None), u.weapon_flags[i])
        if u.weapons_mask & (1 << i) else None for i in range(15)]
    reserves = [(i, u.reserve_type[i], u.reserve_ammo[i]) for i in range(16) if u.reserve_mask & (1 << i)]
    WS.encode_trailing_sections(writer, STATS, stats=stats, weapons_equipped=weapons,
        ammo_in_clip=clips, ammo_not_in_clip=reserves, hud=hud_reference(new),
        hud_from=hud_reference(old), server_time=20000)
    return writer.bytes()

def native(u, old, new, pool=3, capacity=16384):
    buffer = C.create_string_buffer(capacity); msg = Msg()
    ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
    LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, capacity)
    LIB.CODOL_WriteBits(C.byref(msg), 5 & ((1 << pool)-1), pool)
    ok = LIB.CODOL_WritePlayerArrays(C.byref(msg), C.byref(u), C.byref(old), C.byref(new), C.byref(ctx))
    return ok, buffer.raw[:msg.size]

class Arrays(unittest.TestCase):
    def test_combined_sections(self):
        rng = random.Random(187)
        for case in range(40):
            u = Updates(); old, new = Hud(), Hud()
            if case:
                u.stats_mask = rng.randrange(16)
                for i in range(4): u.stats[i] = rng.randrange(256 if i == 3 else 65536)
                u.clip_mask = rng.randrange(65536); u.reserve_mask = rng.randrange(65536)
                u.weapons_mask = rng.randrange(32768); u.weapon_index_mask = rng.randrange(32768)
                for i in range(16):
                    u.clip_index[i] = -1 if i == 0 else rng.randrange(1023)
                    u.clip_presence[i] = rng.randrange(4)
                    for hand in range(2): u.clip_ammo[i][hand] = rng.randrange(512)
                    u.reserve_type[i] = rng.randrange(1024); u.reserve_ammo[i] = rng.randrange(2048)
                    if i < 15:
                        u.weapon_index[i] = rng.randrange(1024); u.weapon_flags[i] = rng.randrange(32)
            for pool in range(8):
                ok, data = native(u, old, new, pool)
                self.assertTrue(ok)
                self.assertEqual(data, expected(u, old, new, pool))
            if case < 3:
                for capacity in range(len(data)):
                    self.assertFalse(native(u, old, new, 7, capacity)[0])

    def test_hud_arrays_and_delete(self):
        u = Updates(); old, new = Hud(), Hud()
        for array in range(2):
            new.count[array] = 31
            for slot in range(31):
                element = new.elements[array][slot].field
                element[3] = 4; element[0] = 0xf8ffffff
                element[4] = slot + 1; element[5] = 24; element[6] = 24
                element[14] = 1; element[41] = 0xffffffff
        for before, after in ((old, new), (new, new), (new, old)):
            self.assertEqual(native(u, before, after)[1], expected(u, before, after, 3))
        new.count[0] = 32
        self.assertFalse(native(u, old, new)[0])
        new.count[0] = 1; new.elements[0][0].field[3] = 0
        self.assertFalse(native(u, old, new)[0])

    def test_invalid_widths(self):
        old = new = Hud()
        u = Updates(); u.clip_mask = 1; u.clip_index[0] = 1024
        self.assertFalse(native(u, old, new)[0])
        u = Updates(); u.weapons_mask = u.weapon_index_mask = 1; u.weapon_index[0] = 1024
        self.assertFalse(native(u, old, new)[0])
        u = Updates(); u.reserve_mask = 1; u.reserve_ammo[0] = 2048
        self.assertFalse(native(u, old, new)[0])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--reference', type=Path, required=True)
    args, rest = parser.parse_known_args(); sys.path.insert(0, str(args.reference))
    import entity_codec as EC
    import weapon_spawn as WS
    tree = ast.parse((args.reference/'spawn_player.py').read_text(encoding='utf-8-sig'))
    method = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_write_stats_section')
    namespace = {}; exec(compile(ast.Module(body=[method], type_ignores=[]), '<reference stats>', 'exec'), namespace)
    STATS = namespace['_write_stats_section']
    with tempfile.TemporaryDirectory(prefix='codol-arrays-') as folder:
        target = Path(folder) / ('arrays.dll' if os.name == 'nt' else 'arrays.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-shared', '-fPIC', '-O2', str(ROOT/'src/codol/net/codol_msg.c'),
                        str(ROOT/'src/codol/snapshot/codol_delta.c'), str(ROOT/'src/codol/snapshot/codol_player_arrays.c'),
                        '-lm', '-o', str(target)], check=True)
        LIB = C.CDLL(str(target))
        LIB.CODOL_MsgWriteInit.argtypes = [C.POINTER(Msg), C.c_void_p, C.c_size_t]
        LIB.CODOL_WriteBits.argtypes = [C.POINTER(Msg), C.c_uint32, C.c_uint]
        LIB.CODOL_WritePlayerArrays.argtypes = [C.POINTER(Msg), C.POINTER(Updates), C.POINTER(Hud), C.POINTER(Hud), C.POINTER(Context)]
        run = unittest.main(argv=[__file__] + rest, exit=False)
        if os.name == 'nt':
            import _ctypes
            _ctypes.FreeLibrary(LIB._handle)
    sys.exit(0 if run.result.wasSuccessful() else 1)
